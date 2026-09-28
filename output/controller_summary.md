# Resumo para o controller

Os arquivos de importação incluem somente títulos aprovados pelo release gate. Subtotais de BRL conhecido são diagnósticos parciais quando há valor ausente, disputa, falha de parsing ou quarentena; não representam o total devido.

## Contas a pagar
- FATURA_FORNECEDOR: 2 candidatos, 0 liberados, 2 retidos.
- REEMBOLSO_COLABORADOR: 18 candidatos, 0 liberados, 18 retidos.
- Arquivos Alchemy: 0 títulos e 0 rateios liberados.
- Corte automatizado configurado: 2026-09; data-base operacional: 2026-09-28. Títulos de competências anteriores ou ainda não encerradas, títulos já emitidos e vencimentos passados ficam retidos.
- Cadastro de títulos já emitidos vazio nesta execução. Confirmar o universo manual diretamente no ERP antes de qualquer importação futura.

## Faturas por demonstrativo
- 2026-07: demonstrativo R$ 14.519,26; subtotal BRL conhecido de detalhes R$ 14.409,24; 2 valores ausentes/disputados e 2 candidatos em quarentena. Não se completou a diferença.
- 2026-08: demonstrativo R$ 15.013,55; subtotal BRL conhecido de detalhes R$ 14.908,99; 1 valores ausentes/disputados e 0 candidatos em quarentena. Não se completou a diferença.
- Conciliação do detalhe 2026-07: diferença de cobranças R$ 110,02, diferença de taxas R$ 0,00, 2 componentes de cobrança sem valor seguro, 2 problemas de integridade e vencimento `overdue`. A diferença não foi lançada por ajuste automático.
- Conciliação do detalhe 2026-08: diferença de cobranças R$ 104,56, diferença de taxas R$ 0,00, 1 componentes de cobrança sem valor seguro, 3 problemas de integridade e vencimento `overdue`. A diferença não foi lançada por ajuste automático.

## Visão mensal de rota
- company_billed: 521 chaves candidatas; 518 valores conhecidos elegíveis ao subtotal, 1 ausentes, 2 disputados, 0 com falha de parsing, 2 em quarentena; subtotal conhecido R$ 29.318,23. É um subtotal do universo desta rota, não valor liberado de AP.
- employee_reimbursement_candidate: 39 chaves candidatas; 39 valores conhecidos elegíveis ao subtotal, 0 ausentes, 0 disputados, 0 com falha de parsing, 0 em quarentena; subtotal conhecido R$ 1.608,75. É um subtotal do universo desta rota, não valor liberado de AP.
- excluded_corporate_card_statement: 12 chaves candidatas; 12 valores conhecidos elegíveis ao subtotal, 0 ausentes, 0 disputados, 0 com falha de parsing, 0 em quarentena; subtotal conhecido R$ 882,55. É um subtotal do universo desta rota, não valor liberado de AP.
- needs_client_card_destination: 1 chaves candidatas; 1 valores conhecidos elegíveis ao subtotal, 0 ausentes, 0 disputados, 0 com falha de parsing, 0 em quarentena; subtotal conhecido R$ 33,20. É um subtotal do universo desta rota, não valor liberado de AP.

## Insights reconciliados
- Maiores centros no faturamento de empresa, por subtotal de BRL conhecido (candidatos, não títulos liberados): CC310: 116 chaves, R$ 5.225,68 conhecido; CC300: 79 chaves, R$ 3.566,09 conhecido; CC210: 53 chaves, R$ 3.421,99 conhecido. No mesmo universo company_billed, UNATTRIBUTED contém 41 chaves e subtotal conhecido R$ 2.594,59; sem rateio imputado.
- Faturamento empresa por mês (subtotal conhecido, com lançamentos de valor desconhecido separados): 2026-07: 260 chaves, R$ 14.409,24 conhecido, 2 ausente/disputado/falha; 2026-08: 261 chaves, R$ 14.908,99 conhecido, 1 ausente/disputado/falha. Como há componentes sem valor e nenhuma fatura foi liberada, isso não permite concluir variação mensal do total devido.
- Rotas fora do faturamento desta integração permanecem visíveis: AMEX corporativo é excluído para processo próprio; VISA 0042 está pendente de decisão. Os subtotais dessas rotas não são contas a pagar liberadas.

## Qualidade e pendências
- DQ por bucket (registros de issue, podem haver vários por candidato): auto_fixable=1978, needs_client=289, rule_based=177. Consulte `dq_report.csv` para localizadores e lineage.
- Custo × Despesa pendente: ENTRE-UN, 9 componentes / R$ 327,03. A pendência bloqueia o título e o rateio até decisão da controladoria.
- Custo × Despesa pendente: TRANSP-FUNC, 71 componentes / R$ 4.972,40. A pendência bloqueia o título e o rateio até decisão da controladoria.
- RH: after_termination, 3 componentes / R$ 173,56. Corridas fora da vigência requerem revisão; status corrente inativo não bloqueia por si só corridas históricas faturadas à empresa.
- Compliance: mobility_black_policy_violation, 6 alertas para RH/gestor. A política não reduz o valor devido à Uber.
- Compliance: mobility_eats_order_cap_violation, 4 alertas para RH/gestor. A política não reduz o valor devido à Uber.
- Compliance: mobility_weekend_policy_violation, 6 alertas para RH/gestor. A política não reduz o valor devido à Uber.
- Decisões para liberar AP:
  - Informar a regra/fonte autorizada para `data_emissao` das faturas; o demonstrativo fornece apenas `data_disponibilizacao`. Podemos usá-la como emissão? Até a resposta, não foi tratada como emissão.
  - Confirmar a premissa operacional adotada neste case: `data_emissao` do reembolso = último dia do mês de competência (18 candidatos, `issue_date_basis=config:last_day_of_competence_month`). Não há documento de origem com essa data; em produção depende de validação do cliente.
  - Definir como ratear `Admin Fee` por centro de custo/contas; hoje bloqueia integralmente a fatura.
  - Confirmar a divergência gerencial de EVENTO; nenhuma sugestão foi aplicada automaticamente.
  - Definir/substituir a conta contábil sintética TREIN por conta postável e confirmar crosswalk.
  - Fornecer/evidenciar BRL para o lançamento CLP sem conversão ou preencher fontes que sustentem os componentes ausentes/disputados; a diferença do demonstrativo não foi usada como plug.
  - Revisar os 2 grupos de chave com valores conflitantes e registrar decisão explícita de ocorrência, sem somar versões.
  - Classificar o débito em conta da VISA corporativa final 0042; a conciliação bancária separada encontra o movimento de R$ 33,20.
- Confirmar as ligações de email Uber pendentes: 2 ambiguidades e 4 não encontrados; não escolher usuário por nome/Employee ID.
- Cadastro: há duplicidade nominal de fornecedores Uber. As faturas atuais foram ligadas pelo CNPJ do demonstrativo a um registro único; confirmar/limpar o cadastro para evitar ambiguidade futura.

## Evidência bancária
Fonte: extrato_itau_cc_2026-07_a_2026-09.csv. Pagamento no extrato não comprova baixa no ERP. Bloqueios de importação não excluem a pesquisa bancária.
- Uber do Brasil Tecnologia Ltda / 2026-07: documento R$ 14.519,26, débito principal R$ 14.519,26, diferença R$ 0,00; composição/classificação de diferenças depende de evidência.
- Uber do Brasil Tecnologia Ltda / 2026-08: documento R$ 15.013,55, débito principal R$ 15.318,82, diferença R$ 305,27; composição/classificação de diferenças depende de evidência.
- Andre Fonseca Neto / 2026-07: open_as_of_statement_end, título R$ 146,23; conferir ERP/comprovante antes de ação financeira.
- Marcos Tavares / 2026-07: título R$ 73,78, pagamento principal R$ 73,78 e duplicidade R$ 73,78; verificar restituição/compensação.
- Mariana Lopes da Silva / 2026-07: open_as_of_statement_end, título R$ 142,68; conferir ERP/comprovante antes de ação financeira.
- Bianca Azevedo da Silva / 2026-08: documento R$ 115,30, débito principal R$ 115,29, diferença R$ -0,01; composição/classificação de diferenças depende de evidência.
- Mariana Lopes da Silva / 2026-08: open_as_of_statement_end, título R$ 102,80; conferir ERP/comprovante antes de ação financeira.
- Reembolsos: 15 títulos com pagamento associado; principal R$ 1.217,03, duplicidades R$ 73,78.
- Débitos de cartão associados: 1, R$ 33,20; classificação contábil ainda pendente.

Os números por rota e centro de custo estão em `int_monthly_cost_center_payment_summary.csv`. Os arquivos detalhados da conciliação são gerados por `bank_reconciliation.py` em `reconciliation/`, com movimentos únicos e valores atribuídos por título. Nenhuma baixa no ERP é executada.
