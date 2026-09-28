# Validação das correções — 28/09/2026

## Entregáveis e execução

`TASK.md` pede canônico, vínculo, resumo por centro de custo, imports com retenções, qualidade em três buckets, resumo ao controller, análise e nota de desenho. O índice em `output/README.md` aponta cada artefato. A conciliação é diferencial opcional e está em `reconciliation/`.

Build com `run.py --output output --as-of-date 2026-09-28`: **67/67 passos dbt aprovados**, dos quais 33 modelos, 33 testes e um seed. `tests_data_controls.py`, `tests_bank_reconciliation.py` e `tests_synthetic.py` passaram. O manifesto de entrada identifica os arquivos por hash; `run_summary.json` contém hash de código, manifesto, decisões, ledger, data de corte e versão Python.

| Controle | Resultado da amostra |
|---|---:|
| Ocorrências Uber | 588 |
| Candidatos canônicos | 573 |
| Títulos candidatos | 20: 2 faturas + 18 reembolsos |
| Títulos e rateios liberados | 0 e 0 |
| Componentes conhecidos das rotas | R$ 31.842,73; outros três da rota faturada sem BRL seguro |
| DQ | 2.444 incidências: 1.978 auto_fixable, 289 needs_client, 177 rule_based |
| Normalizações com localizador e antes/depois | 1.955 |
| Revisão explícita Custo × Despesa | 80 componentes, R$ 5.299,43 |

## Conciliação: o que parecia zerado

Nenhum dos **18 reembolsos** tem `valor_titulo` zero; eles somam **R$ 1.608,75**. O zero em `diferenca_pagamento_principal` informa que o PIX principal fechou o valor daquele título. Campo principal vazio informa que nenhum débito foi atribuído; ele não é convertido em zero.

| Evidência | Valor |
|---|---:|
| 15 reembolsos com PIX principal associado, incluindo dois títulos num mesmo PIX | R$ 1.217,03 atribuído aos títulos |
| Segundo PIX de Marcos, identificado como duplicado | R$ 73,78 adicional |
| Marcos: título / principal / total com duplicidade | R$ 73,78 / R$ 73,78 / R$ 147,56 |
| Bianca agosto: título / PIX | R$ 115,30 / R$ 115,29, diferença −R$ 0,01 |
| André Neto julho: sem PIX associado até 20/09 | R$ 146,23 aberto no recorte |
| Mariana: dois títulos com CPF inválido e sem PIX associado | R$ 245,48, bloqueados para importação |
| Faturas julho/agosto: documentos / débitos bancários | R$ 29.532,81 / R$ 29.838,08 |
| Excesso no boleto de agosto | R$ 305,27, composição não aprovada |
| Cartão VISA 0042 | R$ 33,20, classificação pendente |

Os 86 movimentos estão individualizados em `bank_movements.csv`. `bank_match_pairs.csv` reparte o PIX único de R$ 110,40 entre R$ 37,37 e R$ 73,03; os valores atribuídos somam sem duplicar o movimento. O CSV de revisão não atribui valor. O motor rejeita agrupamento entre matrículas diferentes e um boleto de diferença material, verificados em teste sintético. A busca bancária não exclui o CPF inválido; o bloqueio de importação fica em coluna própria. O extrato declara cobertura até **20/09/2026**, mesmo que o último movimento seja de 18/09.

## Controles adicionais

- TRANSP-FUNC, 71 componentes/R$ 4.972,40, e ENTRE-UN nos CC300/CC310, nove componentes/R$ 327,03, aguardam decisão de Custo × Despesa. Um crosswalk tecnicamente válido não elimina o bloqueio da decisão, verificado na suíte sintética.
- Corridas fora da vigência do RH geram sinalização. A suíte sintética comprovou que uma corrida histórica faturada na vigência pode passar com o status corrente inativo, enquanto o reembolso de ex-funcionário exige revisão.
- Os arquivos de importação continuam vazios para julho/agosto pelo corte e vencimento. Evidência bancária não confirma baixa no ERP nem autoriza reimportação.

## Limites para a operação seguinte

O ledger `config/issued_titles.csv` está vazio; é preciso obter os títulos manuais do ERP antes de automatizar uma competência nova. Candidatos de ajuste ainda não consideram os ajustes já emitidos de modo cumulativo. A publicação do pipeline troca pastas após a validação, mas depende de acesso exclusivo à pasta no Windows. A conciliação atual não publica seus relatórios por essa troca. Homônimos, lotes maiores, pagamentos parciais e origem dos R$ 305,27 precisam de evidência ou extensão de regra antes de uma baixa operacional.
