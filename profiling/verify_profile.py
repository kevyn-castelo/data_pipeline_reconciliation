"""Independent readers + exact arithmetic + unchanged sources + repeatability."""
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'profiling' / 'output'


def read(name):
    return json.loads((OUT/name).read_text(encoding='utf-8'))


def hashes(paths):
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def main():
    inventory=read('inventory.json')
    source_paths=sorted((ROOT/'data').glob('*'))+[ROOT/n for n in ('TASK.md','README.md','politica_mobilidade.md','layout_importacao_contas_a_pagar.md')]
    before=hashes(source_paths)
    independent=[]
    for item in inventory:
        path=ROOT/item['file']
        if path.suffix=='.csv':
            df=pd.read_csv(path,encoding=item['encoding'],sep=item['delimiter'],header=item['header_row']-1,
                           dtype=str,keep_default_na=False,skip_blank_lines=False)
            if 'layout' in item:
                df=df[df['Trip/Eats ID'].str.fullmatch(r'[0-9a-f-]{36}')]
                assert len(df)==item['data_rows'], item['file']
                column='Transaction Amount in BRL'
                values=df[column].map(lambda v:D(v.replace('.','').replace(',','.')) if item['delimiter']==';' else D(v))
                independent.append(dict(file=item['file'],rows=len(df),brl=str(sum(values,D(0)))))
            else:
                assert len(df)==item['data_rows'], item['file']
        else:
            wb=openpyxl.load_workbook(path,read_only=True,data_only=False)
            ws=wb[item['sheet']]
            assert ws.max_row==item['rows'] and ws.max_column==item['columns'],item
            if item['sheet']=='BR':
                assert ws['E62'].value.date().isoformat()=='2026-10-03'
                assert ws['AX7'].value.date().isoformat()=='2026-09-02'
                assert ws['AV190'].value is None
            wb.close()
    metrics=read('metrics.json');recon=read('statement_reconciliation.json')
    assert sum(item['n'] for item in metrics['files'].values())==metrics['raw']['n']==588
    assert sum(D(item['brl']) for item in metrics['files'].values())==D(metrics['raw']['brl'])
    assert metrics['raw']['n']-metrics['excess_occurrences']==metrics['candidate_unique']['n']==573
    assert sum(D(x['brl']) for x in metrics['payment_classes'].values())==D(metrics['candidate_unique']['brl'])
    assert metrics['conflicting_groups']==2
    assert D(recon[0]['by_file']['data/uber_business_2026-07.csv']['brl'])+D('136.99')==D(recon[0]['detail'])
    assert D(recon[1]['by_file']['data/uber_business_2026-08.xlsx']['brl'])-D('201.97')==D(recon[1]['detail'])
    assert D(recon[1]['difference'])==D('104.56') and recon[1]['missing_brl']==1
    assert metrics['manual_summary']['group_count']!=metrics['manual_summary']['total_count']
    assert all(read('metrics.json')['partner_tax_ids'].values())
    evidence=read('transaction_evidence.json')
    assert len(evidence)==588 and sum(r['amount'] is None for r in evidence)==1
    assert all(not r['applied_to_source'] for r in read('diagnostic_interpretations.json'))
    for row in inventory:
        assert hashlib.sha256((ROOT/row['file']).read_bytes()).hexdigest()==row['sha256']
    original_manifest=read('input_manifest.json')
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in original_manifest.items())
    outputs=[p for p in sorted(OUT.glob('*.json')) if p.name!='verification.json']
    evidence_hashes=hashes(outputs)
    result=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'profiling/profile_case.py')],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
    assert result.returncode==0,result.stderr
    assert hashes(outputs)==evidence_hashes,'Evidence changed on identical rerun'
    assert hashes(source_paths)==before,'Source changed during profiling'
    receipt=dict(status='PASS',profile_run_at=datetime.now(timezone.utc).isoformat(),
                 python=sys.version.split()[0],pandas=pd.__version__,openpyxl=openpyxl.__version__,
                 independent_csv_checks=independent,source_files_unchanged=len(source_paths),
                 deterministic_evidence_files=len(outputs),
                 checks=['Independent Pandas CSV row counts and Decimal totals','Independent openpyxl sheets and anomalous dates',
                         'Decimal reconciliation and population partitions','Missing BRL remains null',
                         'All 19 inputs match original manifest','Byte-identical diagnostic rerun'])
    (OUT/'verification.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(receipt,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
