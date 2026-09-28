# Entregáveis gerados

Os CSVs, os manifestos JSON e os documentos desta pasta são versionados. O banco DuckDB, cópias dbt, logs e testes permanecem locais.

| Entregável | Arquivo |
|---|---|
| Transações normalizadas | stg_uber_transactions.csv |
| Candidatos canônicos, resolvidos e conflitos | int_transactions.csv, int_transactions_resolved.csv, int_transaction_conflicts.csv |
| Vínculo por e-mail | int_uber_email_links.csv |
| Resumo mensal por CC e rota | int_monthly_cost_center_payment_summary.csv |
| Imports Alchemy | ap_titulos.csv, ap_rateios.csv |
| Retenções e linhagem | ap_titulos_candidatos.csv, ap_rateios_candidatos.csv, ap_rateios_linhagem.csv |
| Qualidade e normalizações | dq_report.csv, dq_normalization_events.csv |
| Resumo financeiro | controller_summary.md |
| Proveniência | input_manifest.json, run_summary.json |

Os imports podem conter apenas cabeçalhos: consultar os bloqueios dos candidatos. Valores conhecidos não substituem valores ausentes ou disputados.
Conciliação bancária: ../reconciliation/README.md. Análise e arquitetura: ../docs/18_analise_final_pipeline.md. Execução: ../RUNNING.md.
