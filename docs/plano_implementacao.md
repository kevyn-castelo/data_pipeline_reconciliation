# Plano de implementação — case Uber → Alchemy ERP

**Data:** 27/09/2026. **Status:** autorizado para execução por etapas e code-review.  
**Contrato vigente:** `contrato_canonico_v4.md`. As versões anteriores são histórico.  
**Modo de trabalho:** ponytail full; menor implementação que atende à TASK e ao contrato, sem retirar controles financeiros.

## Objetivo e divisão de responsabilidade

Entregar o pipeline local reproduzível pedido em TASK.md. A construção será delegada ao GPT-6 Luna, com contexto de arquivos explícito; o agente principal revisará o código e reproduzirá verificações críticas. Uma etapa não é considerada aprovada apenas porque o executor a declarou concluída.

Nesta primeira delegação, implementar somente **etapa 1: RAW → STAGING → CANONICAL**. O plano das etapas seguintes está definido abaixo; elas não devem ser antecipadas pelo executor antes do checkpoint. A revisão não reabre a arquitetura salvo erro demonstrado, nova evidência ou requisito obrigatório do case.

## Fontes e precedência

1. Requisitos do usuário, TASK.md, README.md, politica_mobilidade.md e layout_importacao_contas_a_pagar.md.
2. Contrato v4 para representação técnica, identidade, conflitos e resoluções.
3. Dados originais em data/; preservá-los integralmente.
4. Profiling como evidência exploratória e funções candidatas a reutilização, nunca como fonte de valores de produção ou regra de first/latest wins.

Ler os documentos e os arquivos afetados antes de implementar. Não executar scripts do profiling pelos pontos de entrada nem sobrescrever profiling/output. Não importar profile_case.py indiscriminadamente: há criação de diretório no módulo. Extrair/reutilizar somente funções adequadas, removendo dependência de nome de arquivo ou ordem fixa de colunas. Não alterar README.md do case para transformar suposição em requisito; escrever instruções de execução separadas.

## Escopo técnico enxuto

- Python para ingestão estrutural, configuração/orquestração, validações de documentos e escrita dos CSVs finais. DuckDB + dbt para camadas tipadas, resolução e transformações SQL. Pandas fora do caminho crítico.
- Um run.py; um projeto dbt local; poucos módulos necessários. Recriar somente banco/saídas gerados no diretório de execução, nunca entradas ou evidências anteriores.
- Um mapeamento explícito por layout suportado, reconhecido pelos cabeçalhos. Ordem de colunas e nome de arquivo não determinam semântica. Layout desconhecido ou ambíguo falha explicitamente.
- Dependências mínimas com versões reproduzíveis. Usar ambiente do projeto. Se instalação falhar por restrição de rede, comunicar o bloqueio e solicitar a permissão prevista pelo ambiente; não contornar controles.
- Sem cloud, UI, scheduler, framework de adapters, multitenancy, atualização automática de títulos pagos ou processamento incremental. Conciliação bancária é opcional posterior.
- Datas de execução podem estar no recibo operacional, mas não tornar aleatórios IDs, dados ou relatórios de negócio. Mesmas entradas, configurações, regras e decisões devem reproduzir o resultado.

## Etapa 1 — ingestão, STAGING e CANONICAL

### Entregáveis

- run.py executa este núcleo em uma pasta de saída explícita; erros retornam código de saída não zero. Um arquivo de instruções descreve instalação e comando.
- Manifesto de arquivos e nomes recebidos; raw_files; raw_uber_occurrences; tabelas auxiliares RAW para cadastros podem ser apenas carregadas estruturalmente nesta etapa.
- stg_uber_transactions; int_transaction_versions; int_transactions; views int_transactions_resolved e int_transaction_conflicts.
- Configuração de cliente/layout; seed resolutions.csv inicialmente vazio; logs técnicos antes/depois, erros e motivos de retenção.
- Saídas auditáveis do núcleo: transações/candidatos, versões, retenções, lineage e resumo de contagens/estados. Não emitir ap_titulos/ap_rateios provisórios como se estivessem aprovados.

### Regras de implementação obrigatórias

1. Ingerir bytes idênticos uma vez por SHA-256 completo e registrar aliases de arquivo. Preservar registros distintos dentro da fonte. Localizador CSV é registro lógico + intervalo de linhas físicas; XLSX é aba + linha.
2. Classificar abas antes de validar Company. Ignorar abas não transacionais; Resumo não é fonte analítica. Company exigido apenas nas fontes transacionais Uber, não nos cadastros de apoio.
3. RAW preserva originais. Usar valores numéricos do XML quando necessário para preservar dinheiro/seriais; leitor limitado e explícito é suficiente. Não criar um parser universal de XLSX.
4. STAGING 1:1, sem decisão de negócio. Normalizar cabeçalhos e campos segundo v4; DECIMAL para dinheiro; erros e ausência não viram zero. Datas textuais DD/MM versus MM/DD exigem prova/override; células nativas seguem workbook.
5. Seriais temporais: conversão decimal, calendário do workbook e resíduo inferior a 1e-6 segundo normalizado HALF_UP antes da chave, com log. Fração material não é truncada silenciosamente. A15 compara conteúdo; D8 testa timestamp transacional, incluindo componente fracionário quando relevante.
6. Agrupar pela chave candidata somente quando interpretável. Duplicatas equivalentes consolidam uma vez; comparação por campo/disponibilidade no grupo todo, com NULL e parse_error distintos. Fingerprint não decide equivalência.
7. Dentro do mesmo arquivo, repetição da chave retém. Múltiplas chaves Fare por viagem retêm. Tipo desconhecido retém. Não escolher versões pela ordem, data de arquivo, montante ou fechamento do demonstrativo.
8. Resolução por mesma chave: accept_occurrence escolhe a representação integral da ocorrência e seus erros; reject_all permanece retido. Conjunto exato de occurrence_id analisados determina validade; mudança implica stale. Uma escolha não supera bloqueios independentes. Validar configuração do seed; não simular respostas reais do cliente.
9. Preservar todos os motivos e alternativas, mantendo uma linha por candidato nas views. Identidade não interpretável continua uma linha por ocorrência, IDs de negócio NULL. Valor ausente pode estar canonicamente resolvido e continua pendência financeira posterior.

### Verificações de aceite

- Hashes das entradas antes/depois iguais; nenhum arquivo original/profiling modificado.
- Contagens raw = staging = versions e cobertura bidirecional de todas as ocorrências; partição resolvidos/retidos sem sobreposição.
- Conferir os arquivos reais por leitura independente: referências históricas 588 ocorrências e 573 candidatos, 13 grupos equivalentes e 2 conflitantes. São checagens da amostra, não hardcode de produção. Divergência exige explicação, não ajuste para bater número.
- XML: 250/286 seriais transacionais fracionários, 137 mudariam de minuto por truncamento ingênuo; conversão normalizada deve preservar os 6 pares de overlap XLSX/complemento. Esses números vêm da investigação anterior e precisam ser reproduzidos para o recibo da execução.
- Sintéticos pequenos, cobrindo o contrato: reenvio idêntico; registro repetido no arquivo; formatos/colunas reordenados; NULL versus zero; dinheiro residual abaixo/no limite; identidade inválida; tipo desconhecido; A/B/C de disponibilidade; A15 nos horários de request e D8 no timestamp transacional; dois Fares; aceitação/rejeição/stale e bloqueio independente.
- Reexecução no mesmo input produz mesmos dados e IDs. Inventário pode adicionar outro nome de arquivo, sem aumentar população de negócio.
- Testes de unicidade e nulabilidade respeitam o grain e o formato; transaction_id não é único em versões. Usar dbt tests e testes Python pequenos, sem criar framework próprio.

## Etapa 2 — cadastros, enrichment e validações

Após aprovação do núcleo: e-mail normalizado/aliases → usuário interno → matrícula → funcionário → CC oficial; convidados pelo solicitante documentado. Detectar cardinalidade ambígua antes de joins para não multiplicar dinheiro. Uber Employee ID, nome e Group não substituem esse vínculo.

Expense Code → conta contábil analítica/ativa → crosswalk gerencial oficial e conta válida. Bandeira + últimos quatro → cartão corporativo/pessoal; manter AMEX fora da integração. Competências: Periodic Billing por timestamp UTC; reembolso por data local da viagem. Validar CPF/CNPJ por algoritmo, cadastros, valores e precisão. Separar DQ, aprovação financeira e compliance; violação de política não reduz dívida.

Pendências existentes do Notion continuam explícitas: regra de Admin Fee/CC, gaps de mapping, aliases ambíguos, CLP sem BRL, divergências monetárias, destino VISA 0042, calendário de feriados, composição Eats e emissão de reembolso. Não inventar resolução; materializar pergunta e impacto. Ausência de calendário não cria feriado presumido.

## Etapa 3 — candidatos de títulos, rateios e release gate

Um candidato por demonstrativo Uber; reembolso por funcionário/mês local. Montar a população completa antes de liberar: uma linha problemática não pode simplesmente sair do agrupamento e deixar um título parcial parecer válido. Preservar AMEX excluído como destino explicado, sem tratá-lo como dívida dessa integração.

IDs estáveis por tipo e documento/grupo, independentes de execução. Rateio por CC × conta; negativos permitidos conforme layout. Total positivo, documentos válidos, contas/CC válidos e fechamento exato ao centavo; divergência retém o título completo. Não preencher missing BRL pela diferença do demonstrativo, não somar versões conflitantes, não usar sucesso da reconciliação para escolher versão.

Saídas ap_titulos.csv e ap_rateios.csv estritamente no layout oficial, somente para títulos liberados; arquivos podem ter apenas cabeçalho se nenhum título tiver suporte. Isso deve decorrer das regras e ser explicado, nunca ser um atalho para evitar implementar a liberação. Saída separada de candidatos/retidos, vínculos de rateio até ocorrência e motivos específicos.

## Etapa 4 — apresentação e reprodutibilidade

Tabela de vínculo por e-mail; resumo por CC e forma de pagamento com não atribuídos explícitos; DQ nos três buckets da TASK; controller summary e insights reproduzíveis com valores conhecidos, desconhecidos e disputados separados. Documento simples é suficiente; dashboard/PPTX/notebook não são condição para fechar o core. Todo número reconcilia com liberados, retidos ou exclusões explicitadas, sem somar alternativas como dívidas.

Execução limpa e reexecução; comandos documentados; dependências reproduzíveis; conferência independente das populações e totais críticos. Conciliação bancária somente depois do core aprovado, se houver tempo.

## Protocolo de delegação e code-review

- Executor informa arquivos alterados, comandos executados, resultados reais e limitações. Não marca teste como aprovado sem executá-lo. Não altera contrato para justificar o próprio código.
- Revisor verifica implementação contra requisitos, casos financeiros, caminhos de erro e resultados dos testes; não apenas estilo. Confere independentemente contagens/valores críticos diretamente das fontes.
- Correções prioritárias: perda/duplicação, parsing incorreto, liberação indevida, falta de lineage, joins que multiplicam valores, outputs inválidos e falta de reprodução. Melhorias cosméticas ficam para depois.
- Aprovar etapa apenas após corrigir problemas materiais e repetir os testes afetados. Resultado: aprovado, aprovado com limite documentado, ou pendente com defeito concreto.
- Notion registra decisão, etapa e evidência de conclusão; o código e o recibo da execução comprovam o que foi realizado. Não confundir contrato congelado com pipeline homologado.
