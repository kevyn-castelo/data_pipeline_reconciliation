"""Exploratory diagnostics only. No RAW warehouse, canonical contract or ERP outputs."""
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import csv
import hashlib
import json
from itertools import combinations
import re
import sys

from inspect_sources import ROOT, load_sources

D = Decimal
OUT = ROOT / 'profiling' / 'output'
OUT.mkdir(parents=True, exist_ok=True)
AUDIT = []
ISSUES = []


def dump(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding='utf-8')


def ref(s, r):
    return dict(source_file=s['file'], source_sheet=s['sheet'], source_row=r['row'],
                source_line_start=r.get('line_start'), source_line_end=r.get('line_end'))


def issue(code, domain, classification, location, **details):
    ISSUES.append(dict(code=code, domain=domain, classification=classification, **location, **details))


def audit(location, field, before, after, rule):
    if str(before) != str(after):
        AUDIT.append(dict(**location, field=field, before=before, after=str(after), rule=rule,
                          applied_to_source=False, scope='diagnostic comparison only'))
    return after


def norm(s):
    return ' '.join(s.split()).casefold()


ALIASES = {
    'surname': 'last name', 'programme': 'program', 'duration (mins)': 'duration (min)',
    'pick-up address': 'pickup address', 'transaction amount': 'transaction amount (local currency)',
    'local currency code': 'local currency', 'tip in brl (inclusive of taxes, if any)': 'tips in brl',
    'totals fare in brl': 'total fare in brl', 'other charges (local currency)': 'other charges',
    'uber fare invoice#': 'invoice number',
}


def field_key(s):
    return ALIASES.get(norm(s), norm(s))


def doc_digits(s):
    return re.sub(r'[.\-/\s]', '', s)


def valid_doc(s, n):
    v = doc_digits(s)
    if not v.isdigit() or len(v) != n or len(set(v)) == 1:
        return False
    weights = [list(range(10, 1, -1)), list(range(11, 1, -1))] if n == 11 else [
        [5,4,3,2,9,8,7,6,5,4,3,2], [6,5,4,3,2,9,8,7,6,5,4,3,2]]
    for i, w in enumerate(weights):
        rem = sum(int(a)*b for a,b in zip(v[:n-2+i], w)) % 11
        if int(v[n-2+i]) != (0 if rem < 2 else 11-rem):
            return False
    return True


def money(v, comma=False):
    return D(v.replace('.', '').replace(',', '.') if comma else v)


def cents(v):
    return v.quantize(D('.01'), rounding=ROUND_HALF_UP)


def dt_parse(v, kind, layout):
    if layout == 'billing_xlsx':
        seconds = (D(v) * D(86400)).quantize(D(1), rounding=ROUND_HALF_UP)
        return datetime(1899, 12, 30) + timedelta(seconds=int(seconds))
    if kind == 'timestamp':
        return datetime.strptime(v, '%d/%m/%y %H:%M' if layout == 'adhoc_us' else '%d/%m/%Y %H:%M')
    if kind == 'date':
        return datetime.strptime(v, '%m/%d/%Y' if layout == 'adhoc_us' else '%d/%m/%Y')
    return datetime.strptime(v, '%I:%M %p' if layout == 'adhoc_us' else '%H:%M')


def offset_minutes(v):
    parts = v.lstrip('+-').split(':')
    return (-1 if v.startswith('-') else 1) * (int(parts[0])*60 + int(parts[1]))


def groups(rows, key):
    result = defaultdict(list)
    for row in rows:
        result[key(row)].append(row)
    return result


def totals(rows):
    return dict(n=len(rows), brl=str(amount_sum(rows)), missing_brl=sum(r['amount'] is None for r in rows))


def amount_sum(rows, field='amount'):
    return sum((r[field] for r in rows if r[field] is not None), D(0))


def signature(row):
    return (row['trip'], row['ts'], row['type'])


def brief(row):
    return dict(**row['ref'], trip_id=row['trip'], timestamp=row['ts'], transaction_type=row['type'],
                amount=row['amount'], email=row['email'], payment=row['payment'], expense=row['expense'])


def main():
    sources = load_sources()
    dump('source_snapshot.json', sources)
    tables, inventory, records, schema = {}, [], [], []
    for s in sources:
        rs = s['rows']
        header = next((r for r in rs if 'Trip/Eats ID' in r['values']), None)
        if header:
            layout = 'billing_xlsx' if 'Programme' in header['values'] else ('adhoc_pt' if s.get('delimiter') == ';' else 'adhoc_us')
            headers = header['values']
            tx = []
            for r in rs:
                if r['row'] <= header['row']:
                    continue
                if not any(r['values']) or any(v.startswith('*Conditional') for v in r['values']):
                    continue
                if len(r['values']) != len(headers):
                    issue('MALFORMED_ROW', 'DATA_QUALITY', 'RULE_BASED', ref(s,r), width=len(r['values']))
                    continue
                tx.append(r)
            for position,h in enumerate(headers,1):
                schema.append(dict(file=s['file'],sheet=s['sheet'],layout=layout,position=position,original=h,comparison_field=field_key(h)))
            for r in tx:
                loc = ref(s,r)
                loc['source_layout'] = layout
                raw = {field_key(k):v for k,v in zip(headers,r['values'])}
                vals = {}
                for k,v in raw.items():
                    nv = v.strip()
                    if k == 'email':
                        nv = nv.casefold()
                    vals[k] = audit(loc,k,v,nv,'TRIM_AND_EMAIL_CASE')
                p = dict(ref=loc,raw=raw,normalized=vals,raw_values=r['values'],trip=vals['trip/eats id'],type=vals['transaction type'])
                for k,v in vals.items():
                    if (any(token in k for token in ['fare','fee','tax','tip','amount','charge','saving','discount','payments'])
                            and not any(token in k for token in ['invoice','partner name','partner address','tax id'])
                            and v not in ('','--')):
                        try:
                            value = money(v,layout=='adhoc_pt')
                        except Exception as exc:
                            issue('NUMERIC_PARSE_ERROR','DATA_QUALITY','RULE_BASED',loc,field=k,value=v,error=str(exc))
                            continue
                        audit(loc,k,v,str(value),'DECIMAL_LOCALE_PARSE')
                        if value != cents(value):
                            issue('SUBCENT_SOURCE_VALUE','DATA_QUALITY','AUTO_FIXABLE',loc,field=k,before=v,
                                  diagnostic_cents=str(cents(value)),delta=str(cents(value)-value),applied=False)
                            audit(loc,k,str(value),cents(value),'DIAGNOSTIC_CENTS_HALF_UP_NOT_APPROVED_CONTRACT')
                        vals[k] = str(cents(value))
                p['amount_lexeme'] = money(raw['transaction amount in brl'],layout=='adhoc_pt') if raw['transaction amount in brl'].strip() not in ('','--') else None
                p['amount'] = cents(p['amount_lexeme']) if p['amount_lexeme'] is not None else None
                p['employee_paid'] = D(vals['payments made by employees/guests in brl']) if vals['payments made by employees/guests in brl'] not in ('','--') else None
                if p['amount'] is None:
                    issue('BRL_AMOUNT_MISSING','FINANCIAL_VALIDATION','RULE_BASED',loc,currency=vals['local currency'])
                p.update(email=vals['email'],expense=vals['expense code'],payment=vals['payment method'],
                         service=vals['service'],program=vals['program'],country=vals['country'])
                p['ts'] = dt_parse(raw['transaction timestamp (utc)'],'timestamp',layout)
                audit(loc,'transaction timestamp (utc)',raw['transaction timestamp (utc)'],p['ts'].isoformat(),'LAYOUT_DATE_PARSE_SECOND_RESOLUTION')
                vals['transaction timestamp (utc)'] = p['ts'].isoformat()
                for prefix in ['request','drop-off']:
                    for zone in ['utc','local']:
                        dk,tk = f'{prefix} date ({zone})',f'{prefix} time ({zone})'
                        date = dt_parse(raw[dk],'date',layout).date()
                        time = dt_parse(raw[tk],'time',layout).time()
                        p[f'{prefix}_{zone}'] = datetime.combine(date,time)
                        vals[dk] = audit(loc,dk,raw[dk],date.isoformat(),'LAYOUT_DATE_PARSE')
                        vals[tk] = audit(loc,tk,raw[tk],time.isoformat(),'LAYOUT_TIME_PARSE_SECOND_RESOLUTION')
                p['offset'] = offset_minutes(raw['request timezone offset from utc'])
                vals['request timezone offset from utc'] = audit(loc,'request timezone offset from utc',raw['request timezone offset from utc'],p['offset'],'OFFSET_MINUTES_COMPARISON')
                for k in ['distance (mi)','duration (min)']:
                    vals[k] = audit(loc,k,raw[k],str(cents(money(raw[k],layout=='adhoc_pt'))),'NUMERIC_COMPARISON_TWO_DECIMALS')
                for prefix in ['request','drop-off']:
                    if p[f'{prefix}_utc'] + timedelta(minutes=p['offset']) != p[f'{prefix}_local']:
                        issue('UTC_LOCAL_OFFSET_MISMATCH','DATA_QUALITY','RULE_BASED',loc,field=prefix)
                if p['drop-off_utc'] < p['request_utc']:
                    issue('NEGATIVE_DURATION','DATA_QUALITY','RULE_BASED',loc,request=p['request_utc'],dropoff=p['drop-off_utc'])
                if p['ts'] < p['request_utc']:
                    issue('TRANSACTION_BEFORE_REQUEST','DATA_QUALITY','RULE_BASED',loc,request=p['request_utc'],transaction=p['ts'])
                if p['amount'] is not None and vals['local currency']=='BRL' and D(vals['transaction amount (local currency)'])!=p['amount']:
                    issue('BRL_LOCAL_AMOUNT_CONFLICT','FINANCIAL_VALIDATION','RULE_BASED',loc,
                          transaction_brl=p['amount'],transaction_local=vals['transaction amount (local currency)'])
                if layout=='billing_xlsx' and raw['uber fare invoice date'] not in ('','--'):
                    invoice_date=dt_parse(raw['uber fare invoice date'],'date',layout).date()
                    audit(loc,'uber fare invoice date',raw['uber fare invoice date'],invoice_date.isoformat(),'EXCEL_DATE_PARSE')
                    report_date=datetime.fromisoformat(s['rows'][1]['values'][1]).date()
                    if invoice_date>report_date:
                        issue('RIDE_INVOICE_DATE_AFTER_EXPORT','DATA_QUALITY','NEEDS_CLIENT',loc,invoice_date=invoice_date,export_date=report_date)
                p['record_hash'] = hashlib.sha256(json.dumps(r['values'],ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
                records.append(p)
            inventory.append(dict(file=s['file'],sheet=s['sheet'],layout=layout,encoding=s.get('encoding','XLSX/XML'),delimiter=s.get('delimiter'),
                                  sha256=s['sha256'],bytes=s['bytes'],rows=len(rs),physical_lines=s.get('physical_lines'),columns=len(headers),
                                  header_row=header['row'],header_line_start=header.get('line_start'),header_line_end=header.get('line_end'),
                                  data_rows=len(tx),nondata_rows=[r['row'] for r in rs if r not in tx],schema=headers))
        else:
            hi = 1 if s['sheet']=='Resumo' else (4 if 'extrato_' in s['file'] else 0)
            headers = rs[hi]['values']
            table = [dict(zip(headers,r['values']),_ref=ref(s,r)) for r in rs[hi+1:]]
            tables[s['file'].split('/')[-1] + (':Resumo' if s['sheet']=='Resumo' else '')] = table
            inventory.append(dict(file=s['file'],sheet=s['sheet'],encoding=s.get('encoding','XLSX/XML'),delimiter=s.get('delimiter'),
                                  sha256=s['sha256'],bytes=s['bytes'],rows=len(rs),physical_lines=s.get('physical_lines'),columns=len(headers),
                                  header_row=rs[hi]['row'],data_rows=len(table),schema=headers))
        for r in rs:
            for i,v in enumerate(r['values']):
                if '\ufffd' in v:
                    issue('REPLACEMENT_CHARACTER_IN_SOURCE','DATA_QUALITY','NEEDS_CLIENT',ref(s,r),column=i+1,value=v)
                if v != v.strip():
                    audit(ref(s,r),f'column_{i+1}',v,v.strip(),'TRIM_PROPOSAL')
    dump('inventory.json',inventory)
    dump('schema_comparison.json',schema)
    grouped = groups(records,signature)
    common_fields = set.intersection(*(set(r['normalized']) for r in records))
    duplicates,conflicts,unique = [],[],[]
    for key, rr in grouped.items():
        unique.append(rr[0])  # Reference scenario only; all versions remain in evidence.
        if len(rr)>1:
            compared_fields=set.intersection(*(set(r['normalized']) for r in rr))
            diffs = {k:sorted(set(r['normalized'][k] for r in rr)) for k in sorted(compared_fields)
                     if len(set(r['normalized'][k] for r in rr))>1}
            entry = dict(key=key,rows=[brief(r) for r in rr],different_common_fields=diffs,
                         exact_raw=len(set(r['record_hash'] for r in rr))==1)
            duplicates.append(entry)
            if diffs:
                conflicts.append(entry)
            for r in rr:
                issue('CONFLICTING_CANDIDATE' if diffs else 'EQUIVALENT_OVERLAP','DATA_QUALITY',
                      'NEEDS_CLIENT' if diffs else 'AUTO_FIXABLE',r['ref'],candidate=key,other_occurrences=[x['ref'] for x in rr if x is not r])
    dump('duplicate_groups.json',duplicates)
    dump('conflicting_candidates.json',conflicts)
    per_file = groups(records,lambda r:r['ref']['source_file'])
    overlap=[]
    for (a,ar),(b,br) in combinations(per_file.items(),2):
        keys=set(map(signature,ar)) & set(map(signature,br))
        overlap.append(dict(a=a,b=b,trip_overlap=len(set(r['trip'] for r in ar)&set(r['trip'] for r in br)),key_overlap=len(keys),
                            raw_identical_hash_overlap=len(set(r['record_hash'] for r in ar)&set(r['record_hash'] for r in br))))
    metrics = dict(raw=totals(records),candidate_unique=totals(unique),common_fields=sorted(common_fields),
                   duplicate_groups=len(duplicates),excess_occurrences=len(records)-len(grouped),conflicting_groups=len(conflicts),overlap=overlap)
    metrics['files']={f:dict(**totals(rr),unique_candidate_keys=len(set(map(signature,rr))),
                           exact_extra=len(rr)-len(set(r['record_hash'] for r in rr)),
                           transaction_types=dict(Counter(r['type'] for r in rr)),
                           min_transaction=min(r['ts'] for r in rr),max_transaction=max(r['ts'] for r in rr),
                           min_ride=min(r['request_local'] for r in rr),max_ride=max(r['request_local'] for r in rr)) for f,rr in per_file.items()}
    metrics['key_candidates']={label:dict(distinct=len(g),groups_repeated=sum(len(v)>1 for v in g.values()),max_multiplicity=max(map(len,g.values()))) for label,g in [
        ('trip',groups(records,lambda r:r['trip'])),('trip_type',groups(records,lambda r:(r['trip'],r['type']))),
        ('trip_timestamp_type',grouped),('raw_row_hash',groups(records,lambda r:r['record_hash']))]}
    metrics['dimensions']={key:{k:totals(v) for k,v in groups(unique,lambda r:r[key]).items()} for key in ['type','payment','program','service','country','expense']}
    metrics['trip_multi_transactions']=[dict(trip_id=k,rows=[brief(r) for r in rr]) for k,rr in groups(unique,lambda r:r['trip']).items() if len(rr)>1]
    metrics['negative']=totals([r for r in unique if r['amount'] is not None and r['amount']<0])
    metrics['employee_paid']=dict(**totals([r for r in unique if r['employee_paid'] is not None and r['employee_paid']!=0]),paid_brl=amount_sum(unique,'employee_paid'))
    metrics['international']=[dict(**brief(r),country=r['country'],local_currency=r['normalized']['local currency'],local_amount=r['normalized']['transaction amount (local currency)'],offset=r['offset'],ride_local=r['request_local']) for r in unique if r['country']!='Brazil']
    metrics['month_boundaries']=[dict(**brief(r),ride_local=r['request_local']) for r in unique if r['ts'].strftime('%Y-%m') != r['request_local'].strftime('%Y-%m')]

    users=tables['usuarios_internos.csv']; employees=tables['funcionarios.xlsx']; ccs=tables['centros_de_custo.xlsx']
    employee_by_id={e['Matrícula']:e for e in employees}; cc_by_id={c['Código']:c for c in ccs}
    directory=defaultdict(list)
    for u in users:
        for method,addresses in [('primary',[u['email_principal']]),('alias',u['emails_alternativos'].split('|'))]:
            for address in addresses:
                if address:
                    clean=norm(address)
                    audit(u['_ref'],method,address,clean,'EMAIL_TRIM_CASE')
                    directory[clean].append((u,method))
    links=[]
    for email, rr in sorted(groups(unique,lambda r:r['email']).items()):
        matches=directory.get(email,[])
        ids=sorted(set(u['id_usuario'] for u,m in matches)); mats=sorted(set(u['matricula'] for u,m in matches))
        status='not_found' if not ids else ('ambiguous' if len(ids)>1 else 'linked')
        method='|'.join(sorted(set(m for u,m in matches))) if matches else 'none'
        e=employee_by_id.get(mats[0]) if len(mats)==1 else None
        link=dict(email=email,status=status,link_method=method,user_ids=ids,matriculas=mats,
                  employee_resolution='found' if e else 'missing',cost_center=e['Centro de Custo'] if e else None,
                  same_employee_multiple_users=len(ids)>1 and len(mats)==1,**totals(rr),rows=[brief(r) for r in rr])
        links.append(link)
        for r in rr:
            r['link_status']=status;r['employee']=e;r['link_method']=method
            if r['type']!='Admin Fee' and status!='linked':
                issue('USER_'+status.upper(),'DATA_QUALITY','NEEDS_CLIENT',r['ref'],email=email,user_ids=ids,matriculas=mats)
            if status=='linked' and e is None:
                issue('EMPLOYEE_NOT_FOUND','DATA_QUALITY','RULE_BASED',r['ref'],email=email,matriculas=mats)
            if e:
                cc=cc_by_id.get(e['Centro de Custo'])
                if not cc or cc['Ativo']!='S':
                    issue('COST_CENTER_MISSING' if not cc else 'COST_CENTER_INACTIVE','DATA_QUALITY','RULE_BASED',r['ref'],employee=e['Matrícula'],cost_center=e['Centro de Custo'])
                reported_id=r['normalized']['employee id']
                if reported_id not in ('','--',e['Matrícula']):
                    zero_variant=reported_id.isdigit() and reported_id.lstrip('0')==e['Matrícula']
                    issue('UBER_EMPLOYEE_ID_DIFFERS','DATA_QUALITY','AUTO_FIXABLE' if zero_variant else 'RULE_BASED',r['ref'],uber_id=reported_id,directory_employee=e['Matrícula'],format_only=zero_variant)
                    if zero_variant:
                        audit(r['ref'],'employee id',reported_id,e['Matrícula'],'ID_FORMAT_COMPARISON_AFTER_OFFICIAL_EMAIL_LINK_ONLY')
    dump('user_linking.json',links)
    master_findings={}
    for name,table,column in [('employees',employees,'Matrícula'),('users',users,'id_usuario'),('cc',ccs,'Código'),
                              ('accounting',tables['plano_de_contas.csv'],'codigo'),('managerial',tables['plano_gerencial.csv'],'codigo_gerencial'),
                              ('crosswalk',tables['de_para_contabil_gerencial.csv'],'conta_contabil'),('expense_mapping',tables['de_para_codigo_despesa.csv'],'codigo_despesa')]:
        master_findings[name+'_duplicate_keys']={k:v for k,v in groups(table,lambda r:r[column]).items() if len(v)>1}
    for name,table,column,n in [('employee_cpf',employees,'CPF',11),('vendor_cnpj',tables['fornecedores.xlsx'],'CNPJ',14)]:
        master_findings[name+'_invalid']=[r for r in table if not valid_doc(r[column],n)]
        master_findings[name+'_duplicates']={k:v for k,v in groups(table,lambda r:doc_digits(r[column])).items() if len(v)>1}
        for r in table:
            audit(r['_ref'],column,r[column],doc_digits(r[column]),'DOCUMENT_PUNCTUATION_REMOVAL_ONLY')
            if not valid_doc(r[column],n):
                issue('INVALID_'+name.upper(),'DATA_QUALITY','RULE_BASED',r['_ref'],value=r[column])
    master_findings['directory_email_collisions']={k:[dict(user=u['id_usuario'],matricula=u['matricula'],method=m,status=u['status'],ref=u['_ref']) for u,m in matches] for k,matches in directory.items() if len(set(u['id_usuario'] for u,m in matches))>1}
    master_findings['directory_cc_disagreements']=[dict(user=u['id_usuario'],matricula=u['matricula'],directory=u['centro_custo'],official=employee_by_id[u['matricula']]['Centro de Custo'],ref=u['_ref']) for u in users if u['matricula'] in employee_by_id and u['centro_custo']!=employee_by_id[u['matricula']]['Centro de Custo']]
    master_findings['directory_missing_employee']=[u for u in users if u['matricula'] not in employee_by_id]
    master_findings['employee_invalid_cc']=[e for e in employees if e['Centro de Custo'] not in cc_by_id or cc_by_id[e['Centro de Custo']]['Ativo']!='S']
    deps={r['CODIGO']:r for r in tables['departamentos.csv']}
    master_findings['department_invalid_cc']=[r for r in deps.values() if r['CENTRO_CUSTO_VINCULADO'] not in cc_by_id]
    master_findings['employee_missing_department']=[e for e in employees if e['Departamento'] not in deps]
    master_findings['employee_department_cc_disagreements']=[e['Matrícula'] for e in employees if e['Departamento'] in deps and e['Centro de Custo']!=deps[e['Departamento']]['CENTRO_CUSTO_VINCULADO']]
    master_findings['terminated']=[e for e in employees if e['Situação']!='Ativo']
    master_findings['names_repeated']={k:[e['Matrícula'] for e in v] for k,v in groups(employees,lambda r:r['Nome']).items() if len(v)>1}
    dump('master_findings.json',master_findings)

    accounts={r['codigo']:r for r in tables['plano_de_contas.csv']}; managerial={r['codigo_gerencial']:r for r in tables['plano_gerencial.csv']}
    crosswalk={r['conta_contabil']:r for r in tables['de_para_contabil_gerencial.csv']}
    mappings={r['codigo_despesa']:r for r in tables['de_para_codigo_despesa.csv']}
    accounting=[]
    for code,rr in sorted(groups(unique,lambda r:r['expense']).items()):
        mapping=mappings.get(code); problems=[]
        case_candidate=mappings.get(code.upper()) if not mapping else None
        if case_candidate:
            problems.append('EXPENSE_CODE_CASE_VARIANT')
            for r in rr:
                audit(r['ref'],'expense code',code,code.upper(),'UNIQUE_MAPPING_CASE_CANDIDATE_NOT_APPLIED')
        acct=accounts.get(mapping['conta_contabil']) if mapping else None
        cross=crosswalk.get(mapping['conta_contabil']) if mapping else None
        ger=managerial.get(cross['conta_gerencial']) if cross else None
        if not mapping and not case_candidate: problems.append('EXPENSE_CODE_MISSING_OR_UNKNOWN')
        if mapping and not acct: problems.append('ACCOUNT_NOT_FOUND')
        if acct and acct['aceita_lancamento']!='S': problems.append('ACCOUNT_NOT_POSTABLE')
        if mapping and not cross: problems.append('OFFICIAL_CROSSWALK_MISSING')
        if cross and not ger: problems.append('MANAGERIAL_ACCOUNT_MISSING')
        if ger and ger['aceita_lancamento']!='S': problems.append('MANAGERIAL_NOT_POSTABLE')
        if cross and mapping['conta_gerencial_sugerida']!=cross['conta_gerencial']: problems.append('SUGGESTED_MANAGERIAL_CONFLICT')
        accounting.append(dict(code=code,mapping=mapping,official_crosswalk=cross,problems=problems,**totals(rr),
                               by_payment={k:totals(v) for k,v in groups(rr,lambda r:r['payment']).items()}))
        for r in rr:
            for problem in problems:
                issue(problem,'DATA_QUALITY' if problem=='EXPENSE_CODE_CASE_VARIANT' else 'FINANCIAL_VALIDATION',
                      'AUTO_FIXABLE' if problem=='EXPENSE_CODE_CASE_VARIANT' else 'RULE_BASED',r['ref'],expense=code)
    metrics['accounting']=accounting
    metrics['crosswalk_invalid_references']=[r for r in crosswalk.values() if r['conta_contabil'] not in accounts or r['conta_gerencial'] not in managerial]
    metrics['postable_parent_accounts']=[r for k,r in accounts.items() if r['aceita_lancamento']=='S' and any(a.startswith(k+'.') for a in accounts)]
    metrics['postable_parent_managerial']=[r for k,r in managerial.items() if r['aceita_lancamento']=='S' and any(a.startswith(k+'.') for a in managerial)]
    metrics['postable_account_missing_crosswalk']=[r for k,r in accounts.items() if r['aceita_lancamento']=='S' and k not in crosswalk]
    cards=tables['cartoes_corporativos.csv']
    metrics['card_collisions']={k:v for k,v in groups(cards,lambda r:(r['bandeira'],r['final'])).items() if len(v)>1}
    card_index={(r['bandeira'],r['final']):r for r in cards}
    for r in unique:
        if r['payment']=='Periodic Billing': r['payment_class']='periodic'
        else:
            match=re.fullmatch(r'(.+?)\s*-\s*(\d{4})',r['payment'])
            card=card_index.get((match[1],match[2])) if match else None
            r['payment_class']='corporate:'+card['tipo'] if card else ('personal' if match else 'unknown')
    metrics['payment_classes']={k:totals(v) for k,v in groups(unique,lambda r:r['payment_class']).items()}
    metrics['personal_employee_months']=[dict(employee=k[0],month=k[1],**totals(rr),invalid_cpf=not valid_doc(rr[0]['employee']['CPF'],11)) for k,rr in groups([r for r in unique if r['payment_class']=='personal' and r['employee']],lambda r:(r['employee']['Matrícula'],r['request_local'].strftime('%Y-%m'))).items()]

    reconciliation=[]
    for s in tables['demonstrativo_mensal_uber.csv']:
        period=datetime.strptime(s['periodo_inicio'],'%d/%m/%Y').strftime('%Y-%m')
        rr=[r for r in unique if r['payment']=='Periodic Billing' and r['ts'].strftime('%Y-%m')==period]
        raw_rr=[r for r in records if r['payment']=='Periodic Billing' and r['ts'].strftime('%Y-%m')==period]
        total=money(s['valor_total'],True); detail=amount_sum(rr)
        reconciliation.append(dict(period=period,statement=s,statement_valid_cnpj=valid_doc(s['cnpj_emitente'],14),
                                   diagnostic_only=True,scenario='Original July versions for conflicting candidates; no winner elected',
                                   header_balances=money(s['cobrancas_usuario'],True)+money(s['taxas_servico'],True)==total,
                                   raw_detail=amount_sum(raw_rr),detail=detail,missing_brl=sum(r['amount'] is None for r in rr),
                                   detail_lexeme=amount_sum(rr,'amount_lexeme'),difference=total-detail,
                                   user_charges=amount_sum([r for r in rr if r['type']!='Admin Fee']),
                                   admin_fee=amount_sum([r for r in rr if r['type']=='Admin Fee']),
                                   n=len(rr),by_file={k:totals(v) for k,v in groups(raw_rr,lambda r:r['ref']['source_file']).items()}))
    dump('statement_reconciliation.json',reconciliation)
    policies=[]
    for r in unique:
        if r['type']=='Admin Fee': continue
        e=r['employee']; flags=[]
        if r['service']=='Travel | Black':
            flags.append(('BLACK_OUTSIDE_CC101','VIOLATION') if e and e['Centro de Custo']!='CC101' else ('BLACK_IDENTITY_UNKNOWN','REVIEW_REQUIRED') if not e else ('',''))
        temporal_valid=r['ts']>=r['request_utc'] and r['drop-off_utc']>=r['request_utc']
        if not temporal_valid: flags.append(('POLICY_DATE_UNRELIABLE','REVIEW_REQUIRED'))
        if temporal_valid and r['request_local'].weekday()>=5 and r['program'] not in ('Transporte Turno Noturno','Refeicao Hora Extra'):
            flags.append(('WEEKEND_PROGRAM','VIOLATION'))
        if r['service']=='Eats' and r['program']!='Refeicao Hora Extra': flags.append(('EATS_PROGRAM','VIOLATION'))
        if r['service']=='Eats' and r['amount'] is not None and r['amount']>80: flags.append(('EATS_TRANSACTION_ABOVE_80','VIOLATION'))
        if r['expense'] not in mappings and r['expense'].upper() not in mappings: flags.append(('EXPENSE_CODE','VIOLATION'))
        if r['payment_class']=='personal': flags.append(('PERSONAL_CARD','REVIEW_REQUIRED'))
        if e and e['Data Desligamento'] and r['request_local'].date()>=datetime.strptime(e['Data Desligamento'],'%d/%m/%Y').date():
            flags.append(('USE_ON_OR_AFTER_TERMINATION','VIOLATION'))
        for flag,status in flags:
            if flag: policies.append(dict(**brief(r),policy_code=flag,review_status=status,blocks_payable=False))
    dump('policy_diagnostics.json',policies)
    metrics['policy_counts']=dict(Counter(r['policy_code'] for r in policies))
    metrics['central']=[dict(**brief(r),service=r['service'],program=r['program'],memo=r['normalized']['expense memo'],conditional=r['normalized']['conditional columns'],first=r['normalized']['first name'],last=r['normalized']['last name']) for r in unique if 'central' in (r['service']+' '+r['program']).lower() or r['normalized']['conditional columns'] not in ('','--')]
    metrics['amount_equation_failures']=[brief(r) for r in unique if r['amount'] is not None and r['employee_paid'] is not None and D(r['normalized']['total fare in brl'])-r['employee_paid']!=r['amount']]
    metrics['linking_summary']={k:dict(emails=len(ll),transactions=sum(l['n'] for l in ll),brl=sum((D(l['brl']) for l in ll),D(0))) for k,ll in groups(links,lambda l:l['status']+' / '+l['link_method']).items()}
    metrics['subcent_amount_count']=sum(r['amount']!=r['amount_lexeme'] for r in records)
    conflict_keys={tuple(c['key']) for c in conflicts}
    # A reference total is NOT an elected winner or deduplicated production output.
    metrics['reference_scenario']='First observed version in sorted sources. Conflicts unresolved; see bounds and all variants.'
    metrics['conflict_amount_bounds']={period:dict(
        nonconflicting_known_brl=amount_sum([r for r in unique if signature(r) not in conflict_keys and r['ts'].strftime('%Y-%m')==period and r['payment']=='Periodic Billing']),
        conflict_min=sum((min(r['amount'] for r in rr) for key,rr in grouped.items() if key in conflict_keys and rr[0]['ts'].strftime('%Y-%m')==period),D(0)),
        conflict_max=sum((max(r['amount'] for r in rr) for key,rr in grouped.items() if key in conflict_keys and rr[0]['ts'].strftime('%Y-%m')==period),D(0))) for period in ('2026-07','2026-08')}
    metrics['complement_only']=[brief(r) for r in unique if 'complemento' in r['ref']['source_file']]
    metrics['email_raw_distinct']=len(set(r['raw']['email'] for r in records))
    metrics['email_normalized_distinct']=len(set(r['email'] for r in records))
    metrics['alias_only']=[{k:v for k,v in l.items() if k!='rows'} for l in links if l['link_method']=='alias' and l['status']=='linked']
    metrics['central_requesters']=[]
    for r in unique:
        if r['program']=='Uber Central - Convidados':
            match=re.search(r'Solicitado por:\s*(\S+)',r['normalized']['conditional columns'])
            email=norm(match[1]) if match else None
            targets=directory.get(email,[])
            metrics['central_requesters'].append(dict(**brief(r),requester_email=email,
                requester_users=sorted(set(u['id_usuario'] for u,m in targets)),
                requester_employees=sorted(set(u['matricula'] for u,m in targets))))
    for key in ['postable_parent_accounts','postable_parent_managerial']:
        for row in metrics[key]:
            issue('POSTABLE_PARENT_CONTRADICTS_ANALYTIC_DESCRIPTION','FINANCIAL_VALIDATION','NEEDS_CLIENT',row['_ref'],account=row)
    for row in master_findings['directory_cc_disagreements']:
        issue('DIRECTORY_CC_DISAGREES_WITH_HR','DATA_QUALITY','RULE_BASED',row['ref'],directory=row['directory'],official=row['official'])
    for k,rr in master_findings['vendor_cnpj_duplicates'].items():
        for row in rr:
            issue('DUPLICATE_VENDOR_CNPJ_CONFLICT','DATA_QUALITY','NEEDS_CLIENT',row['_ref'],cnpj=k)
    for row in master_findings['department_invalid_cc']:
        issue('DEPARTMENT_REFERENCE_CC_MISSING','DATA_QUALITY','RULE_BASED',row['_ref'],cost_center=row['CENTRO_CUSTO_VINCULADO'])
    for recon in reconciliation:
        issue('STATEMENT_NOT_RELEASABLE','FINANCIAL_VALIDATION','RULE_BASED',recon['statement']['_ref'],period=recon['period'],known_difference=recon['difference'],
              reason='Unresolved conflicts and invalid allocation dimensions' if recon['period']=='2026-07' else 'Incomplete BRL detail and invalid allocation dimensions')
    summary=tables['uber_business_2026-08.xlsx:Resumo']
    group_rows=[r for r in summary if r['Group']!='TOTAL']
    total_row=next(r for r in summary if r['Group']=='TOTAL')
    metrics['manual_summary']=dict(group_count=sum(int(r['Qtd']) for r in group_rows),
        group_brl=sum(D(r['Total BRL']) for r in group_rows),total_count=int(total_row['Qtd']),total_brl=D(total_row['Total BRL']))
    issue('MANUAL_SUMMARY_DOES_NOT_SUM','DATA_QUALITY','RULE_BASED',total_row['_ref'],**metrics['manual_summary'])
    bank=tables['extrato_itau_cc_2026-07_a_2026-09.csv']
    metrics['bank_inventory']=dict(movements=sum(bool(r['valor (R$)']) for r in bank),balance_rows=sum(bool(r['saldo (R$)']) for r in bank))
    # Validate all bank fields without matching payments to payables.
    for row in bank:
        datetime.strptime(row['data'],'%d/%m/%Y')
        for field in ['valor (R$)','saldo (R$)']:
            if row[field]: money(row[field],True)
    for row in employees:
        datetime.strptime(row['Data Admissão'],'%d/%m/%Y')
        if row['Data Desligamento']: datetime.strptime(row['Data Desligamento'],'%d/%m/%Y')
    metrics['partner_tax_ids']={value:valid_doc(value,14) for r in records for value in [r['raw'].get('partner tax id','--')] if value not in ('','--')}
    metrics['card_users']={k:sorted(set(r['email'] for r in rr)) for k,rr in groups(unique,lambda r:r['payment']).items() if k!='Periodic Billing'}
    requester_by_ref={(r['source_file'],r['source_sheet'],r['source_row']):r for r in metrics['central_requesters']}
    for item in ISSUES:
        if item['code']=='USER_NOT_FOUND':
            requester=requester_by_ref.get((item['source_file'],item['source_sheet'],item['source_row']))
            item['assessment_stage']='direct_email_only'
            item['resolution']='RESOLVED_FROM_DATA_BY_REQUESTER' if requester and len(requester['requester_users'])==1 else 'NEEDS_CLIENT'
    # Per-column profiles cover ALL rows in every input, including the manual summary and bank.
    column_profiles=[]
    for s,inv in zip(sources,inventory):
        rows=[r for r in s['rows'] if r['row']>inv['header_row'] and r['row'] not in inv.get('nondata_rows',[])]
        for col,h in enumerate(inv['schema']):
            vs=[r['values'][col] if col<len(r['values']) else '' for r in rows]
            counts=Counter(vs)
            kinds=Counter(r.get('cell_types',['text']*len(r['values']))[col] if col<len(r['values']) else 'absent' for r in rows)
            column_profiles.append(dict(file=s['file'],sheet=s['sheet'],column=h,rows=len(vs),empty=counts[''],placeholder=counts['--'],
                                        distinct=len(counts),storage_types=dict(kinds),values=dict(sorted(counts.items()))))
    dump('column_profiles.json',column_profiles)
    metrics['issue_counts']=dict(Counter(i['code'] for i in ISSUES))
    dump('metrics.json',metrics)
    dump('diagnostic_interpretations.json',AUDIT)
    dump('issues.json',ISSUES)
    dump('transaction_evidence.json',[dict(**brief(r),candidate_key=signature(r),record_hash=r['record_hash'],
                                          amount_original=r['amount_lexeme'],employee_paid=r['employee_paid'],
                                          ride_local=r['request_local'],ride_utc=r['request_utc'],source_system='Uber for Business') for r in records])
    dump('input_manifest.json', {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(list((ROOT/'data').glob('*'))+[ROOT/n for n in ['TASK.md','README.md','politica_mobilidade.md','layout_importacao_contas_a_pagar.md']]) if p.is_file()})
    print(json.dumps({k:v for k,v in metrics.items() if k in ['raw','candidate_unique','duplicate_groups','excess_occurrences','conflicting_groups','policy_counts']},ensure_ascii=False,indent=2,default=str))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
