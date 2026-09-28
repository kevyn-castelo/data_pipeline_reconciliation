"""Readable, generated schema appendix, preserving the complete original headers."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'profiling/output'


def escape(value):
    return str(value).replace('|','\\|').replace('\n','<br>')


def main():
    inventory=json.loads((OUT/'inventory.json').read_text(encoding='utf-8'))
    schema=json.loads((OUT/'schema_comparison.json').read_text(encoding='utf-8'))
    lines=['# Schemas completos — profiling', '', 'Gerado a partir dos arquivos inspecionados; nomes de comparação são exploratórios, não o contrato canônico.', '']
    for inv in inventory:
        lines.extend([f"## {inv['file']} — {inv['sheet'] or 'CSV'}", '', '| Posição | Cabeçalho original | Campo de comparação Uber |', '|---:|---|---|'])
        fields={r['position']:r['comparison_field'] for r in schema if r['file']==inv['file'] and r['sheet']==inv['sheet']}
        for pos,h in enumerate(inv['schema'],1):
            lines.append(f"| {pos} | {escape(h)} | {escape(fields.get(pos,'—'))} |")
        lines.append('')
    (ROOT/'profiling/SCHEMAS.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__':
    main()
