# Profiling formal — Uber for Business → Alchemy ERP

Data da análise: 25/09/2026. Escopo: os 15 arquivos de `data/`, todas as 5 abas dos 4 XLSX, e leitura integral dos quatro documentos do case. **Nenhum arquivo de origem foi alterado. Nenhum título, rateio, warehouse RAW ou pipeline final foi criado.**

Há 588 ocorrências transacionais nos três exports, 549 Trip/Eats IDs e **573 chaves candidatas**, incluindo **13 pares equivalentes e 2 pares conflitantes**. Não existe coluna de transaction ID. Os dois demonstrativos ainda não podem ser liberados: julho tem conflitos de versão e problemas de classificação; agosto tem também BRL ausente e divergência de R$ 104,56 sobre a soma conhecida.

## Como interpretar os números

- Os valores são calculados com `Decimal`, a partir dos textos originais do CSV/XML. Valores ausentes permanecem ausentes.
- Para comparar representações monetárias, este diagnóstico mostra também centavos com `ROUND_HALF_UP`. Os 180 resíduos subcentavo encontrados, em diferentes campos do XLSX, são de no máximo R$ 0,00000000000001 por célula. Cada interpretação registra original, resultado, regra e localização; **não é uma tolerância de conciliação nem uma correção do arquivo**. O contrato definitivo de parsing ainda será congelado.
- Salvo indicação de ocorrências brutas, as tabelas usam uma **população exploratória de 573 candidatos**: uma ocorrência por `(Trip/Eats ID, Transaction Timestamp UTC, Transaction Type)`. Para os dois conflitos, os números de referência mostram a versão do CSV original de julho. Isso serve apenas para apresentar cenários; **não elege uma versão vencedora**. Todas as versões estão preservadas. O intervalo monetário conhecido dessa população é R$ 31.952,75–31.962,75, mais uma transação sem BRL.
- Quantidades de problemas não são aditivas: uma transação pode ter vários problemas. Valores conhecidos não representam montantes aprovados.
- Nas referências a CSV, `registro` é o número lógico do registro; `linha` é a linha física. Os cabeçalhos multilinha tornam essas coordenadas diferentes. Em XLSX, `linha` é a linha da aba.

## FILE INVENTORY

Os quatro documentos lidos são [TASK.md](../TASK.md), [README.md](../README.md), [política](../politica_mobilidade.md) e [layout ERP](../layout_importacao_contas_a_pagar.md). Inventário completo, tamanhos e SHA-256: [inventory.json](output/inventory.json). Manifesto dos 19 arquivos: [input_manifest.json](output/input_manifest.json).

| Arquivo em data/ | Formato / encoding / separador | Aba | Registros totais¹ | Dados / colunas |
|---|---|---|---:|---|
| cartoes_corporativos.csv | UTF-8 / `,` | — | 4 | 3 / 6 |
| centros_de_custo.xlsx | XLSX | Sheet | 16 | 15 / 4 |
| demonstrativo_mensal_uber.csv | UTF-8 / `;` | — | 3 | 2 / 11 |
| departamentos.csv | UTF-8 / TAB | — | 11 | 10 / 3 |
| de_para_codigo_despesa.csv | UTF-8 / `,` | — | 9 | 8 / 5 |
| de_para_contabil_gerencial.csv | UTF-8 / `,` | — | 33 | 32 / 4 |
| extrato_itau_cc_2026-07_a_2026-09.csv | CP1252 / `;` | — | 139 | 86 movimentos + 48 saldos / 5 |
| fornecedores.xlsx | XLSX | Sheet | 44 | 43 / 9 |
| funcionarios.xlsx | XLSX | Funcionarios | 73 | 72 / 9 |
| plano_de_contas.csv | UTF-8 / `,` | — | 74 | 73 / 5 |
| plano_gerencial.csv | UTF-8 / `,` | — | 16 | 15 / 4 |
| uber_business_2026-07.csv | UTF-8 com BOM / `,` | — | 291 | 281 transações / 51 |
| uber_business_2026-08.xlsx | XLSX | BR | 293 | 286 transações / 60 |
| mesmo XLSX | XLSX | Resumo | 9 | 6 grupos + 1 total / 3 |
| uber_business_2026-08_complemento_financeiro.csv | UTF-8 / `;` | — | 31 | 21 transações / 51 |
| usuarios_internos.csv | UTF-8 / `,` | — | 77 | 76 / 8 |

¹ Inclui cabeçalho e metadados. Nos XLSX, corresponde às linhas das abas. Julho tem 297 linhas físicas; o complemento tem 37.

**Linhas não transacionais:** os exports Uber têm cinco registros iniciais de título/metadados e cabeçalho no registro/linha 6. Nos CSV, esse cabeçalho ocupa as linhas físicas 6–12. Julho: transações nos registros 7–287 / linhas 13–293; registros 288–290 vazios; rodapé 291. Complemento: registros 7–27 / linhas 13–33; 28–30 vazios; rodapé 31. XLSX BR: linhas 7–292 transacionais; rodapé na 293. Nenhuma linha transacional apresentou quantidade incorreta de campos. O XLSX não tem só uma aba.

A aba `Resumo` tem título na linha 1 e cabeçalho na 2; não é uma nova fonte de transações. No extrato, linhas 1–4 são preâmbulo e a 5 é cabeçalho. Os 48 registros de saldo não são lançamentos. O extrato foi integralmente lido e seus formatos foram avaliados; matching bancário permanece fora desta fase.

## SCHEMA COMPARISON

Os dois CSV Uber possuem exatamente os mesmos 51 nomes de colunas, mas formatos de data, hora e número diferentes. O XLSX BR tem 60 colunas. Há **42 campos comparáveis** depois de reconhecer nomes equivalentes; os componentes específicos de tarifa dos dois layouts não devem ser equiparados por posição.

| Conceito em avaliação | CSV ad-hoc | XLSX mensal |
|---|---|---|
| Relacionamento viagem/pedido | Trip/Eats ID | Trip/Eats ID |
| Data contábil Uber | Transaction Timestamp (UTC) | Transaction timestamp (UTC) |
| Solicitação UTC/local | Request Date/Time (UTC/Local) | mesmos conceitos; casing diferente |
| Chegada UTC/local | Drop-off Date/Time (UTC/Local) | mesmos conceitos; casing diferente |
| Offset da solicitação | Request Timezone Offset from UTC | Request timezone offset from UTC |
| Pessoa | First Name / Last Name / Email | First name / Surname / Email |
| Programa | Program | Programme |
| Duração | Duration (min) | Duration (mins) |
| Origem | Pickup Address | Pick-up address |
| Código / memo / pagamento / tipo | Expense Code, Expense Memo, Payment Method, Transaction Type | mesmos conceitos; casing diferente |
| Valor da empresa na moeda local | Transaction Amount (local currency) | Transaction Amount |
| Moeda local | Local Currency | Local currency code |
| Valor da empresa em BRL | Transaction Amount in BRL | Transaction amount in BRL |
| Total da tarifa BRL | Total Fare in BRL | Totals Fare in BRL |
| Gorjeta BRL | Tips [quebra de linha] in BRL | Tip in BRL (Inclusive of taxes, if any) |
| Pagamentos de pessoas | Payments made by employees/guests in BRL | mesmo campo |
| Outras cobranças | Other Charges | Other charges (local currency) |
| Documento por corrida | Invoice Number | Uber Fare Invoice# — equivalência apoiada pelos 6 overlaps |
| Contexto adicional | Conditional Columns | Conditional Columns |
| Componentes exclusivos | Fare, Booking/Service Fee, Aiport Fee, City Fee, Toll Fee, Delivery Fee, Promotions & Discounts | Net/Gross Uber Fare, Uber Promotions, Partner Fare, Gross Partner Fare, impostos por Uber/Partner |
| Documentos adicionais | Invoices | Datas, links e nomes de arquivos Uber/Partner; Partner Tax ID/Name/Address |

`Aiport Fee` está grafado dessa forma na origem. Cabeçalhos multilinha devem ser lidos por parser CSV, não por separação simples de linhas. “Tips local” e “Tips inclusive of taxes” não foram declarados equivalentes sem ressalva semântica. `Invoices` não é sinônimo automático de link Uber Fare. Partner Name não identifica funcionário nem solicitante.

Todos os schemas de apoio, posições, nomes originais e mapa completo Uber estão no [anexo de schemas](SCHEMAS.md). As frequências, ausências e tipos de armazenamento de **todas as colunas de todas as fontes** estão em [column_profiles.json](output/column_profiles.json). O snapshot preserva inclusive cabeçalhos e rodapés.

## DATA TYPES / PARSING ISSUES

| Campo / origem | Evidência | Interpretação do profiling |
|---|---|---|
| Timestamp julho | `01/07/26 16:19` | `DD/MM/YY HH:MM`, UTC |
| Request/Drop-off julho | `07/01/2026`, `3:16 PM` | `MM/DD/YYYY`, hora de 12h. O próprio mês fornece dias >12 para desambiguar |
| Complemento | `27/08/2026 14:27`, `86,84` | `DD/MM/YYYY`, hora de 24h, vírgula decimal |
| XLSX datas/horas | serial `46235.06458333333` | Datas Excel, época 1899-12-30; interpretação para segundo mais próximo, registrada. A verificação independente confirmou os tipos/date styles |
| Offset | `-3:00:00`, `-03:00`, `-04:00` | Preservar offset de cada viagem; não converter Chile com offset de Brasília |
| BRL Excel | `66.93000000000001` | Valor lexical preservado; comparação em centavos `66.93` auditada |
| Identificadores | CPF/CNPJ com pontuação; `001028`; VISA `0042` | Preservar strings/zeros; não usar `float` nem apagar zeros indiscriminadamente |
| Marcadores | `--`, vazio | Distinguir ausência, não aplicável e contexto. Não transformar em zero |
| Encoding | extrato CP1252, julho BOM | Decodificação estrita; regra registrada no inventário |
| Texto danificado | U+FFFD já presente em 10 células UTF-8 | 5 descrições no plano contábil e 5 no crosswalk. Reabrir como CP1252 não recupera os caracteres perdidos |

Há **38 valores de Transaction Amount in BRL** com resíduo subcentavo; 180 células monetárias ao todo. A soma lexical conhecida de agosto após comparação de overlaps é `14908.99000000000011`; a soma em centavos é `14908.99`. Esse resíduo não explica R$ 104,56 e não autoriza tolerância no release gate.

Problemas concretos de data/valor:

- Julho, registros **151 e 220** (linhas 157 e 226): chegada anterior à solicitação; duração informada **−26 e −59 minutos**, respectivamente. Não inverter horários nem trocar o sinal automaticamente.
- Agosto BR, linha **62**: solicitação/chegada em **03/10/2026**, mas transação em **06/08/2026** e export em 01/09. A data é válida no calendário, porém temporalmente inconsistente. Não trocar outubro por agosto.
- Agosto BR, linha **190**: CLP 12.528,00, com **cinco campos BRL vazios**, inclusive o valor da empresa. Não há equivalente dessa transação no complemento.
- Agosto BR, linhas **32 e 258**: moedas locais BRL, mas `Transaction amount in BRL` diverge do valor local e de Total Fare BRL por **R$ 7,70 em cada linha**. Valores: **41,74 × 34,04** e **89,42 × 81,72**. Sem taxas ou pagamento do usuário para explicar. Não escolher silenciosamente o menor valor.
- **272** datas de documentos individuais no XLSX apontam **02/09/2026**, posteriores ao metadado de exportação **01/09/2026 11:04:51**. São documentos de corrida, distintos do demonstrativo mensal; confirmar semântica/data de emissão, sem substituir a data de disponibilização do demonstrativo.

As relações UTC + offset = horário local fecham nas linhas observadas, inclusive na linha com data futura. Isso mostra por que consistência de timezone, isoladamente, não valida a data.

## TRANSACTION GRAIN

| Tipo | Julho bruto | Agosto BR bruto | Complemento bruto | Candidatos distintos | BRL conhecido de referência |
|---|---:|---:|---:|---:|---:|
| Fare | 268 | 275 | 18 | 546 | 32.109,56 + 1 ausente |
| Adjustment | 7 | 5 | 3 | 15 | −493,81 |
| Tip | 5 | 5 | 0 | 10 | 39,00 |
| Admin Fee | 1 | 1 | 0 | 2 | 298,00 |
| Total | 281 | 286 | 21 | 573 | 31.952,75 + 1 ausente |

Existem **24 Trip/Eats IDs com duas transações distintas legítimas** na população candidata. Exemplo: `2a4d419b-1fdf-4e53-9f58-be3adaa7102d`, julho registros 132/135: Fare **132,38** e Tip **7,00**, em timestamps diferentes. As gorjetas também podem estar incluídas em uma linha Fare; não somar a coluna Tips novamente ao Transaction Amount.

Dos 15 ajustes, 9 são negativos, somando **−523,31**, e 6 positivos somam **29,50**. Não confundir refunds com duplicatas. A taxa mensal tem ID próprio, tipo `Admin Fee`, valor 149,00 e ausência de pessoa/código. Não é rodapé, não deve ser descartada e não pode ser recriada a partir do statement.

Eats aparece como `Service = Eats`, relacionado por Trip/Eats ID; não há `order_id` separado. São 75 transações Eats, incluindo movimentos posteriores vinculados ao pedido.

## TRANSACTION KEY CANDIDATES

| Candidato | Cardinalidade observada | Avaliação |
|---|---:|---|
| Transaction ID nativo | coluna inexistente | Não disponível nos três layouts |
| Trip/Eats ID | 549 | Inadequado como chave transacional: apagaria movimentos legítimos |
| Trip/Eats ID + type | 573 | Distingue estes dados, mas não garante múltiplos ajustes do mesmo tipo no futuro |
| Trip/Eats ID + timestamp UTC + type | 573 | Candidato mais informativo disponível; os 15 overlaps mantêm os três atributos |
| Hash de todos os valores brutos do registro | 588 | Bom para integridade/linhagem; não identifica overlaps entre layouts e formatações |
| Invoice Number / Uber Fare Invoice# | Julho todo `--`; agosto 272 preenchidos, 14 `--` | Não é transaction ID universal nem statement number |
| Arquivo + linha | 588 posições | Referência da origem, não chave de negócio |

**Proposta para discussão posterior, ainda não congelada:** fingerprint de conteúdo comparável separado da identidade candidata. Valor, e-mail, CC e classificação não devem ser incorporados à chave para esconder conflitos como novos eventos. A precisão observada dos timestamps é minuto; duas transações legítimas do mesmo trip/tipo/minuto seriam uma colisão que precisa ser detectada. Os dados deste case não provam unicidade futura nem imutabilidade em outros exports.

Para reembolso, **matrícula** é a melhor candidata observada a `employee_stable_key`: há 72 matrículas únicas e não vazias, enquanto e-mail varia, usuários podem se duplicar e um CPF é inválido. Não há histórico suficiente para provar não reutilização da matrícula. Manter como proposta, sem definir chave final nesta fase.

As chaves ERP definidas pelo usuário continuam separadas: `UBER_FATURA_{statement_number}` e `UBER_REEMB_{employee_stable_key}_{YYYYMM}`. Nenhum `id_externo` foi gerado.

## OVERLAP / DUPLICATION ANALYSIS

| Par de fontes | Trips em comum | Chaves transacionais em comum | Equivalentes após parsing | Conflitantes |
|---|---:|---:|---:|---:|
| Julho × Agosto BR | 0 | 0 | 0 | 0 |
| Julho × Complemento | 11 | 9 | 7 | 2 |
| Agosto BR × Complemento | 6 | 6 | 6 | 0 |

**Duplicatas exatas de valores brutos: zero**, tanto dentro dos arquivos como entre arquivos. Isso não significa ausência de repetição de negócio. Os 13 pares equivalentes coincidem nos campos comparáveis de cada par após parsing/normalização explícitos. Nos pares de layouts diferentes, os componentes de tarifa exclusivos não foram considerados provas de igualdade.

O complemento tem 21 linhas: **13 reexports equivalentes + 2 versões conflitantes + 6 movimentos novos**. Os seis novos são três Fare de julho (**136,99**) e três Adjustment de agosto (**−201,97**). Dois ajustes se relacionam a trips já vistos em julho; o terceiro remete a uma corrida de junho, cujo Fare não está nos arquivos. Essa ausência não invalida automaticamente o crédito de agosto.

| Trip ID conflitante | Julho original | Complemento | Alteração observada |
|---|---|---|---|
| `885ae4b2-e286-4589-a332-d5d4fd17b028` | registro 49 / linha 55: 75,70 | registro 25 / linha 31: 80,70 | Tips BRL 0 → 5; mesmo timestamp `06/07 13:36 UTC`, mesmo tipo Fare |
| `3c4622e8-873f-49ee-b878-dcf46bf4fe23` | registro 86 / linha 92: 34,32 | registro 20 / linha 26: 39,32 | Tips BRL 0 → 5; mesmo timestamp `09/07 17:13 UTC`, mesmo tipo Fare |

Não há evidência suficiente para “latest wins”, “first wins”, somar ambas ou inventar uma Tip adicional. **NEEDS_CLIENT:** confirmar versões/correção no export e efeito na fatura. A coincidência com um total não é prova de precedência. Evidências completas: [duplicate_groups.json](output/duplicate_groups.json) e [conflicting_candidates.json](output/conflicting_candidates.json).

## USER LINKING ANALYSIS

O fluxo explorado é e-mail → directory → matrícula → funcionários → CC oficial. Não há join por nome. Os funcionários têm **10 pares de homônimos**, reforçando essa restrição. O campo Employee ID do Uber não é fonte de linking.

Os 83 valores brutos de Email tornam-se 75 após trim/casing, **incluindo o marcador `--`**; são 74 endereços não-placeholder. Resultado da avaliação direta do campo Email, antes de interpretar Uber Central:

| Status / método | E-mails ou marcadores distintos | Transações | BRL conhecido |
|---|---:|---:|---:|
| linked / primary | 62 | 483 | 25.798,91 + 1 ausente |
| linked / alias | 6 | 53 | 3.790,79 |
| ambiguous / primary | 1 | 6 | 261,56 |
| ambiguous / alias | 1 | 4 | 180,59 |
| not_found / none | 5 | 27 | 1.920,90 |

Os 6 aliases efetivamente necessários são `aline.silva`, `andre.moraes`, `andre.souza`, `marcos.souza`, `mariana.junior` e `tatiane.neto`, todos no domínio histórico `madeireiraparana.com.br`. Detalhes por endereço: [user_linking.json](output/user_linking.json).

| Caso | Evidência | Consequência |
|---|---|---|
| Alias compartilhado | `comercial@madeiraparana.com.br` → U3121/1021 e U3126/1026, ambos ativos; 4 transações, 180,59 | Ambiguidade real de pessoa/CC; NEEDS_CLIENT |
| Usuário duplicado, pessoa única | `mariana.lopes@madeiraparana.com.br` → U3120 ativo e U2007 suspenso, ambos matrícula 1020; 6 transações, 261,56 | Identidade do usuário ambígua, empregado determinável. Não escolher ativo silenciosamente; não tratar como duas pessoas |
| Plus addressing não cadastrado | `marcos.junior+uber` (10 / 753,50) e `natalia.junior+uber` (4 / 223,46) | Não remover `+uber` como regra inventada; pedir inclusão/confirmação de aliases |
| Domínio antigo sem alias | `sabrina.cunha@madeireiraparana.com.br`: 5 / 233,71 | Não trocar domínio em massa |
| Externo sem correspondência | `joao@prestesconsultoria.com.br`: 2 / 160,15 | Directory possui outro endereço de consultor, sem matrícula; nome parecido não autoriza join |
| Uber Central | 4 / 252,08, Email `--`; solicitante em Conditional Columns | Todos explicitamente solicitados por `helena.paranhos@madeiraparana.com.br` → U3171 → 1201 → CC101. Resolvido pelos dados e pela política |
| Admin Fee | 2 / 298,00; Email `--` | Identidade de empregado não aplicável; falta regra de rateio da taxa |

Depois de interpretar solicitantes, **540 transações têm usuário unívoco**, 10 mantêm ambiguidade de usuário, 21 seguem sem match e 2 taxas são não aplicáveis ao linking individual. A matrícula de Mariana continua determinável sem eleger um usuário. Os convidados permanecem sem Expense Code, portanto a identidade resolvida não libera o rateio.

Qualidade dos cadastros:

- 76 usuários com ID único; 3 contas sem matrícula, sem match com e-mails efetivos do Uber. Todos os usuários com matrícula apontam para funcionário existente.
- 6 registros do directory discordam do CC do RH, incluindo o usuário histórico duplicado. Matrículas: **1004, 1016, 1028, 1043, 1050, 1020**. O CC oficial continua sendo o do RH.
- 15 CCs: 13 ativos, **CC250 e CC900 inativos**. RH usa **CC777 inexistente** na matrícula 1006 (4 transações / 209,70) e **CC250 inativo** na 1040 (4 / 273,92).
- 10 departamentos, todos os departamentos dos funcionários existem. D10 referencia **CC555 inexistente**, mas nenhum funcionário usa D10. Há 56 diferenças entre CC do funcionário e referência departamental; isso é esperado por hierarquias distintas, não autorização para realocar.
- 12 divergências entre Employee ID Uber e matrícula do linking: **8 têm apenas zeros à esquerda**, e **4 apontam para outra pessoa** (duas ocorrências de 1045 versus 1057 e duas de 1032 versus 1023). Manter evidência; usar linking oficial por e-mail.
- 72 CPFs distintos; **1 inválido**, matrícula **1053**, linha 54 do RH. Afeta 6 transações pessoais / **245,48**, distribuídas em julho **142,68** e agosto **102,80**. Não alterar dígitos verificadores. A invalidez do CPF do funcionário não invalida automaticamente o CNPJ beneficiário da fatura Uber.
- RH possui datas de admissão e desligamento. Matrículas 1033 e 1062 estão desligadas. Há 3 viagens posteriores ao desligamento de 1033 (21/07, 28/07 e 06/08), total **173,56**; nenhuma observada para 1062. Status atual não deve invalidar retroativamente todas as viagens anteriores.

## ACCOUNTING MAPPING ANALYSIS

Os 8 Expense Codes do cadastro têm chave única. Plano contábil: 73 códigos únicos. Gerencial: 15 únicos. Crosswalk: 32 origens únicas; todas as referências nele existentes apontam para contas que existem e aceitam lançamento.

| Expense Code observado | N | BRL conhecido | Resultado |
|---|---:|---:|---|
| VIS-CLI | 230 | 11.364,82 | 5.1.02.004 → G3.01, válido |
| vis-cli / Vis-Cli | 3 | 168,39 | Candidatos determinísticos de casing para VIS-CLI; registrados, sem alteração da origem |
| AERO | 30 | 2.062,81 | 5.1.02.004 → G3.01, válido |
| ADM | 70 | 3.123,16 | 5.1.01.001 → G3.02, válido |
| ENTRE-UN | 61 | 4.425,72 | 4.1.03.004 → G2.03, válido, Custo |
| HE-REF | 75 | 4.148,66 | 5.1.03.004 → G3.03, válido |
| TRANSP-FUNC | 71 | 4.972,40 | 5.1.03.003 existe e é lançável, mas **não está no crosswalk oficial** |
| TREIN | 6 | 262,52 | 5.1.03 é sintética/não lançável e também não consta no crosswalk |
| EVENTO | 11 | 333,19 + 1 ausente | Mapping sugere G2.03; oficial para 5.1.02.003 é **G3.01** |
| PROJ-X | 2 | 87,51 | Código desconhecido |
| `--` | 14 | 1.003,57 | 12 corridas sem código (705,57) + 2 taxas (298,00) |

**EVENTO é uma inconsistência explícita com efeito na DRE:** G2.03 é Custo/CMV, G3.01 é Despesa Comercial. A autoridade do crosswalk está **DEFINED**; não precisamos perguntar qual fonte usar. Registrar o conflito e propor o alinhamento ao oficial com trilha before/after. Não inventar uma nova conta contábil pela descrição “evento”.

Para **TRANSP-FUNC**, a sugestão G3.03 não substitui um crosswalk ausente: requer confirmação/correção oficial. Para **TREIN**, precisa ser indicada uma conta analítica apropriada. Para Admin Fee, faltam **conta contábil, crosswalk e critério de CC/rateio**; não distribuir proporcionalmente sem regra do cliente.

Outra inconsistência cadastral: **1.1.03, 4.1.01 e 5.1.02** são pais com descendentes, mas têm `aceita_lancamento = S`; o mesmo ocorre com **G3**. TASK descreve S como analítica. Nenhum mapping Uber aponta diretamente para esses quatro pais; registrar para o cliente, sem corrigir os planos nem bloquear contas filhas válidas por associação.

Há outras contas lançáveis sem crosswalk fora do escopo de despesas Uber (por exemplo contas patrimoniais). Isso não significa que todas precisem de mapping nesta integração. A lacuna efetivamente usada é 5.1.03.003, além da origem sintética de TREIN.

## PAYMENT METHOD ANALYSIS

| Classe observada | Transações candidatas | BRL conhecido | Tratamento definido ou pendência |
|---|---:|---:|---|
| Periodic Billing | 521 | 29.428,25 + 1 ausente | Competência por timestamp UTC; 2 demonstrativos |
| Cartões pessoais | 39 | 1.608,75 | 10 empregados, 18 combinações empregado/mês; reembolso via PIX dia 15 seguinte |
| AMERICAN_EXPRESS - 3008 | 12 | 882,55 | Corporativo; processo próprio, fora dos dois fluxos desta integração |
| VISA - 0042 | 1 | 33,20 | **DEBITO_CONTA_PJ**. Não é pessoal nem Periodic Billing. Destino financeiro não especificado nos documentos |

Os 12 rótulos de cartão observados são AMERICAN_EXPRESS 3008, VISA 0042, MASTERCARD **5473, 8129, 7556, 4166, 2854**, ELO **6758, 5328, 2134, 5252, 7391**. Todos mantêm quatro dígitos. Não há bandeira desconhecida ou formato não reconhecido nesta amostra.

Cadastro corporativo: três pares brand+last4, **sem colisão**. MASTERCARD 5510 consta como cancelado em 03/2026, mas não aparece no Uber. Não há colisão observada de cartão pessoal entre empregados. AMEX é usado por três pessoas; isso não é uma colisão cadastral, e o titular não é usado para linking.

**NEEDS_CLIENT:** como representar contabilmente o débito VISA 0042 já originado na conta PJ, sem duplicar pagamento? Sua natureza corporativa é resolvida pelo cadastro; a operação de destino permanece aberta. O lançamento bancário não foi conciliado nesta fase.

Todos os valores preenchidos de `Payments made by employees/guests` são zero. Um BRL está vazio na corrida chilena; o equivalente local é zero. O conjunto não testa a regra para contribuições não nulas; futuramente testar sem somá-las ao valor da empresa e sem subtraí-las novamente de um Transaction Amount já líquido.

As 18 combinações de reembolso são apenas **candidatos para dimensionamento**, não títulos aprovados. A matrícula 1053 tem dois candidatos impedidos pelo CPF, total 245,48. O layout ERP não possui coluna para PIX/boleto e não define a data de emissão de reembolso; são lacunas de integração a confirmar, sem inventar coluna ou data.

## STATEMENT RECONCILIATION

A conciliação usa exclusivamente Periodic Billing e **mês de Transaction Timestamp UTC**, incluindo créditos e Admin Fee. Os números a seguir são cenários de profiling.

| Competência | Statement | Cobranças usuário | Taxa | Invoice total | Detalhe conhecido de referência | Invoice − detalhe |
|---|---|---:|---:|---:|---:|---:|
| 2026-07 | UBR-2026-07-004417 | 14.370,26 | 149,00 | **14.519,26** | **14.519,26** | **0,00 no cenário original** |
| 2026-08 | UBR-2026-08-004981 | 14.864,55 | 149,00 | **15.013,55** | **14.908,99 + 1 BRL ausente** | **104,56 sobre valores conhecidos** |

Os dois cabeçalhos fecham exatamente usuário + taxa = total. CNPJ emitente **28696184000195** é válido e encontra exatamente o fornecedor da linha 43. A linha 44 de fornecedores tem nome semelhante, mas CNPJ `28.696.184/0001-25` inválido: não fazer match pelo nome.

**Julho e o corte antecipado**

O arquivo original contribui **257 transações Periodic / 14.382,27**. Faltam **136,99** perante 14.519,26. O complemento contém três transações novas dentro de julho UTC, todas depois do horário de exportação original `31/07 23:00:12`:

| Complemento: registro / linha | Trip/Eats ID | Timestamp UTC em 31/07 | BRL |
|---|---|---|---:|
| 26 / 32 | 28fe2e3b-2e2d-483c-a937-c598b9d35fb0 | 23:02 | 64,72 |
| 12 / 18 | 836bad43-0233-46c6-b247-b4a0b7b425de | 23:16 | 44,76 |
| 9 / 15 | ca4642c2-5e41-4851-beef-2a022f276841 | 23:29 | 27,51 |
| Total | | | **136,99** |

Essas três linhas fornecem evidência direta do corte incompleto e estão nos dados: nenhuma transação foi inventada. O CSV de julho tem último timestamp 21:28 UTC, embora o export tenha ocorrido às 23:00. O complemento acrescenta os movimentos tardios legítimos.

**Mas existem dois conflitos independentes.** Se mantidas as versões do arquivo original, chega-se a 14.519,26; com uma versão alterada, 14.524,26; com ambas as versões alteradas do complemento, **14.529,26**, diferença **−10,00**. Excluindo integralmente as duas chaves disputadas, a soma não conflitante é **14.409,24**. Não usar a fatura para escolher ganhadores e não liberar julho só porque um cenário fecha.

**Agosto**

O XLSX contribui **258 Periodic / 15.110,96 conhecidos**, já incluindo a taxa. Os três ajustes novos do complemento, pertencentes a agosto UTC, são **−83,21 −25,86 −92,90 = −201,97**. Após evitar os seis overlaps de agosto: **15.110,96 − 201,97 = 14.908,99**. Falta suporte para **104,56** perante o demonstrativo.

As linhas BR 7/8 somam **133,70**, com ride local em 31/07 à noite e timestamp UTC em 01/08: pertencem à fatura de agosto, não à de julho. Os três créditos adicionais têm ride date anterior ao mês; isso não altera a competência Periodic definida.

Há **um BRL ausente** e **duas divergências de +7,70** nos valores BRL/local. Não se pode atribuir automaticamente 104,56 à corrida chilena. Se fossem adotados os valores locais nas duas divergências, a diferença aritmética seria **119,96**, mas esse também é apenas um cenário, não uma cotação nem o valor da corrida. Não estimar câmbio pela outra viagem, pelo saldo faltante ou pelo resumo manual.

**Aba Resumo inconsistente:** os seis grupos somam **286 / 16.588,09**, enquanto TOTAL declara **283 / 16.475,69**. O detalhe BR tem **286 / 16.530,83 conhecidos + 1 ausente**. São três referências distintas; o resumo manual não fecha consigo mesmo e não deve completar BRL ausente nem ser fonte de CC.

**Conclusão de liberação:** ambos os payables de fatura, somando **29.532,81**, permanecem não liberáveis com os dados atuais. Isso é avaliação de evidência, não uma implementação de release gate. Corrigir apenas a conciliação não basta: faltam dimensões válidas para rateios completos.

## POLICY-RELATED FIELDS AVAILABLE

| Regra | Campos disponíveis / limites | Resultado exploratório |
|---|---|---|
| UberX / Comfort / Black | Service + CC oficial via linking | 6 Black fora de CC101 |
| Fim de semana | Request Date Local + Program | 7 transações com programa não permitido; 3 linhas com problemas temporais ficam em revisão |
| Feriado | Datas, cidade, país, endereços; não há calendário aplicável | **Pendente**, não avaliado |
| Eats e programa | Service=Eats, Program, Trip/Eats ID | 75 movimentos Eats; nenhum com programa diferente de Refeicao Hora Extra |
| Limite R$80 | Transaction Amount BRL, tipo e relacionamento pedido | 4 Fare acima de 80: 132,38; 129,35; 130,27; 123,60 |
| Expense Code válido | Campo e mapping | 14 corridas sem código/código desconhecido; 3 variações de caixa tratadas como candidatos de normalização, não como violação |
| Convidados | Conditional Columns: “Solicitado por” | 4 solicitantes determinados; manter pessoa convidada separada do responsável |
| Cartão pessoal / falha corporativa | Payment Method, Expense Memo | 39 **POLICY_REVIEW_REQUIRED**; não há evidência da falha corporativa |
| Desligamento | Data Desligamento do RH + ride date local | 3 viagens após desligamento; reportar RH/gestor |
| Destinatário gestor | Responsável em centros_de_custo | Nome disponível; não há e-mail do gestor nem trilha de aprovação |

O campo de memo não comprova uma falha de meio corporativo. A avaliação de Eats acima de 80 lista as transações que, por si sós, ultrapassam o teto; não congela como somar tips/adjustments por pedido para decidir outros casos. Esse detalhamento do limite por pedido permanece aberto. Nenhum flag de compliance diminui dívida ou bloqueia automaticamente payable. A evidência está em [policy_diagnostics.json](output/policy_diagnostics.json), com códigos, status e linhagem; sua chave transacional continua candidata.

As 3 linhas com data/duração inconsistente geram revisão da avaliação temporal; não afirmar violação de fim de semana a partir da data futura de outubro. Há viagens em São Paulo e Santiago, além de Curitiba/Araucária, reforçando a pendência do calendário aplicável.

## DATA QUALITY FINDINGS

**AUTO_FIXABLE é uma classificação de possibilidade, não afirmação de que a origem foi corrigida.** O log registra interpretações somente para o diagnóstico. [issues.json](output/issues.json) contém ocorrências; [diagnostic_interpretations.json](output/diagnostic_interpretations.json) contém before/after/rule. A tabela abaixo organiza também decisões que não são erros técnicos.

| Achado | Domínio | Classe DQ | Alcance / ação |
|---|---|---|---|
| BOM, delimitadores, cabeçalhos/rodapés, serial Excel, trim/casing | DQ | AUTO_FIXABLE | Parsing com contrato e log; sem alterar origem |
| Resíduos monetários Excel | DQ | AUTO_FIXABLE | 180 células, incluindo 38 valores principais; regra de centavos explícita, não tolerância |
| Variações `vis-cli`, `Vis-Cli` | DQ | AUTO_FIXABLE | 3 transações / 168,39; mapeamento único candidato |
| Overlaps equivalentes | DQ | AUTO_FIXABLE | 13 pares / 26 ocorrências, preservar ambas as origens |
| Mesma chave candidata com montantes diferentes | DQ + financeiro | RULE_BASED na detecção; NEEDS_CLIENT na resolução | 2 pares / 4 ocorrências; sem precedência automática |
| Datas/durações inconsistentes | DQ | RULE_BASED | 2 durações negativas e 1 solicitação futura; confirmar valores corretos |
| BRL local × BRL convertido divergente | Financeiro | RULE_BASED | 2 linhas / +15,40 de diferença; requer fonte corrigida |
| BRL ausente | Financeiro | RULE_BASED | 1 corrida CLP; NEEDS_CLIENT para recuperar cobrança oficial |
| E-mail sem match ou compartilhado | DQ | RULE_BASED na detecção; NEEDS_CLIENT na resolução | Sem fuzzy match, substituição de domínio ou remoção de `+` |
| Employee ID Uber divergente | DQ | AUTO_FIXABLE para 8 representações com zeros; RULE_BASED para 4 divergências reais | Não é chave do linking; preservar original |
| CC inexistente/inativo | DQ / dimensão financeira | RULE_BASED | 8 transações, 483,62; bloqueia rateio necessário |
| CC directory diferente do RH | DQ | RULE_BASED | 6 cadastros; autoridade do RH já definida |
| CPF inválido | DQ / beneficiário financeiro | RULE_BASED | Matrícula 1053; 2 reembolsos candidatos / 245,48 |
| CNPJ inválido | DQ | RULE_BASED | Fornecedores linhas 40, 41, 44; Uber correto na 43 |
| Fornecedor duplicado com outros atributos conflitantes | DQ | NEEDS_CLIENT | 3 CNPJs em pares: linhas 2/35, 3/36 e 5/37; não usados como beneficiário Uber |
| D10 → CC555 inexistente | DQ | RULE_BASED | Cadastro não usado pelos empregados deste conjunto |
| TREIN sintético / TRANSP-FUNC sem crosswalk | Financeiro | RULE_BASED | 6 + 71 transações; requer mapping oficial, sem fallback |
| EVENTO sugerido × oficial | Financeiro | RULE_BASED | 11 movimentos; autoridade oficial definida, divergência auditável Custo/Despesa |
| Código ausente/desconhecido | Financeiro | RULE_BASED | 12 corridas sem código + 2 PROJ-X; caso a caso; sem conta fallback |
| Admin Fee sem classificação/CC | Financeiro | NEEDS_CLIENT | 2 taxas / 298,00; regra de rateio inexistente |
| Pais marcados como lançáveis | Financeiro / cadastro | NEEDS_CLIENT | 3 contas contábeis e G3; contradição com descrição “analítica”; não usados diretamente |
| U+FFFD já gravado na origem | DQ | NEEDS_CLIENT | 10 descrições; solicitar cadastro íntegro, não adivinhar acentos |
| Data de invoice individual posterior ao export | DQ | NEEDS_CLIENT | 272 linhas; esclarecer semântica, não confundir com statement |
| Resumo manual não soma | DQ | RULE_BASED | TOTAL diverge de seus próprios grupos e do detalhe |
| Divergência/insuficiência da conciliação | Financeiro | RULE_BASED | Ambas as faturas não liberáveis; sem plug e sem título parcial |
| Débito PJ sem rota de saída definida | Financeiro | NEEDS_CLIENT | VISA 0042 / 33,20; não reembolsar como pessoal |
| Uso fora da política / evidência insuficiente | Compliance | RULE_BASED / NEEDS_CLIENT conforme evidência | Flags separados; não reduzir dívida nem bloquear automaticamente |

O CNPJ de 13 dígitos da linha 40 está armazenado como **texto**, portanto não há prova de perda de zero causada por célula numérica. Não completar comprimento nem corrigir dígitos verificadores automaticamente. Os cinco Partner Tax IDs distintos do Uber foram validados por algoritmo e passaram; não são beneficiários do payable Uber.

“Nenhuma linha malformada” significa apenas que todas as linhas transacionais puderam ser estruturadas e os campos esperados foram lidos; não significa qualidade financeira aprovada.

## AMBIGUITIES FOUND

Os estados abaixo distinguem fatos definidos, itens investigados nos dados e decisões ainda dependentes do cliente. Não foram enviados novos questionamentos externos nesta fase.

### RESOLVE_FROM_DATA — investigação solicitada

| Pergunta | Resultado encontrado / estado após profiling |
|---|---|
| 1. Transaction ID estável? | Não existe coluna. Trip/timestamp/type se mantém nos 15 overlaps; chave definitiva ainda aberta |
| 2. Estrutura CSV/XLSX? | 2 schemas: 51/60 colunas; 3 contratos de parsing; segunda aba manual identificada |
| 3. Fare/Adjustment/Tip/Admin Fee? | Todos explícitos; grain transacional confirmado |
| 4. Overlaps? | Complemento sobrepõe julho e agosto; 9 e 6 chaves |
| 5. Duplicatas exatas? | Zero brutas; 13 pares equivalentes após parsing auditado |
| 6. Conflicting duplicates? | 2 pares com diferença de 5,00 cada; resolução migra a NEEDS_CLIENT |
| 7. Alias-only? | 6 endereços / 53 transações |
| 8. Ambiguous/not_found? | 2 endereços ambíguos; 4 endereços reais não encontrados; marcador ausente separado |
| 9. Requester Central separado? | Disponível em Conditional Columns nas 4 corridas; responsável Helena/1201/CC101 |
| 10. Eats/order? | Service=Eats, relacionamento Trip/Eats ID; sem order ID próprio |
| 11. Service fee no detalhe? | Sim, Admin Fee de 149,00 por mês; falta classificação, não falta transação |
| 12. Desligamento no master? | Sim; dois desligados, três viagens posteriores para um deles |
| 13. Colisões brand+last4? | Nenhuma no cadastro; nenhum par pessoal compartilhado na amostra |
| 14. Ride date local? | Sim, campos explícitos; formatos diferentes; uma data futura inconsistente |
| 15. Internacional? | Duas corridas Santiago/CLP, offset −04:00; uma sem BRL |
| 16. Statements fecham? | Julho fecha apenas no cenário com versões originais; agosto não fecha e está incompleto |
| 17. Julho incompleto? | Sim: 136,99 após o cutoff, recuperáveis nas três linhas reais do complemento |

### DEFINED — não reabrir regras já estabelecidas

CC do RH; linking por e-mail/aliases cadastrados; responsabilidade do solicitante Central; competência Periodic por timestamp UTC; competência pessoal por ride date local; prioridade do crosswalk oficial; AMEX fora desta integração; demais cartões não cadastrados são pessoais; compliance não altera automaticamente payable; liberação por payable completo; nenhuma tolerância/plug. O profiling não mudou nenhuma dessas regras.

### NEEDS_CLIENT — pendências e inconsistências novas ou confirmadas

| ID | Pergunta concreta / decisão faltante | Efeito |
|---|---|---|
| NC01 | Qual versão das duas corridas conflitantes representa a cobrança? Há export corrigido e documentação da alteração de Tips? | Julho; não usar igualdade agregada para decidir |
| NC02 | Qual conta/crosswalk e qual critério de CC/rateio se aplicam à Admin Fee? | As duas faturas |
| NC03 | Confirmar/corrigir crosswalk oficial de 5.1.03.003 e conta analítica de TREIN | Classificação das duas faturas |
| NC04 | Qual classificação autorizada para corridas sem código e PROJ-X? | Já previsto como caso a caso; sem fallback |
| NC05 | Fornecer export/cobrança BRL da corrida chilena e esclarecer as duas divergências BRL/local de 7,70 | Agosto; não inferir FX ou valor por diferença |
| NC06 | Confirmar responsáveis dos e-mails não cadastrados e do alias comercial compartilhado | Identidade/CC; cadastrar aliases oficiais |
| NC07 | Qual regra deve escolher o usuário do directory quando dois IDs representam a mesma matrícula 1020? | Usuário interno ambíguo; pessoa/CC já determináveis pelos dados |
| NC08 | Corrigir CPF da matrícula 1053, CC777 e CC250 usados no RH | Beneficiário e dimensões inválidas |
| NC09 | Qual destino operacional do VISA 0042, débito da conta PJ? | Não é reembolso pessoal nem fatura Periodic; evitar novo pagamento |
| NC10 | Corrigir/explicar datas impossíveis, durações negativas e datas de invoice individuais posteriores ao export | DQ e avaliação temporal; não alterar automaticamente competência definida |
| NC11 | Qual calendário rege a corrida, incluindo fora do PR/exterior? | Já enviado; feriados pendentes, parametrizáveis |
| NC12 | Existe evidência de falha corporativa para uso de cartão pessoal? | Já enviado; POLICY_REVIEW_REQUIRED, reembolso financeiro definido |
| NC13 | Para o limite por pedido Eats, como tratar múltiplas transações Tip/Adjustment relacionadas ao mesmo pedido? | Preservar grain; não congelar regra de soma líquida/bruta sem definição |
| NC14 | Como informar PIX/boleto no ERP sem campo no layout? Qual data de emissão do reembolso e como mapear disponibilização do demonstrativo para emissão do título? | Contrato de importação/configuração; não criar coluna/data arbitrária |
| NC15 | Confirmar flags de lançamento dos pais, restaurar textos U+FFFD e resolver duplicidades de fornecedores não Uber | Higiene cadastral; não bloquear registros válidos não afetados |

A estabilidade histórica/não reutilização da matrícula e a capacidade de obter ID nativo/maior precisão de transação permanecem **RESOLVE_FROM_DATA para o desenho futuro**; o snapshot atual não as comprova. Não impedem a entrega deste relatório nem autorizam congelar contratos sem a revisão combinada.

## Reprodução, evidências e limite desta entrega

[README do profiling](README.md) contém os comandos. O script principal usa Python standard library e `Decimal`; lê o texto numérico do XML para não tornar `float` fonte de verdade. Pandas/openpyxl são usados em uma **verificação independente**, sem substituir os valores originais. Esta é uma análise exploratória, não a implementação de joins/transformações de produção: a divisão Python → DuckDB/dbt permanece planejada e não houve decisão de abandonar dbt.

[Verificação executada](output/verification.json): **PASS**, 19 entradas inalteradas, 15 arquivos de evidência idênticos em reexecução; leitura CSV independente e confirmação das abas/datas Excel. [Snapshot integral](output/source_snapshot.json), [evidência transacional](output/transaction_evidence.json) e [métricas](output/metrics.json) permitem reproduzir cada número.

`source_file`, `source_sheet`, registro/linha física, layout, sistema, hash e versões candidatas estão preservados. `profile_run_at` identifica a execução do diagnóstico; não foi chamado de `ingestion_ts`, pois ainda não existe camada RAW. O vínculo futuro transaction → rateio/payable, a chave definitiva e a sequência determinística serão implementados depois da revisão. O diretório recebido não era um repositório Git; não houve commit nem implantação.

**Ponto de parada acordado:** profiling entregue. Canonical schema, transaction key, dedup strategy, modelos SQL/dbt, saídas ERP e release gate ainda não foram congelados ou implementados.
