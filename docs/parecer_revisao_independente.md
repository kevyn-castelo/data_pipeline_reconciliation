# Parecer de revisão independente: pipeline Uber for Business → Contas a Pagar

**Escopo:** revisão de `docs/analise_senior_pipeline.md` e `docs/analise_consultas.py` contra `TASK.md`, `README.md`, o layout do ERP, a política de mobilidade, `run.py`, os modelos dbt e os artefatos de `output/`.
**Data-base:** 28/09/2026.
**Método:** todas as consultas foram feitas em modo somente leitura sobre uma cópia de `output/canonical.duckdb`. `analise_consultas.py` foi reexecutado integralmente. O pipeline atual foi reexecutado numa pasta de verificação temporária, removida depois da comparação. Os SHA-256 de `data/` foram conferidos antes e depois e permaneceram idênticos. As evidências deste parecer podem ser reproduzidas com `docs/parecer_consultas.py`. Nenhum dado de origem foi alterado. Não construí dashboard nem conciliação bancária: o extrato foi apenas lido, para avaliar a lacuna descrita na análise.

**Escala de gravidade:**

| Gravidade | Critério |
|---|---|
| Crítico | Seguido como está, gera lançamento ou pagamento financeiro incorreto. |
| Alto | Afirmação material incorreta, ou controle ausente que afeta valor, DRE ou decisão do controller. |
| Médio | Controle ou descrição incompleta que prejudica rastreabilidade, reprodutibilidade ou foco da revisão humana. |
| Baixo | Precisão, clareza ou risco latente. |

---

## 1. Conclusão

1. **Os números da análise estão corretos.** Os números estão corretos. Conferem ao centavo a população (588 → 573), a ponte de R$ 31.842,73, os 16 títulos liberados (R$ 1.363,27), os retidos, a decomposição de UNATTRIBUTED e as contagens de DQ. A reexecução do código atual reproduz byte a byte os arquivos do ERP e os resumos. O núcleo do pipeline é sólido: grão, conservação, gate por título inteiro, idempotência por `id_externo`, formato do layout e validação de CPF/CNPJ.
2. **A leitura financeira está materialmente incompleta.** O extrato, que a análise apenas "perfilou", mostra fatos que mudam a recomendação:
   - as duas faturas "retidas" já foram pagas, uma delas com encargos de atraso;
   - 15 dos 16 reembolsos "importáveis" já foram pagos por PIX;
   - há um PIX em duplicidade e um reembolso vencido sem pagamento.

   **Importar os 16 títulos agora criaria duplicidade no ERP.** Esse é o achado crítico (R01).
3. **Ficaram fora da análise problemas "silenciosos"** que o `TASK.md` pede explicitamente:
   - integridade de valor e datas impossíveis;
   - Custo × Despesa no transporte do turno noturno;
   - corridas após desligamento;
   - regras de identidade resolvíveis com evidência;
   - teto de Eats avaliável pela própria política.
4. **As lacunas de DQ e de conciliação estão descritas de forma incompleta.** O relatório DQ não é determinístico entre execuções, e o critério de "alta confiança" proposto para a conciliação é inatingível com o extrato disponível.

**Parecer:** o pipeline pode seguir como base, mas não recomendo importar `ap_titulos.csv`/`ap_rateios.csv` antes das correções P0 da seção 6. A análise deve ser reemitida com as correções da seção 3.

---

## 2. O que foi verificado e confere

| Afirmação da análise | Verificação | Resultado |
|---|---|---|
| Último build com 29 modelos/seed OK e 32 testes aprovados | `run_results.json`; reexecução: PASS=61 | Confere |
| 588 ocorrências → 573 candidatos (558 únicos, 13 equivalentes, 2 conflitos) | `raw_uber_occurrences`, `int_transactions` | Confere |
| Ponte 29.318,23 + 1.363,27 + 245,48 + 882,55 + 33,20 = 31.842,73 | `int_transaction_enrichment`, `int_ap_release_gate` | Confere |
| 16 títulos = 16 rateios = R$ 1.363,27; 560 componentes com linhagem | `ap_titulos`, `ap_rateios`, `ap_rateios_linhagem` | Confere, fechamento ao centavo |
| Faturas: documentos somam R$ 29.532,81; resíduos de R$ 110,02 e R$ 104,56 | `int_ap_release_gate` | Confere, mas veja R05 e R12 |
| Mensal: 15.513,87 (jul) e 16.328,86 (ago); faturado +R$ 499,75 (+3,5%); reembolsos +R$ 213,59 (+30,6%) | `int_monthly_cost_center_payment_summary` | Confere |
| CC310, CC300 e CC210 = R$ 12.213,76 (41,7%); UNATTRIBUTED 41 / R$ 2.594,59 e sua decomposição | idem | Confere |
| Mix por serviço e por tipo de transação (ajustes −R$ 493,81; gorjetas R$ 39,00) | idem | Confere |
| 74 e-mails: 68 ligados (62 primários + 6 aliases), 2 ambíguos, 4 não encontrados | `int_uber_email_links` | Confere |
| DQ com 399 linhas (23 / 236 / 140); 364 alterações técnicas em 251 ocorrências | `dq_report`, `stg_uber_transactions` | Confere, mas veja R07 e R08 |
| Extrato com 134 linhas após o cabeçalho (86 movimentos, 48 saldos), sem IDs do ERP | leitura do CSV | Confere |
| Saídas apagadas antes do novo build | `run.py:603-613` | Confere |
| Arquivos do ERP em UTF-8 sem BOM, vírgula, `.` decimal, ISO-8601, `id_externo` ≤ 80 | `output/ap_*.csv` | Confere |

**Grão e joins.** A cadeia de grãos é consistente e preserva lineage até `occurrence_ids`:

> ocorrência (sha + aba + linha) → STAGING 1:1 → versão 1:1 → candidato (viagem + minuto UTC + tipo) → enriquecimento 1:1 → componente (só rotas de AP) → título → linha de rateio (CC × contábil × gerencial × status)

Os cadastros são pré-agregados, o que evita multiplicar valores. O teste `ap_value_conservation` garante valor e contagem.

Os joins estão corretos:
- e-mail → usuário → matrícula → CC do RH;
- código de despesa → conta contábil → crosswalk → gerencial;
- bandeira + final → cadastro de cartões;
- CNPJ do demonstrativo → fornecedor.

A única ressalva estrutural é o join com o RH por *status corrente* em vez de *vigência na data da corrida* (R10).

**Competência.** A regra está correta:
- fatura pelo mês UTC de `Transaction Timestamp`, conforme regra 1 do README;
- reembolso pelo mês local da solicitação, com bloqueio quando solicitação e desembarque caem em meses diferentes.

Ressalva: não há validação de datas impossíveis (R05).

**Release gate.** Retém o título inteiro. O teste `ap_release_gate_integrity` cobre bloqueadores, documentos, datas e fechamento. Faltam critérios de estado externo (já emitido, já pago, vencimento passado). Veja R01 e R06.

---

## 3. Achados

### R01 — Crítico — Os 16 títulos "importáveis" são retroativos e 15 já foram pagos; importá-los cria duplicidade no ERP

- **Evidência:**
  - Todos os 16 títulos liberados vencem em 15/08/2026 ou 15/09/2026, antes da data-base (`int_ap_release_gate`).
  - O extrato mostra PIX em 17/08 e 15/09 com os mesmos valores (tabela da seção 4).
  - `TASK.md` diz que o financeiro hoje digita os títulos no ERP.
  - `politica_mobilidade.md` (item 6) diz que o reembolso é pago "mediante lançamento no ERP".
  - `layout_importacao_contas_a_pagar.md` diz que o ERP não detecta duplicatas além do `id_externo`.
- **Leitura:** os títulos manuais já existem no ERP com outros identificadores. A análise (§1, tabela da ponte, "títulos e rateios importáveis") não faz essa ressalva de implantação.
- **Impacto:**
  - R$ 1.363,27 seriam registrados em duplicidade, com risco de novo pagamento;
  - o título em aberto (Andre Neto, jul, R$ 146,23) ficaria misturado a títulos já liquidados.
- **Recomendação:** ver P0.1.

### R02 — Alto — As faturas "retidas" já foram liquidadas; o custo do atraso não aparece

- **Evidência:** o extrato registra `SISPAG BOLETO UBER DO BRASIL TECN`:
  - **10/08/2026: −14.519,26.** É exatamente a fatura de julho, paga no vencimento.
  - **11/09/2026: −15.318,82.** A fatura de agosto é de 15.013,55, com vencimento em 10/09. A diferença de +305,27 equivale a multa de 2% (300,27) mais juros de 1% a.m. por um dia (5,00). Essa composição é uma hipótese a confirmar com a Uber, mas fecha ao centavo.
- **Onde a análise diverge:**
  - §1: "nenhuma liquidação está afirmada";
  - §3, prioridade 1: "liberar faturas corretamente";
  - §4: um débito Uber "pode indicar hipótese".
- **Por que importa:** a dívida é certa (o documento foi pago). O que está pendente é classificação e rateio, não o pagamento. O desenho que retém a fatura inteira, sem alerta de vencimento, já coincidiu com um pagamento em atraso.
- **Lacuna adicional:** `plano_de_contas.csv` não tem conta contábil de despesa financeira para os encargos; o gerencial tem G4.02.
- **Recomendação:** P0.2 e P1.6.

### R03 — Alto — A lacuna de conciliação está mal dimensionada; o critério proposto é inatingível e o universo está errado

- **Evidência:** uma leitura manual do extrato (sem motor de matching) já produz todas as categorias do item 7 do `TASK.md`. Veja a seção 4.
- **Onde a análise erra:**
  - A proposta (§4.3) exige "identificador independente" para alta confiança. O extrato não traz linha digitável, número de documento nem CPF. Com essa regra, 100% dos pares iriam para revisão manual.
  - A proposta (§4.2) limita o universo "apenas aos títulos gerados". Com isso, os dois boletos pagos virariam "débito sem título", sem vínculo com as faturas retidas.
- **O que a análise não aproveita:**
  - O débito `UBER *TRIP HELP.UBER.COM` de 23/07 (−33,20, origem 22/07) é a corrida paga com o VISA de débito PJ 0042 em 22/07. Essa rota já está liquidada na conta. A pergunta ao cliente é de classificação, não de "destino".
  - Nomes são truncados em 18 caracteres e há homônimos: `CAMILA ROCHA NETO` aparece duas vezes, para as matrículas 1005 e 1008; o prefixo `EDUARDO BATISTA` cobre três pessoas. Só o valor desempata.
- **Recomendação:** P2.4, com o "oráculo" de aceite da seção 6.

### R04 — Alto — A questão Custo × Despesa não foi levantada onde ela move o lucro bruto

- **TRANSP-FUNC** ("transporte de funcionário – turno noturno"):
  - 71 componentes, R$ 4.972,40, ou 17,0% do subtotal faturado conhecido;
  - 68 componentes estão em CCs de Produção (CC200–CC250), somando R$ 4.756,74;
  - estão mapeados para `5.1.03.003 Vale-Transporte`, uma **Despesa** (`de_para_codigo_despesa.csv`).
- **Onde a análise diverge:** ela trata o caso só como "crosswalk ausente" (§3, prioridade 2) e pede um crosswalk. Isso consolidaria a classificação como Despesa. Transporte de pessoal de produção tende a compor custo de produção (CPC 16), o que afeta CMV e Lucro Bruto. A decisão é da controladoria e precisa ser pedida de forma explícita.
- **ENTRE-UN** (→ `4.1.03.004 Locomoção – Fábrica`, custo, G2.03):
  - inclui CC300 Comercial (4 / R$ 247,13) e CC310 Marketing (5 / R$ 79,90);
  - inclui 8 componentes sem CC (R$ 657,31);
  - não há regra que confronte a natureza da conta com a natureza do CC.
- A análise cita apenas EVENTO. EVENTO é Despesa nas duas classificações contábeis; o risco ali é só gerencial (a sugestão G2.03 levaria o gasto ao CMV gerencial).
- **Recomendação:** P2.1.

### R05 — Alto — Faltam regras de integridade de valor e de datas; o resíduo de agosto não é necessariamente a corrida em CLP

**Valor BRL divergente do valor local em transações em BRL.** Em `uber_business_2026-08.xlsx`, aba BR, o `Transaction amount in BRL` excede o `Transaction Amount` local em R$ 7,70:

| Registro | Viagem | Valor em BRL | Valor local |
|---|---|---:|---:|
| 32 | `5591f435…` | 41,74 | 34,04 |
| 258 | `3e2917eb…` | 89,42 | 81,72 |

Nas duas linhas, gorjeta e pagamento do funcionário são zero. O pipeline aceita os dois valores como `known`.

**Datas impossíveis.** O `TASK.md` lista explicitamente "impossible dates" como regra:

| Ocorrência | Problema |
|---|---|
| `BR:62` (viagem `56c06f71…`) | Solicitação e desembarque em **03/10/2026**, num relatório gerado em 01/09. A transação é de 06/08. |
| `63fe11a8…::151` | Desembarque antes da solicitação. |
| `63fe11a8…::220` | Desembarque antes da solicitação. |

**Consequência para o resíduo de agosto.** Os R$ 104,56 só equivalem à corrida em CLP (`BR:190`, 12.528 CLP sem BRL) se as duas linhas acima estiverem certas:

| Cenário | Premissa | Resultado |
|---|---|---|
| Valores em BRL corretos | As duas linhas valem 41,74 e 89,42 | Resíduo 104,56 = corrida em CLP |
| Valores locais corretos | As duas linhas valem 34,04 e 81,72 | Resíduo 119,96 = corrida em CLP |
| Números do "Resumo" | Resumo manual da aba `Resumo` | Sobram R$ 47,30 sem explicação |

Sobre o "Resumo": em Administrativo ele fica R$ 15,40 abaixo do detalhe (= 2 × 7,70), o que é consistente com o uso dos valores locais. Em Comercial fica R$ 72,66 acima, o que é consistente com um valor em BRL atribuído à corrida em CLP.

**Efeitos colaterais:**
- a data de 03/10 gera um falso alerta de fim de semana (R11);
- se fosse cartão pessoal, geraria um reembolso de competência futura que **passaria** no gate.

**Recomendação:** P1.3.

### R06 — Alto — Não há estado de título emitido ou liquidado; o `id_externo` é estável mas o conteúdo é mutável

- **Evidência:**
  - `run.py` reconstrói tudo a cada execução;
  - a chave do reembolso é funcionário + mês local (`int_ap_title_candidates.sql:143`);
  - não existe tabela de remessas nem de retorno do ERP.
- **Risco:** um componente tardio (por exemplo, um ajuste de corrida de julho paga com cartão pessoal, exportado em setembro) altera o `valor_total` do mesmo `id_externo`. O ERP então **atualiza** um título já pago.
- A análise cita o livro de remessas como melhoria (§2, item 3). Deveria ser um bloqueador de liberação.
- **Recomendação:** P1.1.

### R07 — Médio — A lacuna do relatório DQ está descrita de forma incompleta

A análise (§2, item 1) diz que basta publicar as 364 `technical_changes` como `auto_fixable`. Isso não resolve, por três motivos.

**1. As 364 alterações são só artefatos de XLSX.** São 250 seriais de data e 114 ruídos de ponto flutuante (`stg_uber_transactions.sql:81-92`). Normalizações materiais ficam fora de qualquer log:
- e-mails com caixa ou espaços (10 valores brutos);
- códigos de despesa com caixa ou espaços diferentes (5);
- placeholders `--` convertidos em nulo;
- DD/MM × MM/DD por arquivo;
- vírgula decimal;
- relógio de 12h;
- zeros à esquerda no Employee ID;
- o **colapso das 13 duplicatas equivalentes** entre arquivos (26 ocorrências), que não aparece no DQ.

**2. O mesmo `issue_code` cai em buckets diferentes conforme o grão.** A lista fixa de `dq_report.sql:46-52` faz com que `email_link_not_found`, `email_link_ambiguous` e `email_link_missing` sejam `needs_client` na transação e `rule_based` no título. Assim, a contagem por bucket não tem semântica estável. O relatório também não tem colunas de grão, severidade, responsável e status.

**3. Regras `rule_based` pedidas pelo `TASK.md` estão ausentes:**
- datas impossíveis (R05);
- consistência de valor (R05);
- corrida após desligamento (R10);
- natureza da conta × natureza do CC (R04);
- corroboração do Employee ID (R09);
- conferência do "Resumo" manual, que é internamente inconsistente: a linha TOTAL diz 283 / R$ 16.475,69, mas as linhas somam 286 / R$ 16.588,09. Hoje a aba é ignorada em silêncio.

Nota adicional: 75 das 236 linhas `needs_client` (32%) são `eats_order_cap_not_assessed`, que é avaliável (R11).

- **Recomendação:** P1.4.

### R08 — Médio — O relatório DQ não é reprodutível entre execuções

- **Evidência:** `dq_report.csv` diferiu entre três execuções com as mesmas entradas: `output/`, uma execução de revisão anterior (`output_review_fix/`) e a minha reexecução. As duas últimas pastas foram removidas depois da comparação. Os arquivos do ERP e os resumos são idênticos. Há duas causas:
  1. O localizador vem de `unnest(occurrence_ids) … limit 1` sem ordenação (`dq_report.sql:11` e `:26`). Por isso, o conflito `3c4622e8…` aponta ora para `uber_business_2026-07.csv`, registro 86, ora para o complemento, registro 20. Num conflito, o relatório mostra só uma das duas fontes.
  2. `list_distinct(flatten(…))` sem `list_sort` (`dq_report.sql:61`).
- **Contradição documental:** `RUNNING.md` afirma que os exports ficaram determinísticos. O requisito de "Reproducibility" do `TASK.md` não é atendido para o relatório DQ.
- **Recomendação:** P1.4.

### R09 — Médio — Identidade: padrões resolvíveis não foram identificados e o Employee ID não é usado como corroboração

Dos 31 componentes faturados sem identidade (R$ 1.812,97), **25 (R$ 1.472,23)** têm resolução determinística com evidência independente (Employee ID da Uber = matrícula):

| E-mail observado | Padrão | Destino no diretório | Corroboração | Componentes / R$ |
|---|---|---|---|---:|
| `marcos.junior+uber@…` | subendereço `+tag` | U3113 `marcos.junior@`, matr. 1013 | Employee ID 1013 / 001013 | 10 / 753,50 |
| `natalia.junior+uber@…` | subendereço `+tag` | U3141, matr. 1041 | Employee ID 1041 | 4 / 223,46 |
| `sabrina.cunha@madeireiraparana…` | domínio antigo sem alias | U3154, matr. 1054 | Employee ID 1054 | 5 / 233,71 |
| `mariana.lopes@…` (ambíguo) | dois registros de diretório (U3120 ativo, U2007 suspenso) com a **mesma** matrícula 1020 | matrícula única 1020 | Employee ID 1020 | 6 / 261,56 |

Casos que são genuinamente indecidíveis:
- `comercial@`: caixa compartilhada de U3121 e U3126 (4 / R$ 180,59);
- `joao@prestesconsultoria…`: consultor externo, U9003 suspenso, com outro e-mail (2 / R$ 160,15).

Com regras aprovadas pelo cliente, UNATTRIBUTED cai de R$ 2.594,59 para R$ 1.122,36.

Há também dois e-mails ligados em que o Employee ID diverge da matrícula e nenhuma regra acusa:
- `larissa.filho@`: 1023 × 1032;
- `juliana.martins@`: 1057 × 1045.

A recomendação da análise ("corrigir por evidência") é correta, mas genérica.

- **Recomendação:** P2.2.

### R10 — Médio — Status do RH por fotografia, não por vigência; corridas após o desligamento não são sinalizadas

- **Caso:** Felipe Araujo Junior (matr. 1033) foi desligado em 15/07/2026. Tem 3 corridas faturadas **depois** do desligamento (21/07, 28/07 e 06/08, somando R$ 173,56) e 1 antes (08/07, R$ 48,29).
- **Comportamento atual:** o pipeline bloqueia as quatro como `employee_inactive` (`dim_internal_user_enrichment.sql:40`). Isso tem dois problemas:
  - bloqueia sem necessidade a corrida legítima de 08/07;
  - não sinaliza as outras três como violação do item 7 da política (remoção no dia do desligamento) nem como possível uso indevido.
- A análise não menciona o caso.
- **Recomendação:** P1.5.

### R11 — Médio — Contagens de compliance incorretas: Eats e fim de semana

**Eats.** A análise diz: "75 pedidos Eats não têm composição suficiente para validar teto por pedido". Isso está errado em dois pontos:
- são **72 pedidos** (75 transações; um pedido tem Fare + Adjustment que zera; dois têm gorjeta);
- a política define o teto sobre o "valor total da transação", logo ele é avaliável.

**4 pedidos excedem R$ 80,00**, mesmo excluindo gorjeta:

| Pedido | Total (R$) |
|---|---:|
| `2a4d419b…` | 139,38 (Fare 132,38 + Tip 7,00) |
| `628fed8d…` | 130,27 |
| `ee2e3594…` | 129,35 |
| `d0a31c72…` | 123,60 |

Esses pedidos não foram comunicados ao RH (`compliance_transaction_flags.sql:24`; `dq_enrichment_issues.sql:133-137`).

**Fim de semana.** A análise conta 8 incidências. Pelo menos 2 são artefatos:
- a data impossível de 03/10 (R05);
- um **ajuste** de −R$ 25,86 sobre uma corrida de 27/06, fora do período.

A causa é que a regra roda em todo tipo de transação (Adjustment e Tip), e não no grão da corrida.

- **Recomendação:** P2.3.

### R12 — Médio — A conciliação demonstrativo × detalhe não foi explorada, e o controle é pulado quando falta um valor

**Julho.** `cobrancas_usuario` 14.370,26 − detalhe conhecido sem Admin Fee 14.260,24 = **110,02**. Isso é exatamente 34,32 + 75,70, as versões do CSV de julho nos dois conflitos. As versões do complemento (+5,00 de gorjeta cada) passariam do valor em R$ 10,00. As `taxas_servico` (149,00) batem com a Admin Fee (149,00). O boleto pago (14.519,26) confirma o documento. Isso é evidência forte para a decisão do cliente, não uma decisão automática. A análise só diz que a diferença "não é valor a imputar".

**Papel do complemento.** O complemento contribui com:
- 3 corridas de 31/07 entre 23:02 e 23:29 UTC (R$ 136,99), depois do corte do export ad-hoc de julho (23:00 UTC);
- 3 ajustes de agosto (−R$ 201,97) que **não estão** no relatório mensal da aba Billing.

Portanto, o relatório "mensal" não é completo sozinho. Quem prova completude é a conciliação com o demonstrativo, e a análise não documenta isso.

**Controle.** `statement_total_does_not_match_periodic_detail` só é avaliado quando `detail_total` não é nulo (`int_ap_title_candidates.sql:120`). Com qualquer valor desconhecido, o pipeline não distingue "resíduo explicado pelos desconhecidos" de "linhas faltando". Também falta a conferência separada de cobranças × Fare/Tip/Adjustment e de taxas × Admin Fee.

- **Recomendação:** P1.6.

### R13 — Médio — A descoberta de arquivos ignora em silêncio o que não reconhece; uma coluna opcional ausente derruba a execução inteira

- **Arquivos não reconhecidos:** um CSV ou aba XLSX sem o cabeçalho `Trip/Eats ID` vira `ignored_non_transactional` (`run.py:184-186`, `:271-274`, `:430-432`). Um CSV que não casa assinatura de cadastro é pulado (`run.py:357-359`). Se a Uber renomear a coluna de ID, as transações somem sem erro. Para reembolsos não existe total de controle que acuse a falta.
- **Colunas opcionais:** qualquer campo canônico ausente (por exemplo, `Conditional Columns`) aborta todos os arquivos (`run.py:169-171`), inclusive os reembolsos do mês.
- A análise (§2, item 4) descreve "falhar com alerta" como se já fosse o comportamento atual.
- **Recomendação:** P1.7.

### R14 — Baixo — Imprecisões pontuais na análise

- A tabela de classificação omite `PROJ-X`, código não mapeado (2 / R$ 87,51). As seis classes somam R$ 29.318,23.
- Os "79 registros de crosswalk" são 77 transações **faturadas** (71 TRANSP-FUNC + 6 TREIN, que também não têm crosswalk) mais 2 linhas de título. Não "abrangem outras rotas".
- Os CCs são citados só por código. O maior centro de gasto Uber é **CC310 Marketing** (R$ 5.225,68), à frente de Comercial. 5 das 6 violações de Black são de CC310.

### R15 — Baixo — Proveniência dos artefatos

- `output/` foi gerado às 10:57. `dbt/models/int_ap_title_candidates.sql` (11:51) e `run.py` (11:54) foram alterados depois. A análise (12:32) não registra isso, e `run_summary.json` não traz hash do código.
- Impacto verificado como nulo: a reexecução do código atual reproduz byte a byte `ap_titulos.csv`, `ap_rateios.csv`, os candidatos, a linhagem, o resumo mensal, o `controller_summary.md` e o `run_summary.json`. A exceção é `dq_report.csv` (R08).

### R16 — Baixo — Riscos latentes

- O `controller_summary.md` tem textos fixos no código ("VISA 0042", "TRANSP-FUNC", "TREIN", "os 2 grupos") e duplica a linha do VISA (`run.py:716-726`). Isso vai envelhecer mal nos próximos meses.
- A checagem de conta postável usa só a flag. Há contas sintéticas com `aceita_lancamento=S` (`5.1.02`, `4.1.01`, `1.1.03`, gerencial `G3`). Hoje nenhuma é usada, mas nada impede uso futuro.
- A regra 5 do README ("Payments made by employees/guests") nunca é validada. Nesta amostra todos os valores são zero.
- O vencimento de reembolso cai em sábado (15/08/2026). O PIX saiu em 17/08, e a janela de conciliação precisa considerar dias úteis.
- Calendário de feriados: é imaterial para julho e agosto de 2026, que não têm feriado nacional, estadual (PR) ou de Curitiba. Passa a ser relevante em setembro (07/09 nacional, 08/09 em Curitiba).

---

## 4. Ponte financeira reproduzida: componentes → documentos → banco

| Etapa | Valor (R$) | Composição verificada |
|---|---:|---|
| Componentes com BRL conhecido | 31.842,73 | 29.318,23 faturado + 1.363,27 reembolso liberado + 245,48 reembolso retido + 882,55 AMEX + 33,20 VISA 0042 |
| Faturas (documentos) | 29.532,81 | 29.318,23 + resíduo 214,58 (jul 110,02 = 2 versões em disputa; ago 104,56 = 1 CLP sem BRL, sujeito a R05) |
| Boletos pagos | 29.838,08 | 14.519,26 (jul, exato, em 10/08) + 15.318,82 (ago, em 11/09) = faturas + 305,27 de encargos (hipótese) |
| PIX de reembolso | 1.290,81 | 1.363,27 liberado − 146,23 em aberto − 0,01 de diferença + 73,78 em duplicidade |
| Débito de cartão PJ | 33,20 | Rota VISA 0042 (corrida de 22/07) |
| **Débitos Uber/PIX no extrato** | **31.162,09** | 29.838,08 + 1.290,81 + 33,20 |

Reembolsos retidos (Mariana Lopes da Silva, R$ 245,48): nenhum pagamento localizado até 18/09. AMEX (R$ 882,55): fora do extrato, como esperado, porque tem processo próprio.

**Resultado da leitura manual do extrato para os 16 títulos liberados.** Não é conciliação implementada; serve como oráculo de aceite.

| Categoria | Títulos | Detalhe |
|---|---:|---|
| Casado exato | 12 | Jul: Andre F. Filho, Bianca, Eduardo B. da Silva, Eduardo B. Moraes, Marcos Tavares. Ago: Andre F. Filho, Andre F. Neto, Camila (1005), Camila (1008), Eduardo B. da Silva, Eduardo B. Moraes, Marcos Tavares. Total R$ 991,34. |
| Casado com diferença | 1 | Bianca, ago: título 115,30 × PIX 115,29 (−0,01) |
| Casado agregado (N:1) | 2 | Andre F. Moraes: jul 37,37 + ago 73,03 = PIX de 110,40 em 15/09 |
| Em aberto | 1 | Andre F. Neto, jul: R$ 146,23, vencido desde 15/08 |
| Pago mais de uma vez | (1) | Marcos Tavares, jul: R$ 73,78 em 17/08 **e** 18/08 |
| Débito sem título | — | `UBER *TRIP` −33,20 (VISA 0042); o PIX duplicado de 73,78 |

---

## 5. Avaliação das lacunas descritas pela análise (item 4)

**Relatório DQ.** O diagnóstico está correto quanto ao grão ("incidências ≠ transações") e quanto à separação entre informativo e bloqueante. Está **incompleto** quanto a:

1. quais correções determinísticas faltam (R07.1);
2. o determinismo (R08);
3. a inconsistência de bucket por grão (R07.2);
4. as regras `rule_based` ausentes (R05, R10, R04, R09).

Publicar só as `technical_changes` não atende "what, where, before → after" para as normalizações que importam.

**Conciliação bancária.** Os princípios estão corretos:
- não deixar o banco escolher versão Uber nem liberar fatura;
- cardinalidade explícita;
- distinguir "não encontrado até a data" de "nunca pago".

O **dimensionamento está incorreto**:
1. o critério de alta confiança é inatingível com este extrato;
2. o universo precisa incluir candidatos retidos e títulos manuais já existentes no ERP;
3. a análise conclui que o material "não prova" pagamentos, quando a leitura direta já identifica todas as categorias do item 7, incluindo duplicidade e encargos;
4. faltam o efeito do truncamento em 18 caracteres e dos homônimos, e a janela de dias úteis.

---

## 6. Correções priorizadas e critérios objetivos de aceite

### P0 — Antes de qualquer importação no ERP

| # | Correção | Critério de aceite |
|---|---|---|
| P0.1 | Definir o corte de implantação. Não importar competências já processadas manualmente. Criar o bloqueador `due_date_in_past_or_already_settled` e um parâmetro de primeira competência automatizada. | Nenhum título importado com `data_vencimento` < data da execução sem status explícito de liquidado. Confronto documentado dos 16 títulos com o ERP (títulos manuais) e com o extrato. Nenhuma coincidência de (beneficiário, competência, valor) com título manual ativo. |
| P0.2 | Registrar as duas faturas como liquidadas e tratar os encargos de 305,27 (definir conta contábil de despesa financeira; gerencial G4.02). | A ponte "fatura 15.013,55 + encargos 305,27 = boleto 15.318,82" fica documentada e aprovada pela controladoria. |
| P0.3 | Tratar as pendências financeiras reais: recuperar ou compensar R$ 73,78 (Marcos Tavares), pagar R$ 146,23 (Andre F. Neto, jul), explicar R$ 0,01 (Bianca, ago) e registrar o débito VISA 0042. | Cada item com responsável, decisão e data em um log de conciliação. Nenhum item sem status. |

### P1 — Controles do pipeline, antes do próximo ciclo mensal

| # | Correção | Critério de aceite |
|---|---|---|
| P1.1 | Livro persistente de títulos emitidos (id, hash do conteúdo, remessa, retorno do ERP, liquidação). Título emitido é imutável; componente tardio gera título de ajuste. | Teste sintético: um ajuste tardio de uma corrida de julho, em uma execução posterior, não altera o valor do `id_externo` original e cria um título de ajuste com linhagem. O teste falha se um `id_externo` emitido mudar de valor. |
| P1.2 | Publicação atômica (build em diretório temporário → testes → rename) e hash do código e da configuração no `run_summary.json`. | Uma falha induzida durante o `dbt build` preserva a saída anterior intacta. O `run_summary.json` contém `code_sha256` e `input_manifest_sha256`. |
| P1.3 | Regras de integridade: moeda BRL ⇒ valor local = valor BRL; `amount_brl` coerente com `total_fare + tips − employee_paid` (a confirmar com a Uber); `request ≤ dropoff`; datas ≤ data do relatório; transação dentro de uma janela plausível em relação à corrida. | Os 5 casos de R05 aparecem como `rule_based` bloqueantes. Há um teste sintético para cada regra. |
| P1.4 | DQ: ordenar listas e localizadores; um localizador por ocorrência em conflitos; bucket único por `issue_code`; colunas de grão, severidade, responsável e status; registrar como `auto_fixable` (antes → depois) as normalizações de e-mail, código, placeholders, formatos de data e decimal, e o colapso das 13 equivalentes. | Três execuções seguidas geram `dq_report.csv` com SHA-256 idêntico. Um teste garante um bucket por `issue_code`. Cada ocorrência normalizada tem linha `auto_fixable` com arquivo, linha, antes e depois. |
| P1.5 | Vínculo com o RH por vigência (admissão ≤ data da corrida ≤ desligamento). Corrida após desligamento vira violação de política e `needs_client`. | A corrida de 08/07 de 1033 deixa de ser bloqueada por status. As 3 posteriores a 15/07 aparecem sinalizadas. |
| P1.6 | Conciliação por fatura: resíduo sempre calculado; cobranças × detalhe sem Admin Fee e taxas × Admin Fee conferidos separadamente; status "resíduo ≤ componentes desconhecidos" ou "linhas faltando"; alerta de vencimento. | Julho mostra resíduo de 110,02 atribuído a 2 componentes em disputa e indica qual combinação de versões fecha. Agosto mostra 104,56 com 1 desconhecido e 2 linhas com valor inconsistente. Fatura com vencimento em até N dias úteis gera alerta. |
| P1.7 | Todo arquivo de entrada precisa ser classificado (transacional, cadastro ou ignorado por lista explícita, por exemplo o extrato). Coluna opcional ausente vira indisponibilidade declarada, não aborto global. | Um CSV com cabeçalho de ID renomeado faz a execução terminar com erro explícito. Uma coluna opcional ausente produz DQ e não impede os demais arquivos. |

### P2 — Decisões do cliente e reemissão da análise

| # | Correção | Critério de aceite |
|---|---|---|
| P2.1 | Pedido formal à controladoria: TRANSP-FUNC como custo de produção ou despesa; ENTRE-UN em CCs não produtivos. Criar a regra "natureza da conta × natureza do CC". | Decisão registrada com aprovador e data. A regra sinaliza os 9 componentes ENTRE-UN em CC300/CC310. Nenhuma sugestão gerencial usada sem aprovação. |
| P2.2 | Propor as regras de identidade de R09 (subendereço, domínio antigo, matrícula única entre registros duplicados), com corroboração obrigatória pelo Employee ID, e a checagem Employee ID × matrícula. | Após aprovação: 25 componentes (R$ 1.472,23) ligados com regra e evidência registradas. `comercial@` e o consultor externo continuam `needs_client`. Os 2 desvios de Employee ID aparecem no DQ. |
| P2.3 | Compliance no grão da corrida ou pedido (só Fare, com gorjeta e ajuste agregados ao pedido); teto de Eats por pedido. | 72 pedidos avaliados e 4 sinalizados acima de R$ 80. Fim de semana sem ajustes e sem datas impossíveis. |
| P2.4 | Reescrever §4 da análise. Universo = títulos liberados + candidatos retidos + títulos manuais do ERP. Confiança em camadas: **alta** = valor exato + prefixo de beneficiário normalizado (18 caracteres) + janela de vencimento em dias úteis + unicidade; **média** = um dos três relaxado (±R$ 0,05, janela maior ou N:1 do mesmo beneficiário); **baixa** = sugestão. | Aplicada a este extrato, a futura conciliação reproduz exatamente a tabela da seção 4: 12 exatos, 1 com −0,01, 1 N:1 (2 títulos), 1 em aberto, 1 duplicidade, fatura de jul exata, fatura de ago com +305,27 e o débito de 33,20 ligado à rota VISA 0042. |
| P2.5 | Reemitir `analise_senior_pipeline.md`: incorporar R01–R05, R09–R12 e R14, nomear os CCs e trocar "retidas" por "pagas fora da integração, pendentes de classificação". | Cada número novo rastreável a uma consulta de `docs/parecer_consultas.py` ou equivalente. A ponte da seção 4 fecha ao centavo. |

---

## 7. Evidências e reprodução

- Consultas deste parecer: `& '.\.venv\Scripts\python.exe' docs\parecer_consultas.py` (somente leitura; o extrato é apenas listado).
- Reexecução do pipeline atual numa pasta temporária (PASS=61), removida após a revisão. Comparação byte a byte com `output/` e com uma execução de revisão anterior: idênticos, exceto `dq_report.csv`. Para reproduzir o teste de determinismo, execute `run.py` duas vezes em pastas distintas e compare o SHA-256 de cada CSV.
- Hashes de `data/` conferidos antes e depois da reexecução: sem alteração.
