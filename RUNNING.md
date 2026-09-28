# Execução e entregáveis

## Preparar uma cópia nova

Ambientes validados: Windows com Python 3.14.6 e Ubuntu 26.04 sob WSL com Python 3.14.4. As versões de DuckDB, dbt e openpyxl estão fixadas em `requirements.txt`. Na raiz do repositório, em PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py --output output --as-of-date 2026-09-28
.\.venv\Scripts\python.exe bank_reconciliation.py --pipeline-output output --output reconciliation
```

A data explícita reproduz o corte dos entregáveis versionados. Em uma execução operacional, informar a data de avaliação correta. `--first-competence YYYY-MM` controla o início da automação; setembro/2026 é uma premissa configurada para este case e depende de confirmação para implantação. Ela impede reimportar o histórico de julho/agosto. Não representa uma pendência para concluir a análise do case.

Em macOS/Linux, depois de instalar Python 3.14.x com `venv` e `pip`, o ambiente virtual usa `./.venv/bin/python` e o pipeline encontra `./.venv/bin/dbt`. Instalações mínimas do Ubuntu podem exigir o componente `venv` da distribuição:

```bash
python3.14 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python run.py --output output --as-of-date 2026-09-28
./.venv/bin/python bank_reconciliation.py --pipeline-output output --output reconciliation
```

Os caminhos do executável dbt e os finais de linha dos relatórios foram tratados para os três sistemas. No Ubuntu, pipeline e conciliação executaram, os 67 passos dbt e as três verificações Python (dados, banco e suíte sintética) passaram, e 58 relatórios CSV/Markdown ou JSON sem metadados de versão coincidiram byte a byte com os do Windows. Os dois resumos JSON diferiram apenas pela versão do Python e pelo hash derivado dela. A suíte sintética completa também passou no Windows; macOS ainda não foi executado.

## Onde estão os resultados

- `output/README.md`: índice dos entregáveis do pipeline, incluindo canônico, vínculo por e-mail, resumo por CC, imports, retenções, linhagem, DQ e resumo para o controller.
- `reconciliation/README.md`: leitura da conciliação, resultados por título e estratégia de associação.
- `docs/18_analise_final_pipeline.md`: análise arquitetural, dados e negócios, com ponte de valores.
- `docs/12_registro_acoes_financeiras.md`: ações do financeiro e evidências ainda necessárias.
- `docs/17_validacao_correcoes.md`: alterações e verificações da revisão atual.
- `docs/README.md`: linha do tempo numerada de todos os documentos, do primeiro contrato à análise final.

Os CSVs, JSONs, Markdown e marcadores de `output/` entram no Git. `canonical.duckdb`, cópias/compilações dbt e logs são regenerados localmente e ficam ignorados. Os resultados sintéticos ficam em `.test_output/`, também ignorada. Não é necessário versionar o banco para ler os entregáveis; é necessário regenerá-lo para consultar SQL ou executar novamente a conciliação.

## O que esperar desta amostra

588 ocorrências Uber formam 573 candidatos canônicos, dos quais 571 resolvidos e dois conflitos retidos. Há 2 faturas e 18 candidatos de reembolso. O subtotal de componentes com BRL conhecido é R$ 31.842,73; valores desconhecidos não foram preenchidos com zero.

`ap_titulos.csv` e `ap_rateios.csv` contêm apenas os cabeçalhos: nenhum título histórico foi liberado pelo corte, vencimento e demais validações. Os valores e motivos de retenção estão nos arquivos de candidatos. Esses imports vazios são o resultado esperado das regras desta execução.

A conciliação pesquisa todos os candidatos com identidade única, valor e vencimento, mesmo com bloqueios de AP. Ela encontra pagamento principal de R$ 1.217,03 para 15 reembolsos, mais R$ 73,78 em duplicidade. Três reembolsos não têm pagamento localizado no extrato: André Neto (R$ 146,23) e dois de Mariana (R$ 245,48), que também têm CPF inválido. As duas faturas apresentam débitos de R$ 29.838,08; a diferença de agosto é R$ 305,27. O débito VISA de R$ 33,20 é separado dos títulos.

## Como ler a conciliação (schema 2)

- `valor_titulo`: obrigação candidata, preservada independentemente do pagamento.
- `valor_pagamento_principal`: valor bancário atribuído ao título; vazio quando não houve associação.
- `valor_pagamento_duplicado`: pagamento adicional identificado.
- `valor_bancario_atribuido_total`: principal + duplicado.
- `diferenca_pagamento_principal`: principal menos título; zero significa que os valores fecham.
- `diferenca_incluindo_duplicidade`: inclui o excedente por pagamento duplicado.
- `status_importacao` e `bloqueios_ap`: elegibilidade de importação, independente da evidência bancária.

`bank_match_pairs.csv` tem valores atribuídos que podem ser somados: o PIX de R$ 110,40 divide-se em R$ 37,37 e R$ 73,03, sem repetir o valor integral. `bank_movements.csv` guarda cada movimento uma vez, com sinal original e localizador. Não somar novamente os débitos duplicados de `bank_unmatched_debits.csv` aos pares: esse relatório destaca exceções, inclusive a duplicidade já atribuída. `bank_review_candidates.csv` guarda possibilidades sem associação financeira.

N:1 exige dois títulos da mesma matrícula. Homônimos ambíguos ficam em revisão. As janelas e tolerâncias técnicas ficam em `config/reconciliation.json`; os limites de diferença de boleto são simultaneamente R$ 500 e 5% do título. Esses limites não aprovam encargos nem baixas. O extrato termina em 20/09/2026; o último movimento é de 18/09. Aberto significa sem débito identificado nesse recorte pelas regras implementadas.

## Verificações

```powershell
.\.venv\Scripts\python.exe tests_data_controls.py
.\.venv\Scripts\python.exe tests_bank_reconciliation.py
.\.venv\Scripts\python.exe tests_synthetic.py
```

O build executa 33 modelos, um seed e 33 testes dbt antes de publicar. A suíte sintética cobre liberação integral, retenção, reenvios, decisões, publicação e regras de RH/classificação. O teste bancário verifica o oráculo da amostra, conservação das atribuições, homônimos, N:1, CPF bloqueado e diferença material de boleto.

## Reexecução e operação mensal

1. Preservar os arquivos de origem em `data/`; o pipeline registra SHA-256, aba/linha e valores originais. A descoberta transacional e cadastral usa cabeçalhos, sem depender dos nomes dos arquivos.
2. Para outra entrada, usar `--input <pasta>`. Para extrato em outro caminho, passar `--bank <arquivo.csv>` à conciliação. O resumo do controller detecta um extrato por cabeçalho na entrada; múltiplos extratos exigem seleção e conciliação separada.
3. Resolver conflitos somente com evidência em `dbt/seeds/resolutions.csv` ou `--resolutions <arquivo.csv>`. Registrar títulos efetivamente emitidos em `config/issued_titles.csv` ou `--issued-ledger <arquivo.csv>`. O ledger desta amostra está vazio; não se inventaram IDs manuais do ERP.
4. Aprovar Custo × Despesa e atualizar mapas na origem. As regras pendentes em `config/client.json` bloqueiam TRANSP-FUNC e ENTRE-UN nos CC300/CC310 mesmo que exista crosswalk. Só retirar essas pendências após decisão documentada.
5. Conferir o período de vínculo de RH na data da corrida. Status corrente inativo não invalida sozinho uma despesa histórica faturada à empresa; reembolso de desligado exige revisão explícita.
6. Rodar o pipeline, verificar o resumo e arquivar retorno do ERP para cada título emitido. Os IDs são determinísticos, mas a prevenção entre execuções exige manter o ledger atualizado. A integração não grava no ERP.

A saída é construída em pasta irmã temporária. Só após dbt e relatórios concluírem, a anterior é renomeada e a nova é publicada; falhas de build preservam a anterior. Essa troca por duas renomeações não oferece acesso contínuo nem coordenação entre escritores concorrentes. Executar uma publicação por vez. `--keep-failed-build` preserva um build com falha para diagnóstico. O destino existente precisa conter `.uber_pipeline_output`.

No Windows, fechar Excel, conexões DuckDB e terminais posicionados em `output/` se a troca da pasta for bloqueada. Versões antigas que usavam `tempfile.mkdtemp` podiam deixar permissões restritas; o código atual cria a pasta temporária com herança das permissões do workspace.

## Limites restantes

Não há baixa automática nem confirmação de lançamentos manuais no ERP. O candidato de ajuste tardio é diagnóstico, fica bloqueado e compara o total atual ao título original; ainda falta contabilizar ajustes já emitidos para obter o incremento de cada fechamento. Não há liberação automática de créditos. O motor bancário cobre PIX 1:1, dois títulos da mesma matrícula em um PIX e boletos únicos por janela; pagamentos parciais, lotes maiores e extratos sobrepostos exigem extensão. A conciliação escreve seus arquivos após validar as atribuições, mas não possui a mesma troca de pasta do pipeline principal.
