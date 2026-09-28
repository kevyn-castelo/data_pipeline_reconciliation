# Execução e reexecução do pipeline

As etapas 1 a 4 implementam ingestão auditável RAW, parsing técnico STAGING, resolução CANONICAL, enriquecimento, candidatos de contas a pagar, release gate e relatórios de consolidação/DQ em DuckDB/dbt. A conciliação bancária opcional foi acrescentada em `bank_reconciliation.py` e roda separadamente, sem baixa no ERP. Os números de builds descritos nas seções históricas abaixo são anteriores ao corte operacional; a seção final traz o estado vigente.

## Ambiente e comandos

Dependências instaladas no `.venv` do projeto: Python, DuckDB 1.5.5, dbt Core 1.12.5, dbt-duckdb 1.11.0 e openpyxl 3.1.5. Para reproduzir no PowerShell a partir da raiz:

```powershell
& '.\.venv\Scripts\python.exe' run.py --output .\output
& '.\.venv\Scripts\python.exe' tests_synthetic.py
```

O primeiro comando constrói `output\canonical.duckdb`, os exports CSV auditáveis e o manifesto de entradas. Uma pasta de saída existente só é aceita quando contém o marcador gerado pelo pipeline; a limpeza se limita a artefatos conhecidos dentro dela. Para usar decisões, passe `--resolutions <caminho.csv>` ao primeiro comando. O seed padrão está vazio.

## Etapa 1 — verificação histórica

Execução real dos arquivos em `data/`: dbt build concluiu com 22/22 (1 seed, 4 modelos tabela, 2 views e 15 testes), sem avisos nem erros. O resultado teve 16 inventários de arquivo/aba, 2 layouts de transação, 588 ocorrências RAW e STAGING, 588 versões de ocorrência, 573 chaves candidatas, 571 resolvidas sem conflito e 2 chaves conflitantes. As chaves se particionaram em 558 únicas, 13 equivalentes e 2 conflitantes.

As somas `amount_brl` na STAGING foram R$ 15.486,90 (julho), R$ 16.530,83 (agosto) e R$ 718,18 (complemento). Valores ausentes e os dois conflitos permaneceram explícitos. As entradas sob `data/` foram hasheadas antes e depois da execução; os 15 SHA-256 permaneceram iguais. Os exports auditáveis foram comparados entre reruns; após ordenar as chaves dos metadados JSON, ficaram determinísticos.

`tests_synthetic.py` passou com casos de colunas reordenadas, alias por hash, repetição dentro de arquivo, NULL versus zero, A15, tipo desconhecido, identidade/data inválida, múltiplas Fare, `accept_occurrence`, `reject_all`, decisão stale, rerun, resíduo e erro monetário, e a proteção temporal D8.

## Limites técnicos da etapa 1

O leitor de XLSX preserva os seriais numéricos e a época do workbook; formatos de data textuais em XLSX ainda não têm inferência dedicada. Overrides explícitos de formato podem ser configurados em `config/client.json` quando uma fonte futura for ambígua. Os modelos são próprios deste caso; não há adaptadores genéricos.

## Etapa 2 — cadastros, enriquecimento e gates

`run.py` descobre fontes de referência pelas assinaturas de cabeçalho e grava o inventário e as tabelas `raw_ref_*`, preservando texto original, arquivo/hash, aba/linha e identificadores como texto. O domínio `sheet_role` do contrato RAW permanece restrito a abas de transação e abas não transacionais ignoradas; cadastros são distinguidos pelo inventário de referência. `departamentos.csv` não entra no vínculo de centro de custo; competência do demonstrativo mensal, extrato bancário e reconciliação pertencem à etapa 3.

Os modelos dbt ligam e-mails primários/aliases, usuários ERP, matrícula de RH e centro de custo oficial de funcionários. Ligações ambíguas permanecem pendentes, status de usuário e funcionário são separados, divergência com centro de custo do diretório é DQ e não substitui o centro oficial. A tabela `int_uber_email_links` tem grão de e-mail Uber distinto; solicitantes de viagens Uber Central ficam em `int_requester_email_links`. `int_transaction_enrichment` conserva uma linha para cada chave candidata e inclui as retidas/quarentenadas, sem multiplicar valor por cardinalidade de cadastro.

O enriquecimento mantém separados os códigos de despesa, conta contábil, crosswalk oficial e sugestão gerencial. A sugestão não preenche lacunas do crosswalk; discrepância EVENTO, falta de crosswalk em TRANSP-FUNC e conta não postável em TREIN são pendências. Cartões corporativos identificados ficam distintos dos pessoais: Periodic Billing é faturamento da empresa; AMEX 3008 está fora da integração; VISA 0042 permanece `NEEDS_CLIENT` sem conversão automática para reembolso. Ausência de BRL permanece NULL, sem câmbio/zero. Competências de faturamento e reembolso são distintas; reembolso candidato usa mês local da solicitação e sinaliza travessia entre meses. As flags de compliance não alteram valores financeiros; limite de Eats e calendário de feriados estão marcados como não avaliados por ausência da composição de itens/calendário.

Para reexecutar no PowerShell:

```powershell
& '.\.venv\Scripts\python.exe' run.py --output .\output
& '.\.venv\Scripts\python.exe' tests_synthetic.py
```

Verificação integrada da etapa 2: dbt PASS=40, WARN=0, ERROR=0 (15 modelos, 24 testes, seed vazio). Foram mantidos 588 ocorrências RAW/STAGING, 573 chaves candidatas (571 elegíveis à view resolved, 2 conflitos em quarentena), e 573 linhas de enriquecimento; o teste dbt de conservação usa `occurrence_ids` e compara `transaction_id` com semântica NULL-safe. A tabela de emails contém 74 endereços: 62 ligações primárias únicas, 6 ligações por alias, 2 ambíguas e 4 sem usuário; a tabela de solicitante contém um email. Rotas nos 571 candidatos resolved: Periodic Billing 519 / R$ 29.318,23 conhecidos e um candidato com BRL ausente; cartões pessoais candidatos 39 / R$ 1.608,75; AMEX 3008 12 / R$ 882,55; VISA 0042 um / R$ 33,20 pendente. Valores das rotas são conferência da amostra, não configuração/hardcode.

`tests_synthetic.py` passou após as alterações de enriquecimento; além dos cenários da etapa 1, a execução dbt inclui a ocorrência de identidade não interpretável, cuja linha continua presente no enriquecimento com `transaction_id=NULL`. Reexecução do pipeline real não alterou os SHA-256 dos 15 arquivos sob `data/`. A suíte sintética também passou o rerun determinístico, decisão accept/reject/stale, colisão D8 e comparação A15.

Pendências explícitas que bloqueiam/liberam somente com decisão ou fonte do cliente: decisão de destino VISA 0042; regra de rateio Admin Fee; classificação gerencial para códigos sem crosswalk ou com sugestão divergente; validação das correspondências cadastrais ambíguas/ausentes; cadastro/calendário de feriados e itens de Eats para medir controles não avaliados; fornecedor Uber com candidatos de mesmo nome/CNPJ divergente. Nenhuma dessas lacunas é resolvida pela etapa 2 nem deve ser inferida automaticamente.

## Etapa 3 — candidatos de AP e release gate

`demonstrativo_mensal_uber.csv` é carregado como fonte de referência separada (`raw_ref_statements`), com hash e localizador. `data_disponibilizacao` permanece como `availability_date`; só uma coluna explícita `data_emissao`, se fornecida, pode preencher a emissão do título. O CNPJ do demonstrativo liga ao fornecedor por dígitos e check digits, evitando escolher por nome entre os dois registros Uber com mesmo nome normalizado. Período deve cobrir o mês UTC inteiro; valores em formato brasileiro são preservados e rejeitados se inválidos ou com mais de duas casas.

O pipeline cria candidatos de fatura por demonstrativo, mais buckets para competência sem demonstrativo, e de reembolso por funcionário/mês local. Gate avalia a população completa do grupo: identidade/quarentena, BRL, link/funcionário/CPF/CC, mapeamento contábil e crosswalk oficial, contas postáveis, CNPJ/documentos/datas, positividade e fechamento das linhas. As importações finais `ap_titulos.csv` e `ap_rateios.csv` têm exatamente os cabeçalhos do layout Alchemy e só recebem títulos com todas as validações aprovadas. `ap_titulos_candidatos.csv` contém bloqueios e valores diagnósticos; `ap_rateios_candidatos.csv` mantém linhas e status; `ap_rateios_linhagem.csv` liga componente/linha a `occurrence_ids`. `id_externo` deriva do tipo e da chave do documento/grupo e é estável entre reruns. Valor desconhecido não entra no total proposto nem é completado pela diferença do demonstrativo.

Build real atual: dbt PASS=55, WARN=0, ERROR=0 (26 modelos, 28 testes, 1 seed). Foram gerados 2 candidatos de fatura cobrindo 521 componentes e 18 candidatos de reembolso cobrindo 39 componentes. Nenhum título ou rateio foi liberado. Julho tem demonstrativo R$ 14.519,26, subtotal de componentes BRL conhecidos R$ 14.409,24 e 2 componentes com valor desconhecido; agosto tem demonstrativo R$ 15.013,55, subtotal conhecido R$ 14.908,99 e 1 desconhecido. `detail_total` fica NULL nos dois meses. Admin Fee e outros bloqueios de componente permanecem visíveis; o subtotal conhecido não fecha o título nem autoriza imputação. Todos os 18 reembolsos permanecem retidos porque não há regra/documento explícito para `data_emissao`; o vencimento candidato segue dia 15 do mês seguinte à competência. `data_disponibilizacao` não foi promovida a emissão.

Na suíte `tests_synthetic.py`, uma fatura sintética com data de emissão explícita, CNPJ válido, período integral e rateio fechado liberou exatamente um título e uma linha, com `id_externo` estável no rerun. Um segundo caso adicionou componente sem mapeamento e reteve o título inteiro, sem exportar a linha boa parcial para o layout final. Um terceiro confirmou retenção de valor do demonstrativo com mais de duas casas decimais e período parcial do mês. Build real e sintéticos passaram; hashes das 15 entradas em `data/` permaneceram iguais. A execução real produziu os arquivos oficiais somente com cabeçalho, consequência dos bloqueios acima.

## Etapa 4 — resumo mensal, qualidade e controller

O modelo `int_monthly_cost_center_payment_summary` conserva uma linha de resumo por mês analítico × atribuição × rota. Para Periodic Billing usa mês UTC da transação; para cartões usa mês local da solicitação, inclusive AMEX e VISA, sem afirmar que seja competência aprovada de título. Só funcionário com CC oficial ativo entra em CC atribuído; qualquer outro fica na linha agregada `UNATTRIBUTED`. Cada linha separa chaves candidatas, valores conhecidos elegíveis, ausentes, disputados, falhas de parsing, quarentena e subtotal conhecido. Os subtotais não são total devido nem valor liberado, e rotas de cartões excluídas ou pendentes seguem identificadas.

`dq_report.csv` consolida incidências transacionais, cadastrais e bloqueios finais de título nos buckets `auto_fixable`, `rule_based` e `needs_client`. Registros transacionais carregam occurrence IDs e localizador da primeira ocorrência; issues de cadastro preservam arquivo/aba/linha; blockers de título trazem localizador do demonstrativo quando existe e a lista de occurrence IDs do grupo. Divergências do centro de custo do diretório mostram valor anterior e CC oficial adotado, sem afirmar que o cadastro de origem foi alterado. Um candidato pode ter várias incidências DQ. `controller_summary.md` apresenta candidatos, liberação/retenção, demonstrativos e subtotais conhecidos, principais CCs e decisões pendentes; não soma versões conflitantes nem usa diferença do demonstrativo como plug. `int_uber_email_links.csv` continua sendo a visão de ligação por email.

Operação mensal: colocar novos exports e cadastros na pasta de entrada configurada, executar `run.py` com uma pasta dedicada de saída; conferir manifesto/hash, resumo mensal, `dq_report.csv` e `ap_titulos_candidatos.csv`; resolver ambiguidades somente por seed revisado e evidência aprovada; revisar `ap_titulos.csv`/`ap_rateios.csv` antes de importação. Reexecução idempotente substitui apenas artefatos gerados e mantém os mesmos IDs quando as chaves de origem não mudam. Não há banco opcional nem conciliação bancária nesta entrega.

Verificação Stage 4: `& '.\.venv\Scripts\python.exe' run.py --output .\output` — dbt PASS=59, WARN=0, ERROR=0. O resumo conserva 573 chaves e subtotal conhecido elegível de R$ 31.842,73 entre rotas (inclui R$ 882,55 AMEX excluído e R$ 33,20 VISA pendente; não é obrigação AP). Rotas: 521 company_billed, 39 personal reimbursement, 12 AMEX excluídas e 1 VISA pendente; company_billed tem R$ 29.318,23 conhecidos e 3 amounts ausentes/disputados. Por CC, o maior subtotal conhecido company_billed é CC310 (116 chaves, R$ 5.225,68), seguido por CC300 (79, R$ 3.566,09) e CC210 (53, R$ 3.421,99); `UNATTRIBUTED` contém 41 company_billed e subtotal conhecido R$ 2.594,59. Julho e agosto têm respectivamente 260/261 chaves faturadas e subtotais conhecidos R$ 14.409,24/R$ 14.908,99, com 2/1 amounts ausentes ou disputados; a variação de subtotais não demonstra variação do total devido. Os bloqueios de emissão, Admin Fee, classificações/crosswalk, BRL CLP, conflitos de chave, links cadastrais e VISA continuam retidos.

## Correções pós-revisão (C1–C6) — prevalecem sobre os números históricos acima

Decisões registradas em `docs/adendo_decisoes_revisao_etapa3.md`.

- **Cartões por tipo cadastrado (C1).** Bandeira normalizada com `upper()` antes do regex (`Amex - 3008` casa `AMERICAN_EXPRESS`). A rota vem de `corporate_card_routes` no `config/client.json` (`CREDITO_CORPORATIVO` → exclusão por processo próprio; `DEBITO_CONTA_PJ` → pendente de destino). Tipo cadastrado sem rota configurada → `needs_client_corporate_card_type_unmapped`. Não há bandeira/final fixos no SQL.
- **Arquivos do ERP sem BOM (C2).** `ap_titulos.csv` e `ap_rateios.csv` saem em UTF-8 sem BOM; CSVs de auditoria mantêm BOM para Excel.
- **Demonstrativo reenviado (C3).** Mesmo número + mesmo conteúdo comparável = um documento (`statement_occurrence_count`); conteúdo divergente → `statement_versions_conflict`, valores financeiros do candidato `NULL` e versões listadas separadamente no resumo do controller com arquivo e linha. Mês com zero ou vários demonstrativos → um único candidato de mês retido (`monthly_statement_missing` / `multiple_statements_for_period`), sem escolher documento. Cada componente pertence a exatamente um candidato. `id_externo` da fatura não depende mais do hash do arquivo.
- **Linha `ready` (C4).** Só quando o componente não tem nenhum bloqueio.
- **Testes (C5).** `ap_value_conservation` (contagem e R$ de enriquecimento → componentes → linhas; `amount_status` coerente), `ap_component_population_covered` (exatamente um título por componente), `ap_allocation_totals_close` (left join, linhas órfãs, seq 1..n) e `ap_released_lines_valid_against_references` (CC ativo, contas postáveis e par do crosswalk conferidos direto nos cadastros). Rodam no build real e nos fixtures sintéticos que liberam títulos.
- **Emissão (C6).** Reembolso: `data_emissao` = último dia do mês de competência, **premissa operacional configurada** (`reimbursement_issue_date_rule`), registrada em `issue_date_basis` e mantida como pergunta ao cliente no `controller_summary.md`. Fatura: sem emissão explícita no demonstrativo, continua retida (`data_disponibilizacao` não é tratada como emissão). `reject_all` mantém a retenção nas duas rotas.

Verificação: `run.py --output .\output` — dbt PASS=61, WARN=0, ERROR=0. Liberados **16 reembolsos / 16 rateios, R$ 1.363,27** (julho: 7; agosto: 9); retidos 2 reembolsos da matrícula 1053 (CPF inválido, R$ 245,48) e as 2 faturas pelos bloqueios reais. Conservação: 573 chaves / R$ 31.842,73 = componentes + rotas fora do AP; 0 linhas `ready` com bloqueio. `tests_synthetic.py` PASS, incluindo liberação de reembolso, arquivos do ERP sem BOM lidos em UTF-8 estrito, AMEX em caixa mista roteado pelo tipo e reenvio do demonstrativo com os mesmos `id_externo`. As 19 entradas do manifesto de profiling mantiveram SHA-256.

Verificação adicional de C3: duas versões sintéticas de um demonstrativo (R$ 10,00 e R$ 11,00) geram um candidato com valor financeiro `NULL`, bloqueio `statement_versions_conflict` e nenhuma fatura liberada. O resumo mostra ambas as ocorrências e seus localizadores, sem somá-las. Nos arquivos reais, `ap_titulos.csv` e `ap_rateios.csv` permaneceram byte a byte idênticos após o ajuste.

O resumo DQ final contém 23 incidências `auto_fixable` com 23/23 localizadores e antes→depois preenchidos, 272 `needs_client` e 136 `rule_based` (contagens de incidências, não candidatos únicos). Testes dbt incluem conservação de população e valor conhecido do resumo mensal e integridade dos buckets/correções DQ. `& '.\.venv\Scripts\python.exe' tests_synthetic.py` cobre rerun, conflitos, rotas e liberação/retenção integral do título. Os 15 arquivos em `data/` mantiveram SHA-256 antes/depois.

## Estado vigente em 28/09/2026 — controles pós-parecer e conciliação

O corte provisório é **2026-09**, configurado em `config/client.json`. `run.py` usa a data corrente como `--as-of-date` quando não informada e retém competência anterior ao corte, vencimento já passado e `id_externo` presente no ledger de títulos emitidos. O `config/issued_titles.csv` está vazio porque falta extrato de títulos do ERP; preenchê-lo com `id_externo,valor_total,status,approved_at` para novas operações. A correspondência entre lançamentos históricos manuais e candidatos exige extração do ERP, pois os IDs podem ser diferentes. Se o valor de um título emitido mudar, o pipeline mantém o título original bloqueado e registra um candidato em `ap_ajustes_candidatos.csv`; a emissão/importação do ajuste depende de regra do cliente para data, vencimento e crédito negativo.

```powershell
& '.\.venv\Scripts\python.exe' run.py --output .\output --as-of-date 2026-09-28
& '.\.venv\Scripts\python.exe' tests_data_controls.py
& '.\.venv\Scripts\python.exe' tests_synthetic.py
& '.\.venv\Scripts\python.exe' bank_reconciliation.py
& '.\.venv\Scripts\python.exe' tests_bank_reconciliation.py
```

O build escreve numa pasta temporária irmã de `output/`, executa dbt e as exportações, e só troca a saída publicada após sucesso. Falha de arquivo desconhecido ou teste preserva os imports anteriores. `output/run_summary.json` grava hash do código, manifesto de entradas, ledger de emitidos, data-base e corte. A conciliação preserva hash/linha do extrato e hash do script em `reconciliation/bank_reconciliation_summary.json`.

Resultado na amostra: **67/67 tarefas dbt aprovadas**, 573 candidatos canônicos, 20 candidatos de título, **0 títulos e 0 rateios para importação**. O DQ registra 2.336 incidências (1.978/172/186 por `auto_fixable`/`needs_client`/`rule_based`) e 1.955 eventos de normalização. Duas reexecuções finais produziram o mesmo SHA-256 de `dq_report.csv`: `475d82c4143da4bfa321a9b2d028d0b7c8628c777c52cd3ee10d85003df38396`. As verificações específicas da amostra e a suíte sintética passaram. A conciliação reproduz o oráculo da seção 4 de `docs/parecer_revisao_independente.md`, inclusive PIX duplicado, título aberto, diferença de um centavo, fatura com R$ 305,27 extras e VISA R$ 33,20. Não há ação automática no ERP.

Antes de importar uma competência nova, confirmar o corte com o cliente, carregar e reconciliar o universo de títulos já emitidos no ERP, aprovar regras de identidade/contas/rateios pendentes e revisar `output/ap_titulos.csv`, `output/ap_rateios.csv`, `output/controller_summary.md` e `reconciliation/`. Julho/agosto não devem ser reimportados.
