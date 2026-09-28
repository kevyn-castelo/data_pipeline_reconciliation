# Reavaliação dos entregáveis após o commit

> **Registro histórico da revisão anterior às correções.** A conciliação e o versionamento de `output/` foram corrigidos depois deste parecer. Para os números e status vigentes, consultar `docs/17_validacao_correcoes.md`, `reconciliation/README.md` e `output/README.md`. As colunas `diferenca` e `held_unpayable` descritas abaixo pertencem ao esquema antigo.

Data da revisão: 28/09/2026. Commit local: `0bf9a1b` (main, alinhado à referência local origin/main). O remoto não foi atualizado por fetch nesta revisão. Há alterações locais não commitadas em `.gitignore`, `RUNNING.md`, `run.py` e `tests_synthetic.py`. Nenhum desses arquivos foi alterado por esta revisão.

## Reembolsos aparentemente zerados

**Nenhum dos 18 reembolsos em `reconciliation/bank_reconciliation.csv` tem `valor_titulo` igual a zero.** Os títulos somam R$ 1.608,75. Os zeros estão na coluna `diferenca`: 14 reembolsos têm diferença 0,00, um tem diferença −0,01 e três têm o campo vazio.

| Situação | Títulos | Valor dos títulos | Débitos bancários principais associados | Interpretação |
|---|---:|---:|---:|---|
| Correspondência exata | 12 | R$ 991,34 | R$ 991,34 em 12 PIX | Diferença zero é o resultado esperado |
| Um PIX para dois títulos de André Moraes | 2 | R$ 110,40 | R$ 110,40 em um PIX | Julho R$ 37,37 + agosto R$ 73,03; não são dois pagamentos de R$ 110,40 |
| Bianca, agosto | 1 | R$ 115,30 | R$ 115,29 em um PIX | Diferença −R$ 0,01 |
| André Neto, julho | 1 | R$ 146,23 | Nenhum movimento associado | Em aberto no recorte do extrato; `diferenca` vazia |
| Mariana, julho e agosto | 2 | R$ 245,48 | Busca excluída pelo motor devido ao bloqueio cadastral | `held_unpayable` por CPF; campo vazio não significa valor zero nem prova ausência de pagamento |
| **Total** | **18** | **R$ 1.608,75** | **R$ 1.217,03 em 14 PIX principais** | Duplicidade tratada abaixo |

Marcos Tavares, julho, é um dos 12 matches exatos: título de R$ 73,78, um PIX principal de R$ 73,78 e outro PIX de R$ 73,78 marcado como duplicado. O campo `diferenca=0.00` considera somente o pagamento principal. `pago_mais_de_uma_vez=True` e `bank_ids_duplicados` mostram o excedente; os débitos totais ligados a esse título somam **R$ 147,56**. Essa informação precisa ficar mais evidente na apresentação final.

Ponte dos 16 títulos históricos elegíveis à busca: **R$ 1.363,27 − R$ 146,23 − R$ 0,01 + R$ 73,78 = R$ 1.290,81** em débitos PIX relacionados. Os R$ 245,48 retidos por CPF completam os R$ 1.608,75 dos 18 candidatos. Existem 15 títulos com evidência de pagamento, cobertos por 14 PIX principais, mais um PIX duplicado.

O campo `num_documento` vazio nos reembolsos também é permitido pelo layout do ERP; não representa valor monetário ausente.

## Problemas da conciliação confirmados nesta revisão

1. **Apresentação dos valores.** A saída por título não contém valor do pagamento principal, valor duplicado ou total bancário associado. `diferenca` é genérico e permite confundir zero de divergência com zero de reembolso. Recomenda-se explicitar esses valores e diferenciar campo não avaliado de zero monetário.
2. **O CSV de pares não é aditivo por movimento.** `bank_match_pairs.csv` repete o movimento de R$ 110,40 para os dois títulos N:1. Somar `bank_value` em todas as linhas dá R$ 31.165,51 em débitos; deduplicar por `bank_id` dá R$ 31.055,11. A diferença de R$ 110,40 é repetição do mesmo movimento. O primeiro total não é o total bancário conciliado. Recomenda-se separar valor do movimento de valor atribuído ao título e documentar o grão.
3. **Homônimos no N:1.** Reproduzido em memória: um PIX sintético de R$ 262,68 para as duas Camila Rocha Neto, cujos títulos são R$ 93,19 e R$ 169,49, é aceito como `matched_aggregate`, embora sejam pessoas diferentes. O motor compara nomes; deve exigir mesma matrícula/CPF para agrupar títulos.
4. **Diferença de boleto sem limite.** Reproduzido em memória: boleto sintético de R$ 30.000,00 contra fatura de R$ 15.013,55 gera match com confiança média e diferença de R$ 14.986,45. É preciso estabelecer critério de materialidade/revisão para evitar tratar qualquer boleto Uber próximo do vencimento como pagamento daquela fatura.
5. **Candidatos retidos não pesquisados.** Reembolsos com bloqueios além de corte/vencimento são excluídos da busca bancária. A elegibilidade de importação e a investigação de pagamentos precisam ser independentes; um título cadastralmente bloqueado pode ter sido pago manualmente.

Os problemas 3–5 não alteraram os resultados esperados desta amostra, mas limitam a abrangência e a confiabilidade do motor. O oráculo da amostra, sozinho, não testa esses cenários.

## Entregáveis locais e conteúdo versionado

| Entregável | Disponibilidade nesta revisão |
|---|---|
| Código, modelos dbt, dependências e instruções | Versionados; há correções de publicação/permissões ainda locais |
| Transações normalizadas/canônicas | Existem em `output/`, ignorado pelo Git |
| Vínculo de usuários e resumo mensal por CC | Existem em `output/`, ignorado pelo Git |
| Imports de AP, candidatos retidos e linhagem | Existem em `output/`, ignorado pelo Git |
| DQ e eventos de normalização | Existem em `output/`, ignorado pelo Git |
| Resumo do controller | Existe em `output/`, ignorado pelo Git |
| Análise de dados, negócio e arquitetura | Versionada em `docs/18_analise_final_pipeline.md` |
| Conciliação opcional | Código e cinco saídas CSV/JSON versionados |

Se o repositório for a única entrega, o avaliador terá de gerar as saídas obrigatórias. Para facilitar o aceite, publicar um conjunto enxuto de saídas demonstrativas (sem banco, logs e fixtures) ou fornecer instruções completas e verificadas de instalação e geração a partir de um clone limpo. O `RUNNING.md` atual ainda parte de uma `.venv` já existente e mistura resultados históricos com a execução vigente.

## Pendências anteriores ainda presentes

- Nove componentes ENTRE-UN em CC300/CC310 somam R$ 327,03 e continuam com `component_blockers=[]`, apesar da classificação Custo × Despesa pendente descrita na análise.
- Uma corrida de R$ 48,29 está dentro do período de emprego e continua retida pelo status atual do RH.
- O resumo do controller precisa incorporar os resultados financeiros da conciliação e distinguir pagamentos de bloqueios de importação.
- O ledger de emitidos continua vazio; ajustes ainda não descontam ajustes anteriores da mesma família. São limites a explicitar para operação recorrente.

## Evidências de execução e conclusão

`tests_bank_reconciliation.py` e `tests_data_controls.py` passaram nesta revisão. A recomputação em memória reproduziu os valores de título e status dos 20 registros do CSV publicado. Foram conferidos os montantes com os movimentos únicos do extrato e executados os dois cenários sintéticos acima, sem gravar alterações nas fontes ou nas saídas.

O hash do script bancário coincide com o registrado no resumo da conciliação. O hash do código local do pipeline **não coincide** com o build publicado, pois há mudanças não commitadas em `run.py`. A conciliação versionada e o `output/` local ainda referenciam o build anterior `fe3db879…`. As mudanças locais de permissões/publicação precisam ser validadas e versionadas antes de serem apresentadas como parte do commit entregue.

**Conclusão:** os reembolsos não foram zerados. A conciliação fecha os valores da amostra, mas sua apresentação permite interpretações incorretas e o motor ainda aceita agrupamento indevido de homônimos. Todos os tipos de entregável existem localmente; a entrega via repositório exige atenção à disponibilização ou reprodução das saídas obrigatórias, além das correções de regra já apontadas.
