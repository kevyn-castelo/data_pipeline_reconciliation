# Registro de ações financeiras — corte de 28/09/2026

Este registro documenta evidência e encaminhamento. **Não substitui a baixa no ERP, comprovante bancário nem aprovação contábil.** O corte configurado para automação é **2026-09, provisório**; `run.py --as-of-date 2026-09-28` gerou arquivos de importação apenas com cabeçalho para julho/agosto.

| ID | Evidência disponível | Estado operacional | Responsável pela decisão/execução | Próxima ação e aceite |
|---|---|---|---|---|
| F-JUL | Demonstrativo R$ 14.519,26; débito `SISPAG BOLETO UBER` em 10/08 pelo mesmo valor | Pagamento observado no extrato; baixa no ERP a confirmar | Financeiro/tesouraria | Localizar título manual e comprovante, registrar vínculo e data de baixa; resolver classificação/rateio sem criar segundo pagamento |
| F-AGO | Demonstrativo R$ 15.013,55; débito em 11/09 de R$ 15.318,82 | Pagamento observado; diferença de R$ 305,27 sem composição aprovada | Financeiro, Uber e controladoria | Obter boleto/aviso de encargos; aprovar conta contábil de despesa financeira e mapa gerencial antes do lançamento. Multa de 2% + juros de 1 dia é hipótese, não fato contabilizado |
| R-MANUAIS | 15 dos 16 reembolsos do gate antigo aparecem pagos via PIX, conforme parecer; usuário informa lançamento manual no ERP | **Bloqueados para importação** pelo corte de competência/vencimento | Financeiro | Confrontar export do ERP por beneficiário, competência e valor; registrar IDs manuais e liquidação no livro de títulos emitidos |
| R-MARCOS | PIX R$ 73,78 em 17/08 e novamente em 18/08 | Possível pagamento duplicado; recuperação pendente | Financeiro/RH | Confirmar os dois comprovantes e tratar restituição ou compensação autorizada; registrar decisão e data |
| R-ANDRE | Reembolso julho R$ 146,23, vencimento 15/08, sem PIX correspondente até o fim do extrato | Em aberto no recorte bancário | Financeiro | Confirmar no ERP e em extrato posterior; pagar/regularizar se ainda aberto e registrar comprovante |
| R-BIANCA | Título agosto R$ 115,30; PIX R$ 115,29 | Diferença bancária de −R$ 0,01 | Financeiro | Verificar arquivo PIX/ERP e decidir ajuste ou baixa residual de R$ 0,01 |
| CARTAO-0042 | Débito `UBER *TRIP` de R$ 33,20 em 23/07, compatível com VISA 0042 | Liquidação observada; classificação pendente | Tesouraria/controladoria | Confirmar vínculo com cartão/débito PJ e conta/centro de custo apropriados; não gerar reembolso pessoal |
| R-CPF | Dois reembolsos somando R$ 245,48 têm CPF inválido no cadastro | Retidos, sem pagamento identificado no extrato revisado | RH/financeiro | Corrigir CPF na fonte com documento válido e revisar elegibilidade; não criar título com CPF inferido |

**Pendências de implantação:** confirmar setembro/2026 como primeira competência; obter export de títulos manuais/retornos do ERP; definir datas/documento e tratamento de crédito para ajustes tardios; aprovar conta de encargos. Nenhum desses campos foi inventado pelo pipeline. O arquivo `config/issued_titles.csv` começa vazio e deve receber somente títulos **efetivamente emitidos** após conferência no ERP, com valor e data aprovados; IDs manuais diferentes exigem cadastro/ligação própria.
