# Revisão — Avaliação 03: Desenvolvimento de Solução de Hyperautomation

Este documento responde, item a item, ao checklist de revisão passado pelo
professor. **Todos os integrantes devem conseguir explicar qualquer um
destes pontos**, não só a pessoa responsável pela parte técnica correspondente.

---

### Como o processo funciona?

O robô executa o pipeline **Extrair → Tratar → Cruzar → Analisar →
Identificar divergências → Gerar relatório** (orquestrado em `src/main.py`):

1. **Extrair**: acessa o GERP simulado (`gerp_fake.html`) via Playwright,
   faz login e captura o download do CSV de faturamento — protegido por um
   Circuit Breaker (ver abaixo).
2. **Tratar**: lê o CSV e o Excel de produção, normaliza tipos numéricos e
   remove duplicatas.
3. **Cruzar**: junta os dois conjuntos pela chave `Codigo_Projeto`
   (`outer join`, para não perder projetos sem correspondência).
4. **Analisar / Identificar divergências**: calcula o desvio financeiro e
   o desvio de produção de cada projeto e classifica em `NORMAL`,
   `ATENCAO` ou `CRITICO`.
5. **Gerar relatório**: preenche o modelo `modelo_relatorio_final_diretoria.txt`
   com o resumo, indicadores, divergências e recomendação, salvando também
   um JSON estruturado para auditoria.

### Qual é a regra de negócio principal?

Um projeto é **CRÍTICO** quando o **custo realizado supera o faturamento
previsto** e, ao mesmo tempo, o **status de produção é diferente de
"Normal"** (ex.: "Atrasado"). É exatamente o caso do `PROJ_REF_02`:
previsto R$ 800.000, custo R$ 850.000 (desvio +6,25%), produção 1.200/1.500
unidades (desvio +20%), status "Atrasado". Fora esse caso, um desvio
desfavorável (financeiro ou de produção) acima de um limiar configurável
(padrão 5%, em `LIMIAR_DESVIO_FINANCEIRO_ATENCAO` / `LIMIAR_DESVIO_PRODUCAO_ATENCAO`)
gera classificação `ATENCAO`.

### Como o robô trata erros?

Em três camadas:

1. **Try/except localizado**: `extrair_via_gerp_fake` captura erros de
   timeout do Playwright e os converte em `ExtracaoGERPError`.
2. **Fallback**: se a extração falhar, o robô usa o CSV local já
   disponível (`extrair_com_fallback`), sem travar o restante do pipeline.
3. **Try/except geral no orquestrador** (`src/main.py`): qualquer exceção
   não prevista é capturada, logada com stack trace completo
   (`logger.exception`) e dispara um alerta crítico antes do robô encerrar
   com código de saída 1 — nada falha silenciosamente.

### Como os testes foram realizados?

Com **pytest** (18 testes em `tests/`), cobrindo:
- leitura do CSV/Excel;
- tratamento (tipos, duplicatas);
- cruzamento (inclusive projetos sem correspondência);
- cálculo de desvios financeiro e de produção;
- classificação correta do `PROJ_REF_02` como crítico;
- geração do relatório (placeholders substituídos);
- as transições de estado do Circuit Breaker (fechado → aberto →
  meio-aberto → fechado, e persistência de estado em disco).

Rodar com: `pytest tests/ -v`.

### Como o Docker foi configurado?

- **Dockerfile**: baseado em `mcr.microsoft.com/playwright/python` (já
  traz o Chromium), timezone `America/Manaus`, usuário não-root (`robo`).
- **docker-compose.yml**: dois serviços — `gerp-fake` (serve a interface
  simulada com `healthcheck`) e `robo-relatorios` (builda a imagem do
  robô, depende do `gerp-fake` estar saudável, roda uma vez e encerra).
- **Volumes**: `data/`, `output/` e `logs/` são montados do host para o
  container, permitindo trocar entradas e inspecionar saídas sem
  rebuildar a imagem.
- **Variáveis de ambiente**: tudo sensível/configurável vem do `.env`
  (nunca hardcoded) — URL do GERP, credenciais, caminhos, timezone e
  limiares de negócio.

### Como funciona o CI/CD?

Pipeline em `.github/workflows/ci.yml` (GitHub Actions), disparado em
`push`/`pull_request` para `main`, `develop`, `feature/**` e `release/**`
(mesmo padrão de branches do GitFlow usado pela equipe):

1. **Job `test`**: instala as dependências e roda `pytest tests/ -v`.
2. **Job `build-docker`**: só roda se os testes passarem (`needs: test`) e
   valida que a imagem Docker builda corretamente (`docker build`).

Isso garante que nenhum código quebrado (que falhe nos testes ou não
builde) seja mesclado em `develop`/`main`.

### Como os logs são registrados?

`src/logger.py` configura três destinos por execução:
1. **Console** — acompanhamento em tempo real.
2. **`logs/execucao_<timestamp>.log`** — log completo (dados processados,
   cálculos, divergências, erros), timestampado em `America/Manaus`.
3. **`logs/alerts.log`** — acumulativo entre execuções, só com mensagens
   de nível `CRITICAL`, para auditoria rápida de ocorrências graves.

### Como os alertas são gerados?

Via `emitir_alerta_critico` (`src/logger.py`), chamado em dois pontos:
- Sempre que um projeto é classificado como `CRITICO` na análise (ex.:
  `PROJ_REF_02`), com o motivo específico da divergência.
- Sempre que ocorre uma falha irrecuperável no pipeline (ex.: extração
  falhou e não há fallback disponível).

O alerta é logado em nível `CRITICAL`, o que o direciona automaticamente
para o `alerts.log` dedicado.

### Como funciona o Fallback?

Se a extração automatizada via GERP falhar (timeout, servidor fora do ar,
etc.), `extrair_com_fallback` (`src/extractor.py`) usa o CSV financeiro já
existente em `data/` como contingência, registrando um `WARNING` no log.
Isso garante que uma falha pontual de infraestrutura não interrompa a
geração do relatório — mas fica claro no log (e seria visível numa
auditoria) que os dados usados não vieram de uma extração automatizada
bem-sucedida naquela execução.

### Como funciona o Circuit Breaker?

Implementado em `src/circuit_breaker.py`, com os três estados clássicos do
padrão:

- **FECHADO (CLOSED)**: funcionamento normal, tenta acessar o GERP a cada
  execução.
- **ABERTO (OPEN)**: após **3 falhas consecutivas**, o circuito abre e,
  pelos próximos **60 segundos**, o robô nem tenta acessar o GERP —
  vai direto para o fallback local. Isso evita martelar um sistema que já
  está indisponível.
- **MEIO-ABERTO (HALF_OPEN)**: passado o cooldown de 60s, a próxima
  execução tem permissão para **uma** tentativa de teste. Se der certo, o
  circuito fecha de novo; se falhar, reabre e reinicia o cooldown.

O estado é persistido em `logs/circuit_breaker_state.json`, então essa
decisão é respeitada entre execuções (ex.: entre diferentes rodadas do
container), não apenas dentro de uma única execução.

Diferença para o fallback puro: o fallback decide **o que fazer quando uma
tentativa falha** (usar o arquivo local); o circuit breaker decide
**se vale a pena tentar de novo**, evitando desperdiçar tempo/recursos
tentando acessar repetidamente um sistema que está fora do ar.

### Por que a arquitetura escolhida atende ao processo?

- **Separação em módulos por responsabilidade** (`extractor`,
  `data_processor`, `report_generator`, `logger`, `circuit_breaker`)
  espelha exatamente as etapas do processo exigido (Extrair → Tratar →
  Cruzar → Analisar → Identificar divergências → Gerar relatório),
  facilitando tanto os testes isolados quanto a divisão de trabalho entre
  os 4 integrantes da equipe.
- **Configuração 100% via `.env`** atende ao requisito de configuração
  segura e execução automatizada em qualquer ambiente (dev, CI, produção).
- **Circuit Breaker + Fallback** atendem ao requisito de resiliência: o
  processo administrativo (gerar o relatório da diretoria) não pode parar
  só porque um sistema de origem está temporariamente indisponível, mas a
  equipe também não quer que o robô fique tentando indefinidamente.
- **Docker Compose com dois serviços** simula de forma realista um robô
  que depende de um sistema externo via rede, com `healthcheck` garantindo
  a ordem correta de inicialização.
- **CI/CD** garante que a arquitetura continua funcionando a cada mudança
  de código, antes de qualquer merge para `develop`/`main`.

---

## Checklist rápido para a arguição

- [x] Como o processo funciona
- [x] Qual é a regra de negócio principal
- [x] Como o robô trata erros
- [x] Como os testes foram realizados
- [x] Como o Docker foi configurado
- [x] Como funciona o CI/CD
- [x] Como os logs são registrados
- [x] Como os alertas são gerados
- [x] Como funciona o Fallback
- [x] Como funciona o Circuit Breaker
- [x] Por que a arquitetura escolhida atende ao processo

Ver também: [`DEFESA_TECNICA_EQUIPE.md`](DEFESA_TECNICA_EQUIPE.md) (defesa
organizada por responsável) e [`DEFESA_TECNICA.md`](DEFESA_TECNICA.md)
(respostas às 6 perguntas oficiais do enunciado).
