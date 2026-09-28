"""Conciliação por movimento e por título. Não altera o ERP nem aprova encargos."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from itertools import combinations
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / 'config/reconciliation.json'


def norm(value):
    value = unicodedata.normalize('NFKD', value or '').encode('ascii', 'ignore').decode().upper()
    return re.sub(r'\s+', ' ', re.sub(r'[^A-Z0-9 ]', ' ', value)).strip()


def cents(value):
    scaled = Decimal(str(value)) * 100
    if not scaled.is_finite() or scaled != scaled.to_integral_value():
        raise ValueError(f'Valor não representável em centavos: {value}')
    return int(scaled)


def money(value):
    return '' if value is None else f'{Decimal(value) / 100:.2f}'


def bank_entries(path):
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    try:
        content = data.decode('utf-8-sig')
    except UnicodeDecodeError:
        content = data.decode('cp1252')
    lines = content.splitlines()
    header = next(i for i, line in enumerate(lines) if line.lower().startswith('data;lan'))
    entries = []
    for physical_line, row in enumerate(csv.reader(lines[header + 1:], delimiter=';'), header + 2):
        if len(row) < 5 or not row[3].strip():
            continue  # Saldos não são movimentos.
        entries.append(dict(bank_id=f'{digest[:16]}:{physical_line}', file_sha256=digest,
                            source_file=path.name, source_line=physical_line,
                            date=datetime.strptime(row[0], '%d/%m/%Y').date(),
                            description=row[1].strip(), origin=row[2].strip(),
                            cents=cents(row[3].replace('.', '').replace(',', '.'))))
    return entries


def discover_bank_files(folder):
    """Detecta o layout do extrato pelos cabeçalhos, sem depender do nome do arquivo."""
    found=[]
    for path in sorted(folder.glob('*.csv')):
        raw=path.read_bytes()
        try:
            text=raw.decode('utf-8-sig')
        except UnicodeDecodeError:
            text=raw.decode('cp1252')
        if any(line.lower().startswith('data;lan') for line in text.splitlines()[:20]):
            found.append(path)
    return found


def statement_end(path, entries):
    # O último movimento pode anteceder o fim do período coberto pelo extrato.
    text = path.read_bytes().decode('cp1252')
    period = re.search(r'(\d{2}/\d{2}/\d{4})\s+a\s+(\d{2}/\d{2}/\d{4})', text[:1000])
    if period:
        end = datetime.strptime(period[2], '%d/%m/%Y').date()
        if end < max(e['date'] for e in entries):
            raise ValueError('Período do extrato termina antes do último movimento')
        return end, 'statement_header'
    return max(e['date'] for e in entries), 'last_movement_only'


def candidates(db):
    con = duckdb.connect(str(db), read_only=True)
    try:
        rows = con.execute('''
            select g.id_externo, g.tipo, g.beneficiario_nome, g.num_documento,
                   g.data_vencimento, g.competence, g.valor_total_candidato,
                   g.final_release_blockers, p.employee_number
            from int_ap_release_gate g
            left join (
              select candidate_group_key,
                     case when count(distinct linked_employee_number)=1
                          and count(linked_employee_number)=count(*)
                          then min(linked_employee_number) end as employee_number
              from int_ap_component_candidates group by 1
            ) p using(candidate_group_key)
            order by g.tipo, g.competence, g.beneficiario_nome, g.id_externo
        ''').fetchall()
        cards = con.execute('''
            select transaction_id, trip_id, request_ts_local::date, amount_brl, payment_route_status
            from int_transaction_enrichment where payment_route_status='needs_client_card_destination'
            order by transaction_id
        ''').fetchall()
    finally:
        con.close()
    titles = [dict(id=r[0], kind=r[1], name=r[2] or '', document=r[3] or '', due=r[4],
                   competence=r[5], cents=cents(r[6]) if r[6] is not None else None,
                   blockers=r[7] or [], beneficiary_key=r[8]) for r in rows]
    visa = [dict(id=r[0], trip_id=r[1], date=r[2], cents=cents(r[3]), route=r[4])
            for r in cards if r[3] is not None and r[2] is not None]
    return titles, visa


def in_window(entry, title, before, after):
    return title['due'] is not None and -before <= (entry['date'] - title['due']).days <= after


def reconcile(titles, visa_rows, entries, config=None):
    config = config or json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
    debits = sorted((e for e in entries if e['cents'] < 0), key=lambda e: (e['date'], e['bank_id']))
    used, duplicate, review = set(), set(), set()
    for t in titles:
        t.update(bank_ids=[], duplicate_bank_ids=[], review_candidates=[], paid_cents=None,
                 duplicate_cents=0, difference_cents=None, confidence='none',
                 primary_status='unmatched', status='unmatched', rule='')
        if t['kind']=='FATURA_FORNECEDOR' and (t['cents'] is None or t['cents']<=0 or t['due'] is None):
            t.update(primary_status='not_assessable', rule='invoice_amount_or_due_unavailable')

    def match(t, e, status, confidence, rule, allocated):
        t.update(bank_ids=[e['bank_id']], paid_cents=allocated, primary_status=status,
                 confidence=confidence, difference_cents=allocated-t['cents'], rule=rule)

    def flag(e, options, reason):
        review.add(e['bank_id'])
        for t in options:
            candidate = dict(bank_id=e['bank_id'], reason=reason)
            if candidate not in t['review_candidates']:
                t['review_candidates'].append(candidate)

    searchable = []
    for t in (t for t in titles if t['kind']=='REEMBOLSO_COLABORADOR'):
        if t['cents'] is None or t['cents'] <= 0 or not t.get('beneficiary_key') or not norm(t['name']) or not t['due']:
            t.update(primary_status='not_assessable', rule='missing_unique_identity_positive_amount_or_due_date')
        else:
            searchable.append(t)  # Inclui retidos por CPF, classificação, emissão e outros motivos.

    def pix_options(e):
        prefix = norm(e['description'][len('PIX TRANSF '):])
        return [t for t in searchable if prefix and norm(t['name']).startswith(prefix)
                and in_window(e, t, config['pix_days_before_due'], config['pix_days_after_due'])]

    pix = [e for e in debits if e['description'].upper().startswith('PIX TRANSF ')]
    for e in pix:
        options = [t for t in pix_options(e) if t['cents']==-e['cents']]
        if len(options) > 1:
            flag(e, options, 'ambiguous_exact_match')
        elif len(options) == 1:
            t = options[0]
            if t['bank_ids']:
                t['duplicate_bank_ids'].append(e['bank_id'])
                t['duplicate_cents'] += -e['cents']
                duplicate.add(e['bank_id'])
            else:
                match(t, e, 'matched_exact', 'high', 'unique_prefix_amount_due_window', -e['cents'])
                used.add(e['bank_id'])

    for e in pix:
        if e['bank_id'] in used | duplicate | review:
            continue
        options = [t for t in pix_options(e) if not t['bank_ids']]
        sums = [p for p in combinations(options, 2) if sum(t['cents'] for t in p)==-e['cents']]
        pairs = [p for p in sums if p[0]['beneficiary_key']==p[1]['beneficiary_key']]
        if len(pairs)==1 and len(sums)==1:
            for t in pairs[0]:
                match(t, e, 'matched_aggregate', 'medium', 'same_employee_two_title_sum', t['cents'])
            used.add(e['bank_id'])
        elif sums:
            flag(e, options, 'ambiguous_or_different_employee_aggregate')

    for e in pix:
        if e['bank_id'] in used | duplicate | review:
            continue
        options = [t for t in pix_options(e) if not t['bank_ids']
                   and abs(-e['cents']-t['cents']) <= cents(config['pix_difference_tolerance_brl'])]
        if len(options)==1:
            match(options[0], e, 'matched_with_difference', 'medium', 'unique_pix_within_tolerance', -e['cents'])
            used.add(e['bank_id'])
        elif options:
            flag(e, options, 'ambiguous_pix_difference')

    invoices = [t for t in titles if t['kind']=='FATURA_FORNECEDOR']
    for e in (e for e in debits if norm(e['description']).startswith('SISPAG BOLETO UBER')):
        if e['bank_id'] in used | duplicate | review:
            continue
        window = [t for t in invoices if t['cents'] is not None and t['cents']>0
                  and in_window(e, t, config['invoice_days_before_due'], config['invoice_days_after_due'])]
        exact = [t for t in window if t['cents']==-e['cents']]
        options = exact or window
        if len(options)!=1:
            if options:
                flag(e, options, 'ambiguous_invoice_window')
            continue
        t = options[0]
        difference = -e['cents']-t['cents']
        if t['bank_ids']:
            flag(e, [t], 'additional_boleto_requires_review')
        elif (abs(difference)>cents(config['invoice_max_difference_brl'])
              or Decimal(abs(difference))/t['cents']>Decimal(config['invoice_max_difference_ratio'])):
            flag(e, [t], 'invoice_difference_exceeds_review_threshold')
        else:
            match(t, e, 'matched_exact' if difference==0 else 'matched_with_difference',
                  'high' if difference==0 else 'medium', 'unique_uber_boleto_within_configured_thresholds', -e['cents'])
            used.add(e['bank_id'])

    visa_matches = []
    for e in debits:
        if e['bank_id'] in used | duplicate | review or not e['description'].upper().startswith('UBER *TRIP'):
            continue
        options = [v for v in visa_rows if v['cents']==-e['cents']
                   and abs((e['date']-v['date']).days)<=config['card_days_from_ride']]
        if len(options)==1 and not any(m['source_transaction_id']==options[0]['id'] for m in visa_matches):
            v=options[0]
            visa_matches.append(dict(source_transaction_id=v['id'], trip_id=v['trip_id'], bank_id=e['bank_id'],
                                     value=money(v['cents']), status='card_debit_matched_classification_pending', confidence='medium'))
            used.add(e['bank_id'])
    for t in titles:
        if t['primary_status']=='unmatched':
            t['primary_status']='needs_review' if t['review_candidates'] else 'open_as_of_statement_end'
            t['rule']='ambiguous_or_material_bank_candidate' if t['review_candidates'] else 'no_bank_debit_identified_in_statement'
        t['status']='paid_more_than_once' if t['duplicate_bank_ids'] else t['primary_status']
    unmatched=[]
    for e in debits:
        if e['bank_id'] in used:
            continue
        category = ('duplicate_payment' if e['bank_id'] in duplicate else
                    'needs_review' if e['bank_id'] in review else
                    'unmatched_uber_or_pix_debit' if e['description'].upper().startswith('PIX TRANSF') or 'UBER' in e['description'].upper()
                    else 'outside_uber_ap_scope')
        unmatched.append({**e, 'category': category})
    validate_allocations(titles, entries)
    return titles, visa_matches, unmatched


def validate_allocations(titles, entries):
    allocated=defaultdict(int)
    duplicates=set()
    by_id={e['bank_id']:e for e in entries}
    for t in titles:
        for bid in t['bank_ids']:
            allocated[bid] += t['paid_cents']
        for bid in t['duplicate_bank_ids']:
            if bid in duplicates:
                raise ValueError('Movimento duplicado atribuído a dois títulos')
            duplicates.add(bid)
    if duplicates & allocated.keys():
        raise ValueError('Pagamento principal também classificado como duplicado')
    for bid, amount in allocated.items():
        if amount != -by_id[bid]['cents']:
            raise ValueError(f'Atribuições não fecham o movimento bancário: {bid}')


def report_rows(titles, entries):
    by_id={e['bank_id']:e for e in entries}
    title_rows, pairs, reviews=[], [], []
    for t in titles:
        title_rows.append(dict(
            id_externo=t['id'], tipo=t['kind'], competencia=t['competence'], beneficiario=t['name'],
            matricula=t.get('beneficiary_key') or '', num_documento=t['document'], vencimento=str(t['due'] or ''),
            valor_titulo=money(t['cents']), valor_pagamento_principal=money(t['paid_cents']),
            valor_pagamento_duplicado=money(t['duplicate_cents']),
            valor_bancario_atribuido_total=money(t['paid_cents']+t['duplicate_cents']) if t['paid_cents'] is not None else '',
            diferenca_pagamento_principal=money(t['difference_cents']),
            diferenca_incluindo_duplicidade=money(t['difference_cents']+t['duplicate_cents']) if t['difference_cents'] is not None else '',
            status=t['status'], status_pagamento_principal=t['primary_status'], confianca=t['confidence'], regra=t['rule'],
            bank_ids='|'.join(t['bank_ids']), bank_ids_duplicados='|'.join(t['duplicate_bank_ids']),
            status_importacao='retido' if t['blockers'] else 'liberado', bloqueios_ap='|'.join(t['blockers']),
            busca_bancaria='nao_avaliavel' if t['primary_status']=='not_assessable' else 'realizada',
            erp_baixa_confirmada='nao_verificada'))
        for kind, ids in [('principal',t['bank_ids']),('duplicado',t['duplicate_bank_ids'])]:
            for bid in ids:
                e=by_id[bid]
                pairs.append(dict(id_externo=t['id'], bank_id=bid, bank_date=str(e['date']),
                                  bank_description=e['description'], tipo_vinculo=kind,
                                  valor_atribuido_titulo=money(t['paid_cents'] if kind=='principal' else -e['cents']),
                                  confianca=t['confidence'], regra=t['rule']))
        for c in t['review_candidates']:
            reviews.append(dict(id_externo=t['id'], bank_id=c['bank_id'], motivo=c['reason']))
    return title_rows, pairs, reviews


def write_csv(path, rows, columns):
    with path.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def write_summary(out, titles, entries, visa_matches, unmatched, pipeline_summary, bank_path):
    end, end_basis = statement_end(bank_path, entries)
    rules=json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
    rr=[t for t in titles if t['kind']=='REEMBOLSO_COLABORADOR']
    summary=dict(schema_version=2, bank_file_sha256=hashlib.sha256(bank_path.read_bytes()).hexdigest(),
                 reconciliation_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 rules_sha256=hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest(),
                 pipeline_code_sha256=pipeline_summary['code_sha256'],
                 pipeline_run_summary_sha256=hashlib.sha256(json.dumps(pipeline_summary,sort_keys=True).encode()).hexdigest(),
                 statement_end=str(end), statement_end_basis=end_basis,
                 last_movement_date=str(max(e['date'] for e in entries)),
                 title_status_counts=dict(sorted(Counter(t['status'] for t in titles).items())),
                 primary_status_counts=dict(sorted(Counter(t['primary_status'] for t in titles).items())),
                 unmatched_debit_counts=dict(sorted(Counter(e['category'] for e in unmatched).items())),
                 paid_more_than_once_title_count=sum(bool(t['duplicate_bank_ids']) for t in titles),
                 visa_route_match_count=len(visa_matches), bank_movement_count=len(entries),
                 reimbursement_title_total=money(sum(t['cents'] for t in rr if t['cents'] is not None)),
                 reimbursement_primary_payments=money(sum(t['paid_cents'] or 0 for t in rr)),
                 reimbursement_duplicate_payments=money(sum(t['duplicate_cents'] for t in rr)),
                 note='Valor vazio: sem pagamento associado ou não avaliável. Diferença zero: pagamento principal fecha o título. Sem baixa automática no ERP.')
    (out/'bank_reconciliation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\r\n')
    lines=['# Conciliação bancária — leitura dos resultados','',
           f"Extrato até {summary['statement_end']}. Todos os candidatos com identidade, valor e vencimento são pesquisados, inclusive os retidos para importação.",'',
           '| Beneficiário | Competência | Título (BRL) | Principal atribuído (BRL) | Duplicado (BRL) | Situação |',
           '|---|---|---:|---:|---:|---|']
    for t in titles:
        lines.append(f"| {t['name']} | {t['competence']} | {money(t['cents']) or '—'} | {money(t['paid_cents']) or '—'} | {money(t['duplicate_cents'])} | {t['status']} |")
    lines += ['', 'Os valores atribuídos e duplicados são saídas de caixa positivas. Campo vazio/— não é zero.',
              'Diferença principal = pagamento atribuído menos título. A diferença incluindo duplicidade soma o pagamento excedente.',
              'N:1 atribui o PIX pelos valores dos dois títulos da mesma matrícula; não são dois pagamentos independentes.',
              '`bank_movements.csv` tem uma linha por movimento, com valor assinado. `bank_match_pairs.csv` informa o valor atribuído a cada título, que pode ser somado inclusive no N:1.',
              '`bank_review_candidates.csv` contém possibilidades não confirmadas, sem atribuição financeira.',
              'PIX: prefixo, valor e janela de vencimento; N:1 exige mesma matrícula. Homônimos ambíguos ficam para revisão.',
              f"Boletos: nome/canal e janela, com diferença limitada a R$ {rules['invoice_max_difference_brl']} e {Decimal(rules['invoice_max_difference_ratio'])*100}% simultaneamente. Tolerâncias técnicas não aprovam encargos ou baixas; excessos ficam em revisão.",
              'Alta confiança significa correspondência única pelas regras; o extrato não contém CPF ou identificador do ERP.',
              'Janelas e tolerâncias estão em `config/reconciliation.json`, e os hashes constam no resumo JSON.', '']
    (out/'README.md').write_text('\n'.join(lines),encoding='utf-8',newline='\r\n')
    return summary


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--pipeline-output',type=Path,default=ROOT/'output')
    parser.add_argument('--bank',type=Path,default=ROOT/'data/extrato_itau_cc_2026-07_a_2026-09.csv')
    parser.add_argument('--output',type=Path,default=ROOT/'reconciliation')
    args=parser.parse_args()
    out=args.output.resolve()
    if out.exists() and not (out/'.bank_reconciliation_output').is_file():
        parser.error('Pasta existente sem marcador de conciliação')
    entries=bank_entries(args.bank)
    if not entries:
        parser.error('Extrato sem movimentos')
    titles,visa=candidates(args.pipeline_output/'canonical.duckdb')
    titles,visa_matches,unmatched=reconcile(titles,visa,entries)
    title_rows,pairs,reviews=report_rows(titles,entries)
    pipeline_summary=json.loads((args.pipeline_output/'run_summary.json').read_text(encoding='utf-8'))
    out.mkdir(parents=True,exist_ok=True)
    (out/'.bank_reconciliation_output').write_text('Resultados reproduzíveis; sem baixa no ERP.\n',encoding='utf-8',newline='\r\n')
    write_csv(out/'bank_reconciliation.csv',title_rows,list(title_rows[0]) if title_rows else ['id_externo','valor_titulo','status'])
    write_csv(out/'bank_match_pairs.csv',pairs,['id_externo','bank_id','bank_date','bank_description','tipo_vinculo','valor_atribuido_titulo','confianca','regra'])
    write_csv(out/'bank_review_candidates.csv',reviews,['id_externo','bank_id','motivo'])
    write_csv(out/'bank_card_route_matches.csv',visa_matches,['source_transaction_id','trip_id','bank_id','value','status','confidence'])
    write_csv(out/'bank_unmatched_debits.csv',[
        dict(bank_id=e['bank_id'],source_file=e['source_file'],source_line=e['source_line'],date=str(e['date']),
             description=e['description'],value=money(e['cents']),category=e['category']) for e in unmatched
    ],['bank_id','source_file','source_line','date','description','value','category'])
    write_csv(out/'bank_movements.csv',[
        dict(bank_id=e['bank_id'],file_sha256=e['file_sha256'],source_file=e['source_file'],source_line=e['source_line'],
             date=str(e['date']),description=e['description'],origin=e['origin'],valor_movimento_bancario=money(e['cents']))
        for e in entries
    ],['bank_id','file_sha256','source_file','source_line','date','description','origin','valor_movimento_bancario'])
    print(json.dumps(write_summary(out,titles,entries,visa_matches,unmatched,pipeline_summary,args.bank),ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
