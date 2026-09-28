"""Read-only source inspection; preserves CSV physical lines and XLSX numeric lexemes."""
from pathlib import Path
import csv
import hashlib
import io
import json
import posixpath
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def load_sources():
    sources = []
    for path in sorted((ROOT / 'data').rglob('*')):
        if not path.is_file():
            continue
        data = path.read_bytes()
        base = dict(file=path.relative_to(ROOT).as_posix(), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        if path.suffix.lower() == '.csv':
            encoding = 'utf-8-sig' if data.startswith(b'\xef\xbb\xbf') else 'utf-8'
            try:
                decoded = data.decode(encoding)
            except UnicodeDecodeError:
                encoding = 'cp1252'
                decoded = data.decode(encoding, errors='strict')
            delimiter = max(',;\t', key=lambda d: decoded.splitlines()[0].count(d))
            if path.name.startswith('extrato_'):
                delimiter = ';'
            reader = csv.reader(io.StringIO(decoded, newline=''), delimiter=delimiter, strict=True)
            rows, previous = [], 0
            for i, values in enumerate(reader, 1):
                rows.append(dict(row=i, line_start=previous+1, line_end=reader.line_num, values=values))
                previous = reader.line_num
            sources.append(dict(**base, sheet=None, encoding=encoding, delimiter=delimiter, physical_lines=len(decoded.splitlines()), rows=rows))
        elif path.suffix.lower() == '.xlsx':
            # Read the XML text itself: no float conversion of monetary cells.
            with zipfile.ZipFile(path) as z:
                strings = []
                if 'xl/sharedStrings.xml' in z.namelist():
                    strings = [''.join(n.itertext()) for n in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si', NS)]
                rels = {r.attrib['Id']: r.attrib['Target'] for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
                wb = ET.fromstring(z.read('xl/workbook.xml'))
                for sheet in wb.findall('s:sheets/s:sheet', NS):
                    rid = sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
                    target = rels[rid]
                    target = target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/' + target)
                    doc = ET.fromstring(z.read(target))
                    rows = []
                    for row in doc.findall('s:sheetData/s:row', NS):
                        values, types, styles = [], [], []
                        for cell in row.findall('s:c', NS):
                            letters = ''.join(c for c in cell.attrib['r'] if c.isalpha())
                            col = 0
                            for letter in letters:
                                col = col * 26 + ord(letter) - 64
                            while len(values) < col:
                                values.append(''); types.append(''); styles.append('')
                            kind = cell.get('t', 'n')
                            v = cell.find('s:v', NS)
                            value = '' if v is None else (v.text or '')
                            if kind == 'inlineStr':
                                value = ''.join(n.text or '' for n in cell.findall('s:is//s:t', NS))
                            elif kind == 's':
                                value = strings[int(value)]
                            if cell.find('s:f', NS) is not None:
                                kind = 'formula:' + (cell.find('s:f', NS).text or '')
                            values[col-1], types[col-1], styles[col-1] = value, kind, cell.get('s', '')
                        rows.append(dict(row=int(row.attrib['r']), values=values, cell_types=types, cell_styles=styles))
                    sources.append(dict(**base, sheet=sheet.attrib['name'], dimension=doc.find('s:dimension', NS).get('ref'), rows=rows))
        else:
            raise ValueError(f'Uninspected source format: {path}')
    return sources


if __name__ == '__main__':
    out = ROOT / 'profiling' / 'output'
    out.mkdir(parents=True, exist_ok=True)
    sources = load_sources()
    (out / 'source_snapshot.json').write_text(json.dumps(sources, ensure_ascii=False, indent=2), encoding='utf-8')
    for s in sources:
        print(json.dumps({k:v for k,v in s.items() if k != 'rows'}, ensure_ascii=False))
        rows = s['rows']
        if 'uber_business' in s['file']:
            show = rows[:9] + rows[-5:]
        else:
            show = rows
        for r in show:
            print(json.dumps(r, ensure_ascii=False))
