# Profiling do case Alchemy ERP

Comece pelo [relatório](REPORT.md). Este diretório contém somente leitura, diagnósticos, evidências e verificação. Os arquivos em `data/` e os documentos originais não são modificados. As normalizações são interpretações documentadas para comparação, sem contratos de produção congelados.

## Executar o profiling

Na raiz do projeto, com Python 3.14 (versão usada: 3.14.6):

```powershell
python -X utf8 profiling/profile_case.py
python -X utf8 profiling/render_schemas.py
```

O profiling principal usa apenas a biblioteca padrão. Ele lê todos os CSV e todas as abas XLSX, incluindo células numéricas em sua representação XML, usando `Decimal` para dinheiro. A detecção de colunas Uber usa cabeçalhos, não posições fixas. Este leitor é delimitado aos formatos efetivamente inspecionados; não é um loader de produção para todo possível XLSX.

## Verificação independente

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r profiling/requirements-verification.txt
.\.venv\Scripts\python -X utf8 profiling/verify_profile.py
```

Valida a leitura com Pandas/openpyxl, populações, valores `Decimal`, reconciliação, ausência explícita de BRL, arquivos de entrada inalterados e evidências idênticas em reexecução. Resultado em `output/verification.json`. Esse recibo contém horário de execução e, por isso, fica fora da comparação determinística.

## Artefatos gerados

| Arquivo em output/ | Conteúdo |
|---|---|
| input_manifest.json / inventory.json | Hashes dos 19 inputs; inventário dos dados, schemas e linhas |
| source_snapshot.json | Todas as células/valores originais, sem perdas intencionais ou exclusão de rodapés |
| schema_comparison.json / column_profiles.json | Nomes equivalentes, posições, cardinalidades, nulos/marcadores, frequências de todos os campos |
| transaction_evidence.json | Todas as 588 ocorrências, valores originais e em centavos, posições e chave candidata |
| duplicate_groups.json / conflicting_candidates.json | Grupos repetidos e diferenças entre versões |
| user_linking.json / master_findings.json | Status por e-mail, aliases, matrículas e qualidade cadastral |
| statement_reconciliation.json | Conciliação preliminar e soma conhecida, com contagem de BRL ausente |
| diagnostic_interpretations.json | Before → after → rule; `applied_to_source=false` |
| issues.json / policy_diagnostics.json | DQ/financeiro separados de compliance |
| metrics.json | Populações, cenários, frequências e totais do relatório |

As somas exploratórias não elegem vencedores de conflitos. `reference_scenario` e `conflict_amount_bounds` documentam a sensibilidade. Nunca reutilizar o primeiro registro do grupo como regra de deduplicação de produção. A fotografia dos dados e as evidências são determinísticas; o texto do relatório registra a interpretação humana desta rodada de profiling e deve ser revisto se os inputs mudarem.
