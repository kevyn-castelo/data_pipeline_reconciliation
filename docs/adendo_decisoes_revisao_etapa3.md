# Adendo — decisões da revisão da etapa 3 (28/09/2026)

**Complementa:** `contrato_canonico_v4.md` e `plano_implementacao.md`. Prevalece nos pontos abaixo.
**Origem:** revisão técnica (bug-hunt, ponytail-review, data-engineer), avaliação de um segundo revisor e aprovação do usuário.

## Decisões aprovadas e implementadas

| # | Decisão | Motivo |
|---|---|---|
| C1 | Rota de cartão corporativo vem do **tipo** do cadastro via `config.corporate_card_routes`; tipo sem rota → pendência. Bandeira normalizada com `upper()` antes do regex | Remove bandeira/final fixos no SQL ("don't hard-code"); a normalização anterior apagava minúsculas e podia rotear cartão da empresa como reembolso |
| C2 | Arquivos do ERP em UTF-8 **sem BOM** | Um importador pode ler `﻿id_externo`; a chave de idempotência é o campo mais crítico |
| C3 | Demonstrativo com mesmo número e conteúdo = um documento; conteúdo divergente = conflito; mês com 0 ou >1 demonstrativos = um candidato de mês retido. `id_externo` sem hash de arquivo | Evita dupla contagem e mudança de ID em reenvio; **não** escolhe demonstrativo "principal" (seria precedência sem evidência) |
| C4 | Linha de rateio `ready` só sem nenhum bloqueio do componente | Status de linha não pode induzir a erro |
| C5 | Testes de conservação em R$, exatamente um título por componente, rateio com left join/órfãos/seq e validação direta contra cadastros | Testes anteriores passavam sobre população vazia ou eram tautológicos |
| C6a | `data_emissao` do **reembolso** = último dia do mês de competência | Não há documento de terceiro no reembolso; a empresa emite o próprio título. **Premissa operacional do case**, registrada em `issue_date_basis` e mantida como pergunta ao cliente |

Em C3, quando há versões divergentes do mesmo demonstrativo, os valores financeiros do candidato ficam desconhecidos (`NULL`). O resumo do controller apresenta os valores de cada ocorrência com seus localizadores, sem escolher nem somar versões. O bloqueio `statement_versions_conflict` continua impedindo a liberação da fatura.

## Decisões de não fazer (por enquanto)

| Item | Decisão | Motivo |
|---|---|---|
| `data_disponibilizacao` como emissão da fatura | Não aplicar | Disponibilização e emissão são conceitos distintos; a emissão da fatura é um fato de documento da Uber que não temos. Ganho imediato nulo (faturas retidas por outros motivos). Mantido como pergunta ao cliente |
| `reject_all` excluindo transação do reembolso | Não aplicar | No contrato, `reject_all` rejeita representações de uma chave canônica; não é decisão financeira sobre o direito do empregado. Exclusão de obrigação exigiria decisão financeira separada e auditada. Sem impacto nos dados atuais |
| `id_externo` legível (`UBER_FATURA_{num}` / `UBER_REEMB_{mat}_{AAAAMM}`) | Adiado | Contrato exige estabilidade, não legibilidade; número e matrícula já estão em colunas auditáveis. Convenção original do usuário registrada no profiling (`REPORT.md:135`) |

## Pendências conhecidas (não tratadas nesta rodada)

Fonte única de bloqueios (hoje codificados em três lugares), demonstrativo em XLSX, aplicação da regra 5 (pagamento de empregado/convidado), funil de valores no `run_summary.json`, `dbt.exe` fixo no `run.py`, fração material de serial Excel sem erro explícito. Alteração de título já importado/pago continua fora do escopo e deve ser declarada.
