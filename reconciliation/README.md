# Conciliação bancária — leitura dos resultados

Extrato até 2026-09-20. Todos os candidatos com identidade, valor e vencimento são pesquisados, inclusive os retidos para importação.

| Beneficiário | Competência | Título (BRL) | Principal atribuído (BRL) | Duplicado (BRL) | Situação |
|---|---|---:|---:|---:|---|
| Uber do Brasil Tecnologia Ltda | 2026-07 | 14519.26 | 14519.26 | 0.00 | matched_exact |
| Uber do Brasil Tecnologia Ltda | 2026-08 | 15013.55 | 15318.82 | 0.00 | matched_with_difference |
| Andre Fonseca Filho | 2026-07 | 61.89 | 61.89 | 0.00 | matched_exact |
| Andre Fonseca Moraes | 2026-07 | 37.37 | 37.37 | 0.00 | matched_aggregate |
| Andre Fonseca Neto | 2026-07 | 146.23 | — | 0.00 | open_as_of_statement_end |
| Bianca Azevedo da Silva | 2026-07 | 63.73 | 63.73 | 0.00 | matched_exact |
| Eduardo Batista Moraes | 2026-07 | 76.97 | 76.97 | 0.00 | matched_exact |
| Eduardo Batista da Silva | 2026-07 | 94.93 | 94.93 | 0.00 | matched_exact |
| Marcos Tavares | 2026-07 | 73.78 | 73.78 | 73.78 | paid_more_than_once |
| Mariana Lopes da Silva | 2026-07 | 142.68 | — | 0.00 | open_as_of_statement_end |
| Andre Fonseca Filho | 2026-08 | 40.79 | 40.79 | 0.00 | matched_exact |
| Andre Fonseca Moraes | 2026-08 | 73.03 | 73.03 | 0.00 | matched_aggregate |
| Andre Fonseca Neto | 2026-08 | 85.04 | 85.04 | 0.00 | matched_exact |
| Bianca Azevedo da Silva | 2026-08 | 115.30 | 115.29 | 0.00 | matched_with_difference |
| Camila Rocha Neto | 2026-08 | 169.49 | 169.49 | 0.00 | matched_exact |
| Camila Rocha Neto | 2026-08 | 93.19 | 93.19 | 0.00 | matched_exact |
| Eduardo Batista Moraes | 2026-08 | 24.33 | 24.33 | 0.00 | matched_exact |
| Eduardo Batista da Silva | 2026-08 | 147.30 | 147.30 | 0.00 | matched_exact |
| Marcos Tavares | 2026-08 | 59.90 | 59.90 | 0.00 | matched_exact |
| Mariana Lopes da Silva | 2026-08 | 102.80 | — | 0.00 | open_as_of_statement_end |

Os valores atribuídos e duplicados são saídas de caixa positivas. Campo vazio/— não é zero.
Diferença principal = pagamento atribuído menos título. A diferença incluindo duplicidade soma o pagamento excedente.
N:1 atribui o PIX pelos valores dos dois títulos da mesma matrícula; não são dois pagamentos independentes.
`bank_movements.csv` tem uma linha por movimento, com valor assinado. `bank_match_pairs.csv` informa o valor atribuído a cada título, que pode ser somado inclusive no N:1.
`bank_review_candidates.csv` contém possibilidades não confirmadas, sem atribuição financeira.
PIX: prefixo, valor e janela de vencimento; N:1 exige mesma matrícula. Homônimos ambíguos ficam para revisão.
Boletos: nome/canal e janela, com diferença limitada a R$ 500.00 e 5.00% simultaneamente. Tolerâncias técnicas não aprovam encargos ou baixas; excessos ficam em revisão.
Alta confiança significa correspondência única pelas regras; o extrato não contém CPF ou identificador do ERP.
Janelas e tolerâncias estão em `config/reconciliation.json`, e os hashes constam no resumo JSON.
