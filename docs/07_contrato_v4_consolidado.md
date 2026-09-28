# Contrato canônico — Uber for Business → Contas a Pagar (v4 — consolidado e congelado)

**Data:** 27/09/2026
**Substitui:** `05_contrato_v3.md` e seu adendo `06_contrato_v3-1_adendo_aba_resumo.md`, além das versões anteriores (preservadas como histórico). Esta v4 é a referência local vigente.
**Considera:** `02_contrato_decisoes_anteriores.md`.
**Status:** **congelado para implementação.** Consolida as cinco correções financeiras, a exclusão da aba Resumo e os esclarecimentos finais aprovados: serial temporal XLSX, ingestão única por hash e fixture A15. Não há decisão arquitetural pendente para iniciar o case. Mudanças posteriores devem registrar motivo e nova versão; não é necessária outra rodada geral de revisão.

Congelamento significa uma base de desenho aprovada. Não significa código implementado, testes executados ou valores liberados financeiramente. Essas evidências serão produzidas na implementação. A conclusão do case admite retenções explícitas e perguntas ao cliente; não depende de resolver todas as ambiguidades das fontes.

Legenda de status usada neste documento:
- **Aprovado** — decisão tomada pelo usuário nesta rodada.
- **Evolução futura** — melhoria fora da entrega atual.
- **Lacuna declarada** — o que os dados/documentos não permitem concluir; não é preenchido por suposição.

---

## 1. Contexto mínimo

Case técnico (Alchemy ERP). Pipeline que recebe relatórios Uber for Business em CSV ou XLSX, trata, valida e gera contas a pagar (`ap_titulos.csv` + `ap_rateios.csv`) e o que ficou retido com motivo; depois consolida e gera insights que reconciliam com títulos e retenções.

Requisitos da TASK que este contrato atende diretamente:
- não codificar para arquivos específicos (nome, formato e ordem de colunas mudam);
- reexecução sobre entradas iguais ou sobrepostas não duplica títulos (ERP só deduplica por `id_externo`);
- todo valor rastreável até arquivo e registro de origem;
- mesmas entradas, configurações, regras e decisões → mesma saída;
- títulos e rateios fecham ao centavo, sem plug.

## 2. Fatos dos dados (com população e limite declarados)

Registro de evidências herdado da v2: profiling (`profiling/output/*`) e rederivação independente ali atribuída ao revisor (leitor próprio, csv + openpyxl). A elaboração desta v3 não refez a auditoria dos datasets nem transforma esses números em resultados de testes da implementação. Eles são referências a confrontar com a execução real; eventual diferença deve ser explicada, nunca ajustada artificialmente para atingir uma contagem.

| Afirmação | População | Fonte | Limite |
|---|---|---|---|
| 588 ocorrências transacionais (281 + 286 + 21) | 3 arquivos | ambas | — |
| 573 **chaves candidatas** `(trip_id, minuto UTC, tipo)` | 588 ocorrências | ambas | Resultado da chave candidata, não contagem de eventos econômicos reais |
| 13 grupos equivalentes, 2 conflitantes, 0 repetidos no mesmo arquivo | 573 chaves candidatas | ambas | — |
| Nenhuma chave candidata de Fare repete viagem | 573 chaves candidatas | revisor | Em ocorrências, viagens sobrepostas têm 2 ocorrências de Fare |
| Nenhuma viagem+tipo com timestamps distintos | 588 ocorrências | revisor | Ausência na amostra não garante o futuro |
| `Payments made by employees/guests` = 0 em todas as linhas com valor (587 em BRL, 1 vazio; 302 CSV e 286 XLSX em moeda local) | 588 ocorrências | revisor | **A regra de subtração do valor pago pelo empregado não é testada por estes dados.** O valor devido é definido pela regra 5 do README, não por fórmula inferida |
| `Transaction Amount in BRL` = `Total Fare in BRL` em 585/588; exceções: 2 linhas com +7,70 e 1 CLP sem BRL | 588 ocorrências | ambas | Serve como checagem de DQ, não como definição |
| Segundos = 0 no timestamp do XLSX | 286/286 | revisor | Sugere precisão de minuto, **não prova** a precisão do layout |
| Resíduo máximo de float Excel em valores ≈ 1e-14 | células monetárias do XLSX | profiling | — |
| `Invoice Number` (CSV-BR) = `Uber Fare Invoice#` (XLSX) nos 6 pares sobrepostos; 272/272 valores XLSX no padrão `BR-\d{4}-\d{7}` | 6 pares; 286 linhas XLSX | revisor | CSV de julho é 100% `--`: sem evidência de valor para esse layout |
| Colunas exclusivas dos CSV (taxas, endereços, distância, duração, `Invoices`) iguais após parsing nos 7 pares equivalentes julho × complemento; nos 2 conflitos só diferem gorjeta local e Total Fare local | 9 pares CSV × CSV | revisor | Pares XLSX × CSV não são comparáveis nesses campos (decomposição de tarifa diferente) |
| Padrão `Solicitado por: <email>` em Conditional Columns | 4 linhas | profiling | Outros formatos desconhecidos |

## 3. Decisões aprovadas (inclui histórico)

| # | Decisão | Origem |
|---|---|---|
| A1 | Stack Python + DuckDB + dbt; pandas fora do caminho crítico; `run.py` único; banco reconstruído a cada execução | rodada atual |
| A2 | Fronteira: Python = ingestão, detecção de layout/formato, CPF/CNPJ, escrita dos CSVs do ERP; SQL = staging → marts | rodada atual |
| A3 | **Grain:** "Uma linha representa um movimento transacional reportado pela Uber cuja identidade e representação foram resolvidas a partir das ocorrências recebidas." Viagem, ocorrência em export e movimento canônico são conceitos distintos | decisões anteriores #1 |
| A4 | Admissão canônica ≠ aprovação financeira: presença na camada canônica não significa "liberado para pagar" | anteriores #7 |
| A5 | Regra de duplicatas em 4 casos (seção 7.3) + Fare duplicado na mesma viagem → quarentena | rodada atual (P4) |
| A6 | `int_transactions` com uma linha por chave, complementado por views de consumo (seção 7.5) | rodada atual + anteriores #6 |
| A7 | Colunas exclusivas de layout ficam na RAW, exceto número de invoice | rodada atual; alinhado a anteriores #3 |
| A8 | Competências (fatura: mês UTC; reembolso: mês local) calculadas em `int_enriched`, não no canônico | rodada atual |
| A9 | Seed mínimo `resolutions.csv` para decisões por transação (seção 8) | rodada atual (P7); atende anteriores #9 |
| A10 | Equivalência campo a campo com matriz de disponibilidade (seção 7.2) | rodada atual (P1); implementa anteriores #4 |
| A11 | Ocorrência com identidade não interpretável nunca é agrupada (seção 7.3) | rodada atual (P3); anteriores #7 |
| A12 | `accept_occurrence` usa os campos da ocorrência escolhida; `reject_all` permanece retido e rastreável | correções financeiras aprovadas para v3 |
| A13 | Seed resolve apenas alternativas da mesma chave; não remove bloqueios independentes, especialmente múltiplos Fares entre chaves | correções financeiras aprovadas para v3 |
| A14 | Decisão depende do conjunto exato de ocorrências examinadas e de uma única decisão ativa por chave | correções financeiras aprovadas para v3 |
| A15 | Fonte menos precisa não apaga divergências temporais; comparação não reduz precisão em função do grupo | correções financeiras aprovadas para v3 |

## 4. Critério de inclusão de colunas

Uma coluna entra em `stg_uber_transactions` somente se alguma etapa posterior a consome (vínculo, classificação, destino por pagamento, competência, resumo por CC, políticas, checagens de DQ ou evidência de conflito). Tudo o mais permanece acessível na RAW via `occurrence_id`.

## 5. RAW (Python)

### `raw_files` — uma linha por arquivo ou aba
`file_sha256`, `source_file`, `source_sheet` (NULL em CSV), `file_format`, `encoding`, `delimiter`, `layout_id`, `company_header_raw` (valor do cabeçalho `Company:`, texto como veio), `header_row`, `n_data_records`, `n_ignored_records`, `sheet_role` (`transactions` | `ignored_non_transactional`), `report_date_raw` (texto, sem conversão de fuso — D1).

**Validação de conta (P6):** identificar primeiro o papel da aba. Nas fontes/abas transacionais Uber, comparar `company_header_raw` ao nome esperado no config; ausência ou divergência causa erro explícito. Abas `ignored_non_transactional` e arquivos cadastrais de apoio não precisam de cabeçalho Uber `Company:`. O cabeçalho não forma identificadores. A validação é uma barreira para o cliente configurado, não prova de identidade universal da conta. Esta entrega opera um cliente/escopo de conta por execução.

**Aba Resumo excluída:** registrar somente o inventário e o motivo `ignored_non_transactional`. Seus valores e inconsistências não alimentam análise, reconciliação, conflitos ou decisões financeiras. A aba BR fornece as transações do XLSX; `demonstrativo_mensal_uber.csv` fornece os demonstrativos. Preservar o arquivo original integralmente. A identificação do papel depende do conteúdo/layout, não de exceção hardcoded pelo nome Resumo.

**Arquivo idêntico reenviado:** ler e persistir o conteúdo uma vez por SHA-256 completo. Registrar todos os nomes/caminhos recebidos no inventário/log; escolher deterministicamente o nome de referência das ocorrências. As invariantes de contagem referem-se ao conteúdo único recebido. Outro nome com bytes idênticos não produz novas ocorrências nem repetição dentro do arquivo. Hash diferente continua fonte distinta, mesmo quando o conteúdo de negócio é equivalente. Duplicatas de linhas dentro de um arquivo não são removidas pela ingestão.

### `raw_uber_occurrences` — uma linha por **registro lógico** de dados
- **Unidade:** registro lógico do CSV (um registro pode ocupar várias linhas físicas por campos multilinha) ou linha da aba XLSX.
- **Localizadores:** `source_row` (número do registro lógico; em XLSX, a linha da aba), `source_line_start`, `source_line_end` (linhas físicas; NULL em XLSX).
- `occurrence_id` = sha do arquivo (16 caracteres) + aba + `source_row`.
- Demais colunas: `file_sha256`, `source_file`, `source_sheet`, `layout_id`, e valores como mapa `{cabeçalho original → texto original}`.

### Mapeamento de layouts (seed ou YAML)
Por layout: cabeçalhos aceitos por campo canônico, **disponibilidade** do campo (seção 7.2) e precisão temporal documentada por campo. Precisão descreve a leitura da fonte; não autoriza reduzir valores para fazer duas ocorrências coincidirem.

### Config do cliente
- `client_id` (ex.: `madeireira_parana`) — namespace do `transaction_id` (P6).
- `expected_company_header` — valor esperado em `Company:`.
- `date_format_overrides` — declarações explícitas de formato de data por `file_sha256` + coluna, usadas **somente** quando a coluna não oferece prova (D3). Cada uso é registrado no log.

## 6. `stg_uber_transactions` — uma linha por ocorrência

Invariante: `count(raw_uber_occurrences) = count(stg_uber_transactions)`. Legenda: **CSV** = ambos os CSV; **XLSX** = aba BR.

### 6.1 Linhagem e parsing
| Coluna | Tipo | Nulo | Regra |
|---|---|---|---|
| `occurrence_id` | VARCHAR | não | Único |
| linhagem (`file_sha256`, `source_file`, `source_sheet`, `source_row`, `source_line_start/end`, `layout_id`) | — | conforme RAW | Repassada |
| `parse_errors` | VARCHAR[] | sim | Campos não interpretados; o registro **não** é removido |

### 6.2 Identidade
| Coluna | Tipo | CSV | XLSX | Regra |
|---|---|---|---|---|
| `trip_id` | VARCHAR | `Trip/Eats ID` | `Trip/Eats ID` | Trim + minúsculas |
| `transaction_ts_utc` | TIMESTAMP | `Transaction Timestamp (UTC)` | `Transaction timestamp (UTC)` | Precisão original preservada (não truncada nesta camada); D2/D3 |
| `transaction_type` | VARCHAR | `Transaction Type` | `Transaction type` | Trim; valor fora de {Fare, Adjustment, Tip, Admin Fee} preservado; motivo de retenção `unknown_transaction_type` na camada de identidade |

**Regras de data/hora (D2, D3):**
- Tipo `TIMESTAMP` sem fuso; semântica no sufixo `_utc` / `_local`; offset em coluna própria. `TIMESTAMPTZ` não é usado (evita conversão pelo fuso da sessão).
- Para datas textuais ambíguas entre DD/MM e MM/DD, formato identificado **por coluna, com prova**: algum valor válido desambigua a posição do dia (> 12). Valores contraditórios na mesma coluna → falha sempre.
- Sem prova nesse caso → só interpretar com declaração em `date_format_overrides` para aquele `file_sha256` + coluna; senão a execução falha. Formatos observados: CSV-US timestamp `DD/MM/YY HH:MM`, datas `MM/DD/YYYY`, horas `h:MM AM/PM`; CSV-BR `DD/MM/YYYY` e `HH:MM`.
- Datas/horas numéricas nativas do XLSX seguem o calendário e a representação do workbook; não dependem de prova DD/MM versus MM/DD. Texto dentro de XLSX segue as regras textuais. Ausências continuam ausências. O parsing deve ser verificado contra a representação original; resíduos técnicos não podem ser resolvidos pela escolha do valor que facilita deduplicação.
- **Serial temporal XLSX:** converter com aritmética decimal e calendário do workbook. Antes de construir o timestamp e truncar a chave, calcular a distância absoluta ao segundo inteiro mais próximo (HALF_UP). Resíduo zero mantém o valor; resíduo positivo menor que `1e-6` segundo admite normalização técnica para esse segundo, com log e serial original preservado. Frações iguais ou superiores ao limite não são descartadas: preservar sua precisão suportada ou registrar erro explícito se não representável. Não truncar segundos fracionários antes dessa verificação. Aplicar a mesma leitura técnica aos campos nativos de data/hora; não escolher a conversão por favorecer overlap.

### 6.3 Tempo da corrida
| Coluna | Tipo | Regra |
|---|---|---|
| `request_ts_utc`, `request_ts_local` | TIMESTAMP | Data + hora; local **como informado**, não recalculado |
| `dropoff_ts_utc`, `dropoff_ts_local` | TIMESTAMP | Idem; usados na checagem de duração negativa |
| `request_utc_offset_min` | INTEGER | `-3:00:00` / `-03:00` → −180; formato desconhecido → `parse_errors` |

### 6.4 Pessoa
| Coluna | Origem | Regra |
|---|---|---|
| `email` | `Email` | Trim + minúsculas; `--` → NULL; não remove `+tag` nem troca domínio |
| `requester_email` | `Conditional Columns` | Extração **sintática** do padrão `Solicitado por: <email>`; outro formato → NULL. Não vincula nem atribui responsabilidade (D4, aprovado como extração sintática) |
| `uber_employee_id_raw` | `Employee ID` | Texto como veio; **nunca** usado para vínculo |
| `first_name`, `last_name` | `First Name`/`First name`, `Last Name`/`Surname` | Trim; nunca usados para vínculo |
| `uber_group` | `Group` | Trim; nunca usado como centro de custo |

### 6.5 Uso e pagamento
| Coluna | Origem | Regra |
|---|---|---|
| `service` | `Service` | Trim |
| `program` | `Program` / `Programme` | Trim |
| `city`, `country` | `City`, `Country` | Trim |
| `expense_code` | `Expense Code` / `Expense code` | Trim + maiúsculas; `--` → NULL; mudança registrada no log |
| `expense_memo` | `Expense Memo` / `Expense memo` | Trim; `--` → NULL |
| `payment_method_raw` | `Payment Method` / `Payment method` | Trim |
| `card_brand`, `card_last4` | extraídos de `payment_method_raw` | Extração **sintática** de `<BANDEIRA> - <4 dígitos>`; `last4` como texto; fora do padrão → NULL; **classificação (corporativo/pessoal) só em `int_enriched`** |

### 6.6 Valores — DECIMAL(15,2)
| Coluna | CSV | XLSX | Uso |
|---|---|---|---|
| `amount_brl` | `Transaction Amount in BRL` | `Transaction amount in BRL` | Valor devido pela empresa (README regra 5); NULL permanece NULL |
| `total_fare_brl` | `Total Fare in BRL` | `Totals Fare in BRL` | Checagem de DQ |
| `employee_paid_brl` | `Payments made by employees/guests in BRL` | idem | Regra 5; **comportamento com valor ≠ 0 não observado nos dados** |
| `tips_brl` | `Tips in BRL` | `Tip in BRL (Inclusive of taxes, if any)` | Informativo; o **campo** nunca é somado ao valor. Não confundir com transações do **tipo** Tip, que são movimentos contados normalmente (D5) |
| `amount_local` | `Transaction Amount (local currency)` | `Transaction Amount` | Conferência BRL × local |
| `local_currency` | `Local Currency` | `Local currency code` | Trim + maiúsculas |

**Regras monetárias (D6):**
- Nos campos monetários textuais, separador decimal identificado **por arquivo, com prova** (algum valor com separador seguido de exatamente 2 casas e coerência dos demais valores); sinais contraditórios → falha; valores inteiros sem separadores são inequívocos. Não inferir formato a partir de IDs, horários ou outros campos.
- Células numéricas nativas do XLSX seguem sua representação numérica, não o separador de exibição do Excel. Usar aritmética decimal para dinheiro, preservando o original na RAW.
- Resíduo = distância absoluta entre o valor decimal interpretado e sua quantização HALF_UP para 2 casas. Valor já em centavos é mantido. Para resíduo positivo **< 1e-6**, admitir a normalização técnica com log before → after (ex.: `66.93000000000001`). O limiar é a política aprovada, não prova da causa de um resíduo.
- Resíduo ≥ 1e-6 ou valor não representável no tipo de destino → `parse_errors`, sem valor monetário inventado. Falha de parsing e ausência não viram zero; a falha deve chegar à validação downstream, mesmo quando a identidade está resolvida.
- `tips_brl` participa da comparação de equivalência como campo informativo (D5): pode gerar conflito falso se a semântica diferir entre layouts; consequência aceita = atraso, não valor errado.

### 6.7 Documento
| Coluna | CSV | XLSX | Regra |
|---|---|---|---|
| `uber_invoice_number` | `Invoice Number` | `Uber Fare Invoice#` | `--` → NULL. Mapeamento aprovado para o case, sustentado pelas correspondências reportadas nos 6 pares CSV-BR × XLSX e pelo padrão comum; não é garantia universal de equivalência documental. **Sem evidência de valor no CSV de julho.** Teste marca valores fora do padrão observado. `Invoices` do CSV não é mapeado como equivalente |

**Somente na RAW:** componentes de tarifa, taxas, impostos, dados/links/arquivos de parceiro e de invoice, `Uber Fare Invoice Date` (D7), endereços, distância, duração, membership savings, other charges, total taxes, `Invoices`.

## 7. Camada de identidade

### 7.1 Três conceitos de identidade (anteriores #2)
| Conceito | Coluna | Papel |
|---|---|---|
| Identidade de negócio candidata | `business_key` | Agrupa ocorrências potencialmente referentes ao mesmo movimento |
| Identificador canônico | `transaction_id` | Identifica a entidade resolvida: `'UBR\|' + client_id (config) + '\|' + business_key` (P6). Não usa texto do arquivo. Estável **enquanto a regra da chave e o `client_id` não mudarem** |
| Ocorrência na fonte | `occurrence_id` | Chega ao registro recebido |

`business_key` = `trip_id | transaction_ts_utc truncado ao minuto (AAAA-MM-DDTHH:MM) | transaction_type`.

**Precisão de minuto (D8):** o truncamento ocorre **somente na chave**; a coluna mantém a precisão original. Um teste falha a execução se algum layout trouxer segundos ≠ 0 **e** duas ocorrências colidirem na mesma chave. Lacuna declarada: com todas as fontes em precisão de minuto, dois movimentos legítimos no mesmo minuto em arquivos diferentes seriam fundidos, e isso é indetectável com os dados disponíveis.

O `id_externo` dos títulos **não depende** de `transaction_id` (usa número do demonstrativo; matrícula + mês, com identificação do tipo de título). Isso evita que a identidade interna determine diretamente a chave de importação. Não garante segurança de alterações de valor, beneficiário ou competência após importação: nesta entrega, títulos já importados/pagos não são atualizados automaticamente.

Valores monetários e atributos mutáveis **não** entram na chave.

### 7.2 Equivalência campo a campo (A10)
- **Matriz de disponibilidade:** campo canônico × layout → `available` | `not_in_layout`. Nesta versão, todos os campos das seções 6.2–6.6 estão disponíveis nos três layouts (verificado no mapeamento de cabeçalhos); um teste falha se um layout novo deixar de fornecer um campo sem que a matriz seja atualizada.
- **Regra:** para cada campo comparável, considerar as ocorrências cujo layout o fornece. Um único estado/valor distinto é consistente; mais de um é divergência. NULL participa como estado explícito, sem colidir com texto literal. Campo `not_in_layout` não participa; se nenhum layout fornecer o campo, ele fica indisponível/NULL, sem conflito artificial. `--`/vazio tecnicamente normalizados para NULL em layout que fornece o campo participam como esse estado. Falhas de parsing são preservadas como erros e não equivalem silenciosamente a ausência legítima.
- **Consistência do grupo:** a regra é avaliada sobre o grupo inteiro, não por pares; uma ocorrência sem o campo não serve de ponte entre valores diferentes (ex.: A=`ADM`, B sem campo, C=`AERO` → conflito).
- **Precisão temporal (A15):** comparar os timestamps resultantes do parsing técnico documentado sem reduzir sua precisão por causa de outro layout do grupo. Valores diferentes permanecem divergentes, mesmo que coincidam quando truncados. Uma fonte menos precisa não apaga diferenças já observáveis; possíveis falsos conflitos ficam retidos até esclarecimento. O truncamento da chave em 7.1 não é regra de igualdade de conteúdo.
- **Invoice:** fora da regra geral; preenchimento por enriquecimento (seção 7.4).
- **Limite declarado:** entre XLSX e CSV, equivalência significa igualdade **nos campos do núcleo**, não nos detalhes exclusivos de cada layout.
- `content_hash` é apenas fingerprint informativo. Não decide equivalência nem validade de resolução; a seção 8 usa o conjunto exato de ocorrências.

### 7.3 `int_transaction_versions` — uma linha por ocorrência
| Coluna | Regra |
|---|---|
| `occurrence_id`, `business_key`, `transaction_id` | — |
| `content_hash` | sha256 dos campos comparáveis normalizados (fingerprint) |
| `n_occurrences_key` | Ocorrências com a mesma chave |
| `same_file_repeat` | Chave repetida no mesmo arquivo |
| `conflict_fields` | Campos que violam a regra 7.2 no grupo |
| `key_status` | Precedência abaixo |

**Precedência de `key_status`:**
1. `identity_unresolved` — `trip_id`, `transaction_ts_utc` ou `transaction_type` com falha de parsing ou nulo. **Uma linha por ocorrência, nunca agrupada** (evita que o SQL agrupe todas as chaves NULL). Sempre em quarentena.
2. `within_file_duplicate` — mesma chave repetida no mesmo arquivo. Quarentena, NEEDS_CLIENT.
3. `conflict` — `conflict_fields` não vazio. Quarentena, NEEDS_CLIENT, sem precedência presumida.
4. `equivalent` — várias ocorrências, sem conflito. Uma entidade; AUTO_FIXABLE com log.
5. `single`.

**Regra adicional (A5, P4):** duas ou mais chaves **Fare** com o mesmo `trip_id` → todas recebem `fare_duplicate_trip = true` e vão para quarentena, NEEDS_CLIENT.

> **Regra de risco, não semântica comprovada.** Os dados não contêm o caso, e nem o README nem a documentação consultada dizem se a Uber pode emitir mais de um Fare por viagem. Tratar como transações distintas arriscaria pagamento em dobro; reter apenas atrasa o título até a confirmação. Revisar se o cliente ou a Uber documentarem o comportamento.

Mesma viagem com **Adjustment** ou **Tip** em timestamps diferentes: transações distintas, com flag informativo `same_trip_type_multi_ts` (não bloqueia). Lacuna declarada: uma correção de timestamp entre exports seria indistinguível de dois movimentos legítimos.

`key_status` descreve a classificação das ocorrências antes de decisões humanas e é preservado para auditoria. Outros motivos de retenção são independentes dessa precedência: `fare_duplicate_trip` e `unknown_transaction_type` não podem desaparecer porque a chave foi classificada como `conflict` ou `single`. O tipo desconhecido é preservado, mas nunca segue para títulos nesta entrega.

### 7.4 `int_transactions` — uma linha por chave (ou por ocorrência, se `identity_unresolved`)
| Coluna | Regra |
|---|---|
| `transaction_id`, `business_key`, `key_status`, `n_occurrences` | — |
| `occurrence_ids` | VARCHAR[] ordenado; rastreio até arquivo/registro |
| campos de negócio | Sem escolha aplicada: valor comum quando consistente; NULL quando divergente. Com `accept_occurrence` aplicada: **todos os campos de negócio efetivos vêm da ocorrência escolhida**, sem mistura de alternativas |
| `conflict_fields` | Divergências originais preservadas mesmo após resolução; inclui invoice quando houver valores não nulos diferentes |
| `uber_invoice_number` | Sem escolha aplicada: único valor não nulo por enriquecimento; valores não nulos diferentes geram conflito. Com escolha aplicada: valor da ocorrência escolhida, inclusive NULL. Não se presume o significado de `--` |
| `amount_status` | `known` / `missing_in_source` / `disputed` / `parse_failed`; representa o valor efetivo conforme regras abaixo |
| `resolution_status` | `none` / `applied` / `stale` (seção 8) |
| `resolution_action`, `chosen_occurrence_id` | Ação e ocorrência associadas ao registro de decisão; só alteram o conteúdo se `resolution_status = applied` |
| `retention_reasons` | Lista determinística de motivos canônicos ainda impeditivos, incluindo rejeição explícita; regras abaixo |
| `is_quarantined` | Verdadeiro se e somente se `retention_reasons` não estiver vazia |

**Conteúdo efetivo e valor:**
- `accept_occurrence` aplicada fornece os valores da ocorrência selecionada, sua origem e seus erros de parsing. Não corrige valores e não dispensa validação financeira, cadastral ou de reconciliação.
- Sem escolha aplicada, se `amount_brl` apresentar estados/valores divergentes entre as ocorrências, `amount_status = disputed`. Se não houver divergência, mas houver falha de parsing nesse campo, `parse_failed`; se houver valor interpretado, `known`; caso contrário, `missing_in_source`. Indisponibilidade do campo no layout permanece identificável pela matriz e RAW.
- Com escolha aplicada, o status é o da ocorrência escolhida: falha de parsing → `parse_failed`; valor ausente → `missing_in_source`; valor interpretado → `known`. As demais alternativas continuam acessíveis e o conflito original não é apagado.
- `reject_all` não escolhe valor efetivo para pagamento. Os valores comuns e os estados originais podem permanecer para contexto, sempre em retenção. Alternativas conflitantes não são somadas como obrigações independentes.

**Motivos de retenção, avaliados independentemente:**
1. Identidade não interpretável: `identity_unresolved`.
2. Tipo fora do domínio aceito: `unknown_transaction_type`.
3. Mais de uma chave Fare da mesma viagem: `fare_duplicate_trip`, mesmo que exista escolha aplicada dentro de uma chave.
4. Repetição dentro do arquivo e/ou divergência entre ocorrências: motivos `within_file_duplicate` e/ou `conflict`, removidos da lista de impedimentos apenas por uma `accept_occurrence` válida para essa chave. A evidência histórica permanece.
5. Decisão desatualizada: `resolution_stale`, independentemente de a classificação atual ter passado a `single` ou `equivalent`.
6. `reject_all` aplicada: `rejected_by_decision`, sempre retido.

Para identidade não interpretável, `business_key` e `transaction_id` permanecem NULL. A linha é individualizada e vinculada por seu único `occurrence_id`; não se inventa uma identidade de negócio. Erros de parsing em campos não identitários permanecem disponíveis às validações posteriores, inclusive quando o movimento está canonicamente resolvido.

### 7.5 Views de consumo (A6, P2)
Motivo: `SUM()` ignora NULL; somar diretamente `int_transactions` faria disputas e BRL ausente desaparecerem dos totais sem erro. As views separam retenções canônicas, mas a validação financeira ainda deve explicitar valores ausentes ou com parsing inválido.

| View | Conteúdo | Quem consome |
|---|---|---|
| `int_transactions_resolved` | `is_quarantined = false`; inclui valores ausentes ou não interpretados para validação financeira posterior; nunca inclui rejeição aplicada | **Única entrada** para `int_enriched`; títulos somente após validação downstream |
| `int_transaction_conflicts` | `is_quarantined = true`; uma linha por candidato retido, inclusive `rejected_by_decision` | Relatório de retenções, pendências e marts |

Invariante: `count(resolved) + count(conflicts) = count(int_transactions)`, sem interseção. Toda ocorrência de `int_transaction_versions` pertence a exatamente um candidato de uma das views, incluindo rejeitados e identidades não interpretáveis. Alternativas são consultadas pela relação de ocorrências com `int_transaction_versions` e STAGING; sua expansão não altera o grain nem multiplica os totais da view. Conflitos não constituem obrigações somáveis. Os relatórios distinguem valor conhecido, desconhecido e em disputa.

## 8. Decisões por transação — seed `resolutions.csv` (A9)

**Problema resolvido:** com o banco reconstruído a cada execução, a resposta do cliente a uma pendência precisa ser uma entrada; caso contrário, só seria aplicável editando a origem, o código ou o ERP.

**Escopo nesta entrega:** aceitar uma ocorrência ou rejeitar todas as alternativas **da mesma chave** para `conflict` e/ou `within_file_duplicate`. A decisão resolve somente esses motivos; não remove `fare_duplicate_trip`, tipo desconhecido, identidade não interpretável ou impedimento financeiro posterior. Múltiplos Fares entre chaves continuam retidos e `NEEDS_CLIENT`. Correções de cadastro (crosswalk, CPF, CC, aliases, regra de Admin Fee) chegam como nova versão dos arquivos de cadastro/config.

| Coluna | Conteúdo |
|---|---|
| `business_key` | Chave decidida |
| `occurrence_ids_seen` | Array JSON, ordenado e sem repetição, com o conjunto exato de `occurrence_id` examinados; substitui `versions_seen` da v2 |
| `action` | `accept_occurrence` / `reject_all` |
| `chosen_occurrence_id` | Obrigatório e pertencente ao conjunto examinado se `accept_occurrence`; vazio se `reject_all` |
| `decided_by`, `decided_at`, `reason` | Auditoria |

- O seed representa as decisões ativas da execução, **no máximo uma por chave**, dentro do cliente configurado. Preservar suas versões junto às entradas para reproduzir decisões anteriores; não criar workflow de aprovação nesta entrega.
- Configuração estruturalmente inválida (ação desconhecida, mais de uma decisão por chave, auditoria obrigatória ausente ou ocorrência escolhida fora do conjunto declarado) falha com erro explícito. Não escolher arbitrariamente uma linha do seed.
- Aplicar somente se o conjunto atual de ocorrências da chave for exatamente `occurrence_ids_seen`. Para `accept_occurrence`, exigir também que a ocorrência escolhida exista e pertença à chave; `reject_all` não exige ocorrência escolhida. Se a evidência mudou ou a ocorrência escolhida deixou de existir, `resolution_status = stale`, emitir `RESOLUTION_STALE` e manter o candidato retido. Decisão cuja chave deixou de existir é reportada como não aplicável/desatualizada, sem fabricar transação.
- O identificador da ocorrência depende do hash do arquivo: alteração de arquivo, incluindo invoice, invalida conservadoramente a decisão. Reexport equivalente também pode exigir nova decisão. **Esse custo operacional é aceito para evitar um mecanismo complexo de continuidade de decisões no case.** `content_hash` não é usado para contornar essa invalidação.
- `accept_occurrence` aplicada tem o efeito de conteúdo descrito em 7.4, removendo apenas conflitos/repetições da mesma chave. `reject_all` aplicada permanece na view de retenções com `rejected_by_decision`, nunca na view resolvida.
- **Nesta entrega o seed vai vazio** (não há respostas do cliente). Fixtures sintéticos demonstram o mecanismo; não são misturados aos dados do case nem apresentados como respostas reais do cliente.
- **Fora do escopo:** resolução automatizada entre chaves, framework genérico de decisões, fluxo de aprovação e alteração de títulos já importados ou pagos.

## 9. Testes deste trecho

- Conservação: `count(raw) = count(stg) = count(versions)`; cobertura por ocorrência e partição da seção 7.5. Contagem igual sozinha não basta: nenhuma ocorrência pode desaparecer ou se vincular a dois candidatos.
- `occurrence_id` único e não nulo em cada tabela por ocorrência (RAW, STAGING e versões). `transaction_id` único e não nulo nas linhas de `int_transactions` com identidade interpretável; pode se repetir na tabela de versões. Linhas `identity_unresolved` são individualizadas pelo único `occurrence_id`.
- Linhagem obrigatória: identificador da ocorrência, hash, arquivo, registro e layout. Aba é obrigatória em XLSX e NULL em CSV; linhas físicas são obrigatórias em CSV e NULL em XLSX. Testar domínio de `key_status`, `amount_status`, `resolution_status` e ações de resolução.
- Matriz de disponibilidade cobre todos os campos canônicos de todos os layouts.
- Contagens históricas da seção 2 são referências de conferência da amostra, não condições de produção. Recalcular contagens e valores críticos diretamente das fontes por uma rota independente, comparar com a execução e explicar diferenças. Nenhuma regra de negócio deve depender desses números fixos.
- Sintéticos:
  - registro repetido no mesmo arquivo;
  - colunas reordenadas / cabeçalhos mapeados / CSV↔XLSX → mesmo conteúdo de negócio dentro do escopo comparável; linhagem pode mudar;
  - caso A/B/C de disponibilidade (A=`ADM`, B sem campo, C=`AERO`) → conflito;
  - `trip_id` ou timestamp não interpretável → `identity_unresolved`, não agrupado;
  - dois Fares da mesma viagem → quarentena;
  - tipo desconhecido → preservado e retido;
  - `request_ts_utc` A=`12:00:10`, B=`12:00`, C=`12:00:50`, com `transaction_ts_utc` idêntico e segundos zero → conflito A15; a menor precisão de B não apaga a diferença entre A e C;
  - timestamp transacional com segundos não zero e colisão na chave de minuto → falha D8, em cenário separado;
  - serial temporal XLSX próximo ao segundo por resíduo inferior a `1e-6` segundo → normalização registrada antes da chave; fração material não é apagada;
  - cópia byte a byte com nome diferente → inventário de ambas as origens e conteúdo ingerido uma vez;
  - aba não transacional sem Company → ignorada e inventariada, sem falha de conta;
  - coluna textual ambígua entre DD/MM e MM/DD, sem valor desambiguador → falha (D3); mesma coluna com override declarado → interpretada e registrada no log;
  - coluna com valores contraditórios (um só válido como DD/MM, outro só como MM/DD) → falha mesmo com override;
  - fonte/aba transacional Uber com `Company:` diferente do esperado → falha na ingestão (P6);
  - valor com resíduo abaixo do limite → normalização registrada; resíduo igual ou superior a 1e-6 → erro (D6); NULL e erro nunca viram zero;
  - `Payment Method` fora do padrão;
  - `accept_occurrence` → valores da ocorrência escolhida, histórico preservado e validações downstream mantidas;
  - `reject_all` → retido, rastreável e fora dos títulos;
  - alteração do conjunto de ocorrências → decisão stale e retenção;
  - escolha aplicada dentro de uma chave não libera bloqueio por múltiplos Fares entre chaves.

Essas verificações ainda serão executadas na implementação. Na entrega completa, verificar também títulos/rateios ao centavo e estabilidade de `id_externo` nas reexecuções. Os dados reais e os exemplos sintéticos devem permanecer separados.

## 10. Decisões de parsing e identidade — todas aprovadas

| # | Decisão aprovada | Lacuna declarada |
|---|---|---|
| D1 | `report_date` guardado como texto, sem conversão de fuso; usado só como evidência de corte | O horário de julho informado no README (20:00 Brasília, até minutos) é compatível com o metadado `23:00:12`; isso não é igualdade exata nem prova de fuso dos demais exports |
| D2 | `TIMESTAMP` sem fuso + sufixo `_utc`/`_local` + offset em coluna | — |
| D3 | Datas textuais ambíguas: prova por coluna; sem prova, override por arquivo/coluna; contradição sempre falha. Valores nativos XLSX seguem representação do workbook | Export textual ambíguo dos dias 1–12 exige declaração humana |
| D5 | `tips_brl` mantido como informativo e comparável | Equivalência semântica entre layouts não confirmada; risco aceito = conflito falso (atraso) |
| D6 | Dinheiro textual com formato demonstrado; leitura nativa XLSX separada; decimal; resíduo absoluto positivo < 1e-6 admite HALF_UP com log; ≥ 1e-6 → erro | Limite é política técnica; máximo observado (~1e-14) herdado do profiling |
| D7 | `Uber Fare Invoice Date` só na RAW; achado das 272 datas no relatório como observação do profiling | Sem checagem automatizada; entra depois se o cliente indicar relevância |
| D8 | Truncamento ao minuto só na chave; teste de colisão com segundos | Movimentos legítimos no mesmo minuto em arquivos diferentes são indetectáveis com precisão de minuto |
| D9 | `amount_status` = `known` / `missing_in_source` / `disputed` / `parse_failed` | — |
| P6 | `transaction_id` com namespace `client_id` do config; `Company:` validado contra o config, divergência falha a ingestão | — |

As regras A12–A15 e as seções 7–8 integram o congelamento. Não há aprovação pendente para iniciar a implementação. Pendências sobre dados continuam explícitas e não autorizam criar valores ou precedência entre exports.

## 11. Mudanças em relação às versões anteriores

### v3 e adendo v3.1 → v4 — referência única para execução

- Resumo excluída da análise; validação de conta limitada às fontes/abas transacionais Uber.
- Ingestão única por SHA-256 completo, preservando nomes recebidos; duplicação de linhas dentro da fonte continua visível.
- Resíduos submicrossegundo de seriais XLSX normalizados antes da chave, com limite, log e original preservado.
- Fixture A15 usa horário de request; D8 mantém teste e bloqueio separados.
- Plano de execução e delegação em `08_plano_implementacao.md`. Evidências de execução e code-review serão registradas separadamente das decisões de desenho.

### v2 → v3 — consolidação final para implementação

| Item | Mudança | Motivo |
|---|---|---|
| Aceitação de ocorrência | Conteúdo efetivo e status monetário vêm da ocorrência selecionada; histórico preservado | Evitar remover quarentena sem resolver a representação |
| Rejeição | Permanece nas retenções com motivo explícito | Impedir entrada em títulos |
| Escopo do seed | Somente alternativas da mesma chave; bloqueios independentes permanecem | Evitar liberação de múltiplos Fares por escolha local |
| Validade de decisão | Conjunto exato de ocorrências examinadas, escolha pertencente à chave e uma decisão ativa por chave | Detectar nova evidência sem framework genérico |
| Comparação temporal | Sem redução de precisão em função do grupo | Não ocultar divergências conhecidas |
| Implementação e testes | Parsing nativo/textual separado, nulabilidade por formato, unicidade por grain, rejeitados cobertos | Tornar verificável o contrato sem ampliar arquitetura |

As tabelas abaixo são histórico; regras históricas substituídas não prevalecem sobre o corpo desta v3.

### v1 → v2
| Item | v1 | v2 | Motivo |
|---|---|---|---|
| Namespace do `transaction_id` | `source_account` lido do cabeçalho `Company:` | `client_id` do config; cabeçalho só validado | Texto livre do export poderia variar e dividir o mesmo movimento em chaves diferentes |
| Formato de data sem prova | Falha a execução | Falha, exceto com declaração explícita por arquivo no config | D3 (b) |
| D1–D9, P6 | Abertas | Aprovadas | Decisão do usuário em 27/09 |
| Status | Proposta | Congelado para implementação | — |

### v0 → v1
| Item | v0 | v1 | Motivo |
|---|---|---|---|
| Equação monetária | "A = Total Fare − pago pelo empregado em 585/588" | Pago pelo empregado é sempre 0; regra 5 do README é a autoridade; equação vira checagem | Afirmação da v0 excedia a evidência |
| População das contagens | Implícita | Declarada (ocorrências vs chaves candidatas) | Evitar leitura como eventos reais |
| Unidade da RAW | "linha física" | Registro lógico + localizadores físicos | CSV com campos multilinha |
| Equivalência | Hash de todos os campos | Campo a campo com matriz de disponibilidade | Implementa anteriores #4; caso A/B/C |
| Identidade não interpretável | Não especificada | `identity_unresolved`, nunca agrupada | NULL agrupado pelo SQL |
| Fare duplicado na viagem | Distintos, sem alerta | Quarentena, regra de risco | Decisão P4 |
| Consumo | Tabela única | + views `resolved` / `conflicts` | `SUM()` ignora NULL |
| Precisão temporal | Não especificada na comparação | Precisão por layout; comparação na mais grossa | Evitar falso conflito |
| Identificador canônico | `business_key` | `transaction_id` com namespace de conta | Anteriores #2 |
| Decisões humanas | Adiado | Seed mínimo `resolutions.csv` | Decisão P7; anteriores #9 |
| Invoice | Campo único sem evidência citada | Campo único com evidência e limite | Anteriores: não presumir equivalência documental |

## 12. Limites aceitos e critério de conclusão

- Manter arquitetura, stack, núcleo canônico, detalhes na RAW e aprovação financeira downstream. Não desenvolver multitenancy nem controle de alteração de títulos já pagos nesta entrega.
- A chave é candidata: movimentos distintos com os mesmos identificadores e precisão disponível podem ser indistinguíveis. Aplicar os controles aprovados e declarar esse limite, sem fabricar unicidade.
- Múltiplos Fares entre chaves ficam retidos até esclarecimento do cliente/fornecedor. Adjustment e Tip com timestamps diferentes seguem a regra aprovada com flag, sem afirmar que a fonte fornece um identificador de versão.
- Manter o mapeamento de invoice e Tips aprovado para o case, com suas limitações; a data de invoice permanece na RAW e no relato do profiling. Não iniciar nova pesquisa para bloquear implementação.
- Pagamentos de empregados diferentes de zero não foram exercitados pela amostra. Usar a autoridade do README sobre `Transaction Amount in BRL`, sem reconstrução por fórmula presumida nem desconto duplicado.
- Toda afirmação monetária deve apontar para fonte ou transformação explícita. Não preencher desconhecidos pela diferença do demonstrativo, escolher versões para fechar total ou usar exemplos sintéticos como evidência real.

**Entrega concluída:** todas as ocorrências cobertas e rastreáveis; equivalentes contados uma vez; conflitos e rejeições visíveis sem somar alternativas; desconhecidos preservados; títulos liberados reconciliados e rateios fechando ao centavo; reexecução reproduzível com IDs estáveis; pendências e perguntas ao cliente objetivas no relatório. Retenção justificada é um resultado válido da TASK.

**Próxima etapa:** implementar RAW/STAGING, CANONICAL, enriquecimento/financeiro e saídas/relatórios, nessa ordem. Só reabrir o desenho por falha demonstrada, evidência nova ou requisito necessário da TASK. Melhorias opcionais ficam para evolução futura.
