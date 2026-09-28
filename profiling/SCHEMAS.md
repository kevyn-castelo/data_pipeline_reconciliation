# Schemas completos — profiling

Gerado a partir dos arquivos inspecionados; nomes de comparação são exploratórios, não o contrato canônico.

## data/cartoes_corporativos.csv — CSV

| Posição | Cabeçalho original | Campo de comparação Uber |
|---:|---|---|
| 1 | bandeira | — |
| 2 | final | — |
| 3 | tipo | — |
| 4 | titular | — |
| 5 | banco_emissor | — |
| 6 | observacao | — |

## data/centros_de_custo.xlsx — Sheet

| Posição | Cabeçalho original | Campo de comparação Uber |
|---:|---|---|
| 1 | Código | — |
| 2 | Descrição | — |
| 3 | Ativo | — |
| 4 | Responsável | — |

## data/de_para_codigo_despesa.csv — CSV

| Posição | Cabeçalho original | Campo de comparação Uber |
|---:|---|---|
| 1 | codigo_despesa | — |
| 2 | descricao | — |
| 3 | conta_contabil | — |
| 4 | conta_gerencial_sugerida | — |
| 5 | observacao | — |

## data/de_para_contabil_gerencial.csv — CSV

| Posição | Cabeçalho original | Campo de comparação Uber |
|---:|---|---|
| 1 | conta_contabil | — |
| 2 | descricao_contabil | — |
| 3 | conta_gerencial | — |
| 4 | descricao_gerencial | — |

## data/demonstrativo_mensal_uber.csv — CSV

| Posição | Cabeçalho original | Campo de comparação Uber |
|---:|---|---|
| 1 | numero_demonstrativo | — |
| 2 | cnpj_emitente | — |
| 3 | periodo_inicio | — |
| 4 | periodo_fim | — |
| 5 | data_disponibilizacao | — |
| 6 | data_vencimento | — |
| 7 | forma_pagamento | — |
| 8 | cobrancas_usuario | — |
| 9 | taxas_servico | — |
| 10 | valor_total | — |
| 11 | observacao | — |

## data/departamentos.csv — CSV

| Posição | Cabeçalho original | Campo de comparação Uber |
|---:|---|---|
| 1 | CODIGO | — |
| 2 | NOME | — |
| 3 | CENTRO_CUSTO_VINCULADO | — |

## data/extrato_itau_cc_2026-07_a_2026-09.csv — CSV

| Posição | Cabeçalho original | Campo de comparação Uber |
|---:|---|---|
| 1 | data | — |
| 2 | lançamento | — |
| 3 | ag./origem | — |
| 4 | valor (R$) | — |
| 5 | saldo (R$) | — |

## data/fornecedores.xlsx — Sheet

| Posição | Cabeçalho original | Campo de comparação Uber |
|---:|---|---|
| 1 | Razão Social | — |
| 2 | Nome Fantasia | — |
| 3 | CNPJ | — |
| 4 | Inscrição Estadual | — |
| 5 | Município | — |
| 6 | UF | — |
| 7 | E-mail | — |
| 8 | Telefone | — |
| 9 | Condição de Pagamento | — |

## data/funcionarios.xlsx — Funcionarios

| Posição | Cabeçalho original | Campo de comparação Uber |
|---:|---|---|
| 1 | Matrícula | — |
| 2 | Nome | — |
| 3 | CPF | — |
| 4 | Departamento | — |
| 5 | Centro de Custo | — |
| 6 | Cargo | — |
| 7 | Data Admissão | — |
| 8 | Situação | — |
| 9 | Data Desligamento | — |

## data/plano_de_contas.csv — CSV

| Posição | Cabeçalho original | Campo de comparação Uber |
|---:|---|---|
| 1 | codigo | — |
| 2 | descricao | — |
| 3 | tipo | — |
| 4 | natureza | — |
| 5 | aceita_lancamento | — |

## data/plano_gerencial.csv — CSV

| Posição | Cabeçalho original | Campo de comparação Uber |
|---:|---|---|
| 1 | codigo_gerencial | — |
| 2 | descricao | — |
| 3 | grupo | — |
| 4 | aceita_lancamento | — |

## data/uber_business_2026-07.csv — CSV

| Posição | Cabeçalho original | Campo de comparação Uber |
|---:|---|---|
| 1 | Trip/Eats ID | trip/eats id |
| 2 | Transaction Timestamp (UTC) | transaction timestamp (utc) |
| 3 | Request Date (UTC) | request date (utc) |
| 4 | Request Time (UTC) | request time (utc) |
| 5 | Request Date (Local) | request date (local) |
| 6 | Request Time (Local) | request time (local) |
| 7 | Drop-off Date (UTC) | drop-off date (utc) |
| 8 | Drop-off Time (UTC) | drop-off time (utc) |
| 9 | Drop-off Date (Local) | drop-off date (local) |
| 10 | Drop-off Time (Local) | drop-off time (local) |
| 11 | Request Timezone Offset from UTC | request timezone offset from utc |
| 12 | First Name | first name |
| 13 | Last Name | last name |
| 14 | Email | email |
| 15 | Employee ID | employee id |
| 16 | Group | group |
| 17 | Service | service |
| 18 | Program | program |
| 19 | City | city |
| 20 | Country | country |
| 21 | Distance (mi) | distance (mi) |
| 22 | Duration (min) | duration (min) |
| 23 | Pickup Address | pickup address |
| 24 | Drop-off Address | drop-off address |
| 25 | Expense Code | expense code |
| 26 | Expense Memo | expense memo |
| 27 | Payment Method | payment method |
| 28 | Transaction Type | transaction type |
| 29 | Trip/Meal Fare (Local Currency) | trip/meal fare (local currency) |
| 30 | Booking Fee/Service Fee (Local Currency) | booking fee/service fee (local currency) |
| 31 | Aiport Fee<br>(Local Currency) | aiport fee (local currency) |
| 32 | City Fee<br>(Local Currency) | city fee (local currency) |
| 33 | Toll Fee<br>(Local Currency) | toll fee (local currency) |
| 34 | Delivery Fee<br>(Local Currency) | delivery fee (local currency) |
| 35 | Promotions & Discounts<br>(Local Currency) | promotions & discounts (local currency) |
| 36 | Tips (Local Currency) | tips (local currency) |
| 37 | Other Charges | other charges |
| 38 | Total Fare (Local Currency) | total fare (local currency) |
| 39 | Total Taxes (local currency) | total taxes (local currency) |
| 40 | Payments made by employees/guests (local currency) | payments made by employees/guests (local currency) |
| 41 | Transaction Amount (local currency) | transaction amount (local currency) |
| 42 | Membership Savings (Local Currency) | membership savings (local currency) |
| 43 | Local Currency | local currency |
| 44 | Tips <br>in BRL | tips in brl |
| 45 | Total Fare in BRL | total fare in brl |
| 46 | Total Taxes in BRL | total taxes in brl |
| 47 | Payments made by employees/guests in BRL | payments made by employees/guests in brl |
| 48 | Transaction Amount in BRL | transaction amount in brl |
| 49 | Invoices | invoices |
| 50 | Invoice Number | invoice number |
| 51 | Conditional Columns | conditional columns |

## data/uber_business_2026-08.xlsx — BR

| Posição | Cabeçalho original | Campo de comparação Uber |
|---:|---|---|
| 1 | Trip/Eats ID | trip/eats id |
| 2 | Transaction timestamp (UTC) | transaction timestamp (utc) |
| 3 | Request date (UTC) | request date (utc) |
| 4 | Request time (UTC) | request time (utc) |
| 5 | Request Date (Local) | request date (local) |
| 6 | Request Time (Local) | request time (local) |
| 7 | Drop-off date (UTC) | drop-off date (utc) |
| 8 | Drop-off time (UTC) | drop-off time (utc) |
| 9 | Drop-off date (local) | drop-off date (local) |
| 10 | Drop-off time (local) | drop-off time (local) |
| 11 | Request timezone offset from UTC | request timezone offset from utc |
| 12 | First name | first name |
| 13 | Surname | last name |
| 14 | Email | email |
| 15 | Employee ID | employee id |
| 16 | Group | group |
| 17 | Service | service |
| 18 | Programme | program |
| 19 | City | city |
| 20 | Country | country |
| 21 | Distance (mi) | distance (mi) |
| 22 | Duration (mins) | duration (min) |
| 23 | Pick-up address | pickup address |
| 24 | Drop-off address | drop-off address |
| 25 | Expense code | expense code |
| 26 | Expense memo | expense memo |
| 27 | Payment method | payment method |
| 28 | Transaction type | transaction type |
| 29 | Net Uber Fare (local currency) | net uber fare (local currency) |
| 30 | Uber Promotions/Discounts (local currency) | uber promotions/discounts (local currency) |
| 31 | Total Taxes on Uber Fares (local currency) | total taxes on uber fares (local currency) |
| 32 | Gross Uber Fare (local currency) | gross uber fare (local currency) |
| 33 | Partner Fare (local currency) | partner fare (local currency) |
| 34 | Tips (Local Currency & Inclusive of taxes, if any) | tips (local currency & inclusive of taxes, if any) |
| 35 | Total Taxes on Partner fare (local currency) | total taxes on partner fare (local currency) |
| 36 | Gross Partner Fare (local currency) | gross partner fare (local currency) |
| 37 | Other charges (local currency) | other charges |
| 38 | Total Fare (local currency) | total fare (local currency) |
| 39 | Total Taxes (local currency) | total taxes (local currency) |
| 40 | Payments made by employees/guests (local currency) | payments made by employees/guests (local currency) |
| 41 | Transaction Amount | transaction amount (local currency) |
| 42 | Membership savings (local currency) | membership savings (local currency) |
| 43 | Local currency code | local currency |
| 44 | Tip in BRL (Inclusive of taxes, if any) | tips in brl |
| 45 | Totals Fare in BRL | total fare in brl |
| 46 | Total Taxes in BRL | total taxes in brl |
| 47 | Payments made by employees/guests in BRL | payments made by employees/guests in brl |
| 48 | Transaction amount in BRL | transaction amount in brl |
| 49 | Uber Fare Invoice# | invoice number |
| 50 | Uber Fare Invoice Date | uber fare invoice date |
| 51 | Uber Fare Invoice Link | uber fare invoice link |
| 52 | Uber Fare Invoice File Name | uber fare invoice file name |
| 53 | Partner Fare Invoice # | partner fare invoice # |
| 54 | Partner Fare Invoice Date | partner fare invoice date |
| 55 | Partner Fare Invoice Link | partner fare invoice link |
| 56 | Partner Fare Invoice File Name | partner fare invoice file name |
| 57 | Partner Tax ID | partner tax id |
| 58 | Partner Name | partner name |
| 59 | Partner Address and Postal Code | partner address and postal code |
| 60 | Conditional Columns | conditional columns |

## data/uber_business_2026-08.xlsx — Resumo

| Posição | Cabeçalho original | Campo de comparação Uber |
|---:|---|---|
| 1 | Group | — |
| 2 | Qtd | — |
| 3 | Total BRL | — |

## data/uber_business_2026-08_complemento_financeiro.csv — CSV

| Posição | Cabeçalho original | Campo de comparação Uber |
|---:|---|---|
| 1 | Trip/Eats ID | trip/eats id |
| 2 | Transaction Timestamp (UTC) | transaction timestamp (utc) |
| 3 | Request Date (UTC) | request date (utc) |
| 4 | Request Time (UTC) | request time (utc) |
| 5 | Request Date (Local) | request date (local) |
| 6 | Request Time (Local) | request time (local) |
| 7 | Drop-off Date (UTC) | drop-off date (utc) |
| 8 | Drop-off Time (UTC) | drop-off time (utc) |
| 9 | Drop-off Date (Local) | drop-off date (local) |
| 10 | Drop-off Time (Local) | drop-off time (local) |
| 11 | Request Timezone Offset from UTC | request timezone offset from utc |
| 12 | First Name | first name |
| 13 | Last Name | last name |
| 14 | Email | email |
| 15 | Employee ID | employee id |
| 16 | Group | group |
| 17 | Service | service |
| 18 | Program | program |
| 19 | City | city |
| 20 | Country | country |
| 21 | Distance (mi) | distance (mi) |
| 22 | Duration (min) | duration (min) |
| 23 | Pickup Address | pickup address |
| 24 | Drop-off Address | drop-off address |
| 25 | Expense Code | expense code |
| 26 | Expense Memo | expense memo |
| 27 | Payment Method | payment method |
| 28 | Transaction Type | transaction type |
| 29 | Trip/Meal Fare (Local Currency) | trip/meal fare (local currency) |
| 30 | Booking Fee/Service Fee (Local Currency) | booking fee/service fee (local currency) |
| 31 | Aiport Fee<br>(Local Currency) | aiport fee (local currency) |
| 32 | City Fee<br>(Local Currency) | city fee (local currency) |
| 33 | Toll Fee<br>(Local Currency) | toll fee (local currency) |
| 34 | Delivery Fee<br>(Local Currency) | delivery fee (local currency) |
| 35 | Promotions & Discounts<br>(Local Currency) | promotions & discounts (local currency) |
| 36 | Tips (Local Currency) | tips (local currency) |
| 37 | Other Charges | other charges |
| 38 | Total Fare (Local Currency) | total fare (local currency) |
| 39 | Total Taxes (local currency) | total taxes (local currency) |
| 40 | Payments made by employees/guests (local currency) | payments made by employees/guests (local currency) |
| 41 | Transaction Amount (local currency) | transaction amount (local currency) |
| 42 | Membership Savings (Local Currency) | membership savings (local currency) |
| 43 | Local Currency | local currency |
| 44 | Tips <br>in BRL | tips in brl |
| 45 | Total Fare in BRL | total fare in brl |
| 46 | Total Taxes in BRL | total taxes in brl |
| 47 | Payments made by employees/guests in BRL | payments made by employees/guests in brl |
| 48 | Transaction Amount in BRL | transaction amount in brl |
| 49 | Invoices | invoices |
| 50 | Invoice Number | invoice number |
| 51 | Conditional Columns | conditional columns |

## data/usuarios_internos.csv — CSV

| Posição | Cabeçalho original | Campo de comparação Uber |
|---:|---|---|
| 1 | id_usuario | — |
| 2 | nome_exibicao | — |
| 3 | email_principal | — |
| 4 | emails_alternativos | — |
| 5 | matricula | — |
| 6 | centro_custo | — |
| 7 | status | — |
| 8 | ultimo_acesso | — |
