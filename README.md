# Integração Rastreável de Dados Financeiros e de Produção por RPA para Apoio à Decisão Organizacional

Repositório do artefato de pesquisa desenvolvido sob a metodologia *Design Science Research* (DSR) voltado ao Simpósio Brasileiro de Sistemas de Informação (SBSI).

Automação local em Python: extração do GERP simulado → preservação de integridade de entradas (hashes SHA-256) → validação por porta de qualidade → cruzamento rastreável → regras financeiras/produção → relatório textual e JSON com manifesto → conferência e revisão humana supervisionada no Streamlit.

O projeto é um protótipo experimental para investigação em Sistemas de Informação Organizacionais. Resultados sintéticos caracterizam o comportamento técnico nas condições controladas do protocolo e não constituem estudo de campo com dados empresariais reais.

## Instalar e demonstrar

Python **3.12** (mesma versão do CI). No PowerShell, na raiz do projeto:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m src.main --local
python -m streamlit run src/dashboard.py
```

Abra `http://127.0.0.1:8501`. O comando `--local` usa explicitamente o financeiro local como contingência. Os dados originais da demonstração são antigos e o financeiro local não possui evidência temporal; é esperado um resultado **PROVISIONAL**, não uma afirmação de atualidade. Consulte fontes, problemas e valores, selecione uma ocorrência e registre uma justificativa com responsável autodeclarado. O resultado automático continua preservado.

Para extração pelo navegador:

```powershell
python -m playwright install chromium
python -m http.server 8000 --bind 127.0.0.1 --directory gerp_fake_server
# Em outro terminal, com o ambiente virtual ativo:
python -m src.main
```

A URL padrão é `http://localhost:8000/web/gerp_fake.html`. A interface declara o período **2026-W34**; baixá-lo hoje não o torna atual. Credenciais e caminhos ficam no `.env`; não são exportados ao manifesto. `HEADLESS=false` permite ver a automação local.

## Execuções preservadas e replay

Cada execução cria `output/runs/<timestamp_UUID>/` com:

- `inputs/`: cópias binárias das entradas e do modelo textual;
- `policy.json`: política efetivamente usada, sem credenciais;
- `result.json`: estado, fontes, qualidade, decisões por linha e análise operacional;
- `manifest.json`: horários e duração das etapas, hashes, versão Git, indicação de alterações locais, hashes do código e versões de dependências;
- `relatorio.txt`: modelo textual existente acrescido de estado e limitações;
- `reviews.sqlite`: criado apenas ao registrar a primeira revisão, separado dos resultados.

```powershell
python -m src.main --replay output/runs/ID_DA_EXECUCAO
python -m src.main --local --policy config/policy.json
```

Replay verifica hashes das entradas e do modelo, usa a política preservada e gera **outro ID**, sem nova extração. A atualidade é reavaliada na data do replay. O código executado é o código instalado naquele momento e fica identificado no novo manifesto; para repetir exatamente uma versão, é necessário também restaurar código/dependências correspondentes. Política alternativa no replay é permitida e registrada na nova execução.

Saída de processo: `0` para concluído/provisório, `1` para bloqueado/falha. **Código 0 não significa dados atuais**: consumidores devem ler `state`, `provisional` e `publication_allowed`. “Publicação” aqui significa liberação local de conclusões; não existe envio externo.

## Política e regras

Edite `config/policy.json`: `quality_mode` (`partial` ou `block`), `freshness_policy` (`provisional` ou `block`), `max_age_days` e os dois limiares percentuais. Sem `--policy`, os limiares do `.env` continuam tendo precedência para preservar o fluxo antigo. Com `--policy`, o JSON é a referência. `rules_version` identifica a implementação, não é um rótulo arbitrário.

As fórmulas existentes foram mantidas: `(custo - faturamento previsto)/faturamento previsto*100` e `(planejado - produzido)/planejado*100`. Custo superior ao previsto com status de produção não normal é CRITICO; desvio desfavorável **maior ou igual** ao limiar ou status atípico é ATENCAO. Os demais registros válidos são NORMAL. Dados inválidos ficam fora dessas classificações.

Detalhes, ambiguidades de negócio e pontos de extensão: [arquitetura e políticas](docs/ARQUITETURA_POLITICAS.md).

## Testes e experimentos

```powershell
python -m pytest tests -q
python -m src.experiments --repetitions 3
python -m src.research_evaluation --repetitions 3
```

Em ambientes com restrição ao diretório temporário, use um diretório **novo** do projeto: `python -m pytest -q --basetemp=output/pytest-NOVO_ID`. O pytest limpa seu `basetemp`; não aponte para entradas ou evidências.

O experimento gera dez cenários sintéticos, protocolo e oráculo antes da execução, entradas, manifestos, métricas JSON/CSV e repetições isoladas em `output/experiments/<UUID>`. A indisponibilidade é injetada na fronteira de aquisição, executando o fallback/circuit breaker reais; não representa uma medição de latência de rede empresarial. Os testes verificam o software; o experimento caracteriza somente os cenários definidos. Veja [protocolo experimental](docs/PROTOCOLO_EXPERIMENTAL.md) e [verificação efetivamente realizada](docs/VERIFICACAO.md).

Para a avaliação de pesquisa, o segundo comando executa três instanciações sintéticas e compara a baseline histórica com a versão aprimorada no fluxo financeiro/produção. Veja [avaliação multiprocesso](docs/AVALIACAO_MULTIPROCESSO.md), [revisão inicial](docs/REVISAO_LITERATURA_INICIAL.md) e [rascunho do artigo](docs/ARTIGO_SBSI_RASCUNHO.md). Os dois novos cenários não representam requisitos de sourcing, materiais ou ECOs reais.

Para consultar uma execução experimental no dashboard, defina `OUTPUT_DIR` no terminal como o diretório do cenário que contém `runs`, antes de iniciar o Streamlit.

## Docker

```powershell
Copy-Item .env.example .env
docker compose up --build gerp-fake robo-relatorios
docker compose --profile dashboard up --build dashboard
```

O dashboard fica vinculado a `127.0.0.1:8501`. O robô usa Chromium headless e os volumes locais `data`, `output` e `logs`. Para replay: `docker compose run --rm robo-relatorios --replay /app/output/runs/ID`. Garanta permissão de escrita dos volumes para o usuário `robo` (também para `reviews.sqlite`). A imagem mantém a base Playwright original e acrescenta a configuração e Streamlit.

## Baseline histórica e limitações do artefato

A referência histórica da baseline está registrada em [BASELINE.json](docs/BASELINE.json), correspondente ao commit `7e1768daf5d4081450ee5d6e904c8c0d3a5a983d`, preservada para replicação da avaliação comparativa. A inspeção da versão inicial confirmou a presença da extração básica com Playwright, pandas, fallback e circuit breaker; a versão original não possuía validação explícita por porta de qualidade, controle de metadados temporais, dashboard de supervisão humana ou histórico rastreável de revisões.

Revisões são locais, sem autenticação, assinatura digital ou proteção contra edição dos arquivos por seu proprietário. Hashes detectam alterações quando comparados com o manifesto preservado, mas não garantem origem autêntica nem inviolabilidade. O armazenamento inclui dados de entrada: controle acesso e retenção conforme o contexto. A extração/circuit breaker pressupõe um escritor por diretório de dados; o histórico SQLite suporta transações locais. Não foi implementado agendador, ML, nuvem, e-mail ou serviço pago.
