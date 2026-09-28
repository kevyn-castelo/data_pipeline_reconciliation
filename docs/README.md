# Documentos — linha do tempo do raciocínio

Os arquivos estão numerados na ordem em que foram escritos. Cada número é uma etapa: desenho do contrato, plano, implementação, revisões e análise final. Documentos substituídos continuam aqui como histórico; o status abaixo indica qual versão vale.

**Para ler o estado atual:** a pasta [`analysis/`](../analysis/) reúne o notebook e o resumo da controladoria; [07](07_contrato_v4_consolidado.md) é o desenho vigente, [18](18_analise_final_pipeline.md) reúne arquitetura e ponte de valores em texto, [17](17_validacao_correcoes.md) valida as correções e [12](12_registro_acoes_financeiras.md) registra ações financeiras pendentes.

**Para entender como se chegou lá:** na cópia local, ler de 01 a 18 em sequência; no repositório público, começar pelo documento 07 e seguir os documentos publicados.

## Linha do tempo

A data vem do próprio documento; o horário, da última gravação do arquivo antes da reorganização. Documentos marcados como *local* são rascunhos e revisões internas: ficam na máquina de trabalho e não são publicados no Git (ver `.gitignore`). Por isso o repositório público mostra lacunas na numeração.

| # | Quando | Fase | Documento | O que é / o que mudou | Status |
|---|---|---|---|---|---|
| 01 | 27/09 20:13 | Contrato | `01_contrato_v0_proposta.md` | Primeira proposta do contrato canônico (RAW → STAGING → CANONICAL, chave de transação, equivalência), escrita para revisão crítica | Histórico, *local* |
| 02 | 27/09 20:26 | Contrato | `02_contrato_decisoes_anteriores.md` | Decisões de uma rodada anterior e roteiro para comparar abordagens; introduz a equivalência pelo significado e pela disponibilidade de cada campo | Histórico, *local* |
| 03 | 27/09 20:52 | Contrato | `03_contrato_v1_proposta.md` | Revisão da v0: valor pago pelo empregado vira checagem, RAW por registro lógico, equivalência campo a campo, `identity_unresolved`, views resolvidos/conflitos, seed de decisões | Histórico, *local* |
| 04 | 27/09 21:16 | Contrato | `04_contrato_v2.md` | Primeiro congelamento: `transaction_id` com `client_id` do config, override explícito de formato de data, decisões D1–D9 e P6 aprovadas | Histórico, *local* |
| 05 | 27/09 21:44 | Contrato | `05_contrato_v3.md` | Correções financeiras A12–A15: aceite usa a ocorrência escolhida, rejeição fica retida, decisão vale só para o conjunto exato de ocorrências | Histórico, *local* |
| 06 | 27/09 21:57 | Contrato | `06_contrato_v3-1_adendo_aba_resumo.md` | Adendo: a aba Resumo do XLSX é inventariada e excluída da análise | Histórico, *local* |
| 07 | 27/09 22:07 | Contrato | [`07_contrato_v4_consolidado.md`](07_contrato_v4_consolidado.md) | Consolida v3 e adendo; acrescenta serial temporal do XLSX, ingestão única por SHA-256 e fixture A15 | **Vigente** |
| 08 | 27/09 22:08 | Plano | [`08_plano_implementacao.md`](08_plano_implementacao.md) | Etapas de implementação, divisão de responsabilidades e escopo enxuto | Histórico |
| 09 | 28/09 11:54 | Implementação | [`09_decisoes_revisao_etapa3.md`](09_decisoes_revisao_etapa3.md) | Decisões C1–C6a da revisão da etapa 3 (rota de cartão por tipo, UTF-8 sem BOM, reenvio de demonstrativo, rateio `ready`, testes de conservação, emissão do reembolso) e o que ficou de fora | Complementa 07 |
| 10 | 28/09 13:03–13:13 | Revisão 1 | [`10_revisao_independente_parecer.md`](10_revisao_independente_parecer.md) + [`10_revisao_independente_consultas.py`](10_revisao_independente_consultas.py) | Revisão independente R01–R16. Achado crítico: os 16 reembolsos liberados já tinham sido pagos. Plano de correção P0–P2 | Histórico; orientou 11–18 |
| 11 | 28/09 13:36 | Análise | [`11_analise_consultas.py`](11_analise_consultas.py) | Consultas somente leitura que reproduzem os números da análise final (18) | Vigente, apoio de 18 |
| 12 | 28/09 13:45 | Ação financeira | [`12_registro_acoes_financeiras.md`](12_registro_acoes_financeiras.md) | Evidência bancária e próxima ação por item (faturas, reembolsos manuais, PIX duplicado, CPF inválido) | **Vigente** |
| 13 | 28/09 14:01 | Revisão 2 | `13_revisao_analytics_engineer_prompt.md` | Escopo pedido ao Analytics Engineer para a segunda revisão | Histórico, *local* |
| 14 | 28/09 16:15 | Revisão 2 | `14_revisao_analytics_engineer_parecer.md` | Segunda revisão: A1–A3 (saída ilegível, corte só por parâmetro, Custo × Despesa sem gate), M1–M4 e B1–B3 | Histórico, *local* |
| 15 | 28/09 16:51 | Revisão 2 | `15_verificacao_entregaveis.md` | Checklist dos entregáveis do TASK contra os artefatos, com ressalvas | Histórico, *local* |
| 16 | 28/09 ~17:40 | Revisão 3 | [`16_reavaliacao_pos_commit.md`](16_reavaliacao_pos_commit.md) | Reavaliação após o commit `0bf9a1b`: reembolsos não estavam zerados; problemas de apresentação e regra na conciliação | Histórico; corrigido em 17 |
| 17 | 28/09 18:18 | Validação | [`17_validacao_correcoes.md`](17_validacao_correcoes.md) | Validação das correções do commit `db1f5b6`: build 67/67, ponte de valores e conciliação no esquema 2 | **Vigente** |
| 18 | 28/09 (última revisão após 17) | Análise final | [`18_analise_final_pipeline.md`](18_analise_final_pipeline.md) | Análise final reemitida após as revisões 10 e 14: arquitetura, ponte de valores, centros de custo, conciliação e decisões do cliente | **Vigente** para arquitetura; análise numérica consolidada no notebook em `analysis/` |

A análise 18 começou antes da revisão 10 e foi reescrita depois das revisões; a versão anterior não foi preservada separadamente. Por isso ela aparece no fim da linha do tempo.

## Nomes anteriores

| Nome atual | Nome anterior |
|---|---|
| `01_contrato_v0_proposta.md` | `contrato_canonico_proposta_v0.md` |
| `02_contrato_decisoes_anteriores.md` | `decisoes_anteriores_canonical_para_comparacao.md` |
| `03_contrato_v1_proposta.md` | `contrato_canonico_proposta_v1.md` |
| `04_contrato_v2.md` | `contrato_canonico_v2.md` |
| `05_contrato_v3.md` | `contrato_canonico_v3.md` |
| `06_contrato_v3-1_adendo_aba_resumo.md` | `contrato_canonico_v3_1_adendo_resumo.md` |
| `07_contrato_v4_consolidado.md` | `contrato_canonico_v4.md` |
| `08_plano_implementacao.md` | `plano_implementacao.md` |
| `09_decisoes_revisao_etapa3.md` | `adendo_decisoes_revisao_etapa3.md` |
| `10_revisao_independente_parecer.md` | `parecer_revisao_independente.md` |
| `10_revisao_independente_consultas.py` | `parecer_consultas.py` |
| `11_analise_consultas.py` | `analise_consultas.py` |
| `12_registro_acoes_financeiras.md` | `registro_acoes_financeiras.md` |
| `13_revisao_analytics_engineer_prompt.md` | `prompt_analytics_engineer.md` |
| `14_revisao_analytics_engineer_parecer.md` | `parecer_analytics_engineer.md` |
| `15_verificacao_entregaveis.md` | `verificacao_entregaveis_case.md` |
| `16_reavaliacao_pos_commit.md` | `reavaliacao_entregaveis_pos_commit.md` |
| `17_validacao_correcoes.md` | `validacao_correcoes.md` |
| `18_analise_final_pipeline.md` | `analise_senior_pipeline.md` |

As citações entre documentos foram atualizadas para os nomes atuais; o texto histórico não foi alterado. O Git preserva os arquivos versionados com o nome anterior (`git log --follow`).

## Convenção para novos documentos

- Usar o próximo número livre (`19_...`) e um nome que diga a fase e o assunto.
- Não renumerar documentos existentes. Quando um documento for substituído, atualizar o status nesta tabela em vez de apagá-lo.
- Documento interno que não deve ser publicado: acrescentar o nome ao `.gitignore` e marcá-lo como *local* aqui.
