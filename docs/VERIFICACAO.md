# Verificação realizada em 18/09/2026

Ambiente: Windows, Python 3.12.14, ambiente virtual local; dependências de `requirements.txt`. Versões de execução estão também nos manifestos. Alterações não foram publicadas nem enviadas a serviços externos.

## Resultados efetivamente observados

- **46 testes passaram em 3,16 s**: `python -m pytest -q --basetemp=output/pytest-session-3`. Incluem testes originais de cálculos, relatório e circuit breaker; novos testes de valores desconhecidos/não finitos, chaves, duplicatas, denominadores, esquema, atualidade, bloqueio, replay, hashes, logs sem mensagem sensível, revisão e formulário Streamlit. O teste legado que esperava ATENCAO para integração ausente foi atualizado para DADOS_INVALIDOS com percentual nulo: essa é uma correção explícita de semântica de qualidade, não alteração das fórmulas válidas.
- **30 execuções experimentais conforme o oráculo**: dez cenários sintéticos, três repetições. Na unidade e critérios definidos no protocolo: zero falsos alertas e zero erros silenciosos observados. Isso não estima uma taxa de erro empresarial nem garante correção em entradas arbitrárias.
- **Navegador real**: `python scripts/verify_browser.py` iniciou servidores em localhost, fez login e download via Chromium, verificou modo `current_extraction`, três projetos e estado provisório devido à referência 2026-W34. Abriu o dashboard com Streamlit, verificou o aviso e a presença da revisão humana, ausência de erro de aplicação e capturou `dashboard.png`. Os servidores de verificação foram encerrados pelo próprio script. O envio do formulário foi coberto por Streamlit AppTest, não por clique do Chromium.
- **Fluxo local demonstrado**: `python -m src.main --local` gerou execução provisória, com dois projetos NORMAL e um CRITICO. Financeiro sem referência temporal e produção antiga aparecem no texto e JSON. Logger registrou apenas ID/estado e alerta para conferência.
- `git diff --check` sem erros de whitespace. Docker não disponível nesta máquina: arquivos atualizados, mas **build e execução Docker não foram realizados**. O CI remoto não foi executado.

## Evidências

As métricas, protocolo e identificação da execução foram copiados para [evidence](evidence/source.json), para acompanhar o código. [CSV de métricas](evidence/metrics.csv), [JSON de métricas](evidence/metrics.json), [protocolo prévio](evidence/protocol.json).

Artefatos completos locais (ignorados pelo Git, não apagar se forem usados na pesquisa):

- `output/experiments/a90df7feda974194afa8b74ca0062c71/`: protocolo, política, entradas, 30 execuções com hashes, resultados e tempos.
- `output/browser-verification/6e534bd3f8504474889b4786c87b11b1/`: verificação ponta a ponta, captura do dashboard, log de inicialização e execução preservada.
- `output/runs/20260918T184319_39866919cb414dd3bb57c6a4698bbfe1/`: demonstração final com contingência local.

Os manifestos identificam a baseline Git, indicam árvore modificada e incluem hashes do código executado. Esses hashes e arquivos preservados ajudam a explicar os resultados; não equivalem a uma assinatura digital. Os tempos individuais no CSV medem apenas o pipeline nas condições descritas. Nenhum tempo manual, ganho percentual, avaliação de gestor ou implementação dos outros dois projetos foi inventado ou realizado.

## Pendências científicas e operacionais

Validar com o gestor significado dos indicadores e status, política de 14 dias, admissibilidade de valores negativos, períodos diferentes e casos de denominador zero. Implementar/adaptar os outros processos para avaliar reutilização real. Executar o protocolo pareado com participantes e entradas equivalentes. Definir retenção/controle de acesso e política de atualização de dependências antes de usos além da demonstração local. Autenticação, assinatura digital, inviolabilidade, execução concorrente da extração e integração empresarial não foram implementadas.
