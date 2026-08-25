# Defesa Técnica — Equipe 04 (Automação do Processo de Relatórios Administrativos)

Avaliação 03 — Técnicas de Hyperautomation (Professor Moisés Levy)

Este documento organiza a defesa técnica por responsável, para que cada
integrante consiga explicar sua parte da solução com segurança. No fim, as
6 perguntas oficiais da avaliação (item 5) aparecem respondidas de forma
consolidada.

---

## Pessoa 1 — Automação / GERP
**Responsabilidade:** acesso ao sistema simulado, login e extração/download dos dados.
**Arquivo principal:** `src/extractor.py`

### O que foi feito
- Uso do **Playwright** (Chromium headless) para abrir o `gerp_fake.html`,
  preencher usuário e senha (`GERP_USER` / `GERP_PASSWORD`, vindos do `.env`)
  e clicar em "Entrar".
- Após o login, o robô espera o painel (`#app`) ficar visível e clica em
  "Exportar dados", capturando o evento de download disparado pelo
  JavaScript da página fake (`page.expect_download`).
- O arquivo baixado é salvo em `data/GERP_faturamento_bruto.csv`.
- **Mecanismo de contingência (`extrair_com_fallback`)**: se a automação
  web falhar por qualquer motivo (timeout, servidor fora do ar), o robô
  registra um aviso no log e usa o CSV local já existente, evitando que
  uma falha de infraestrutura pare todo o pipeline.

### Perguntas que essa pessoa deve saber responder
- Por que Playwright e não outra ferramenta? (framework de automação de
  navegador moderno, headless, mesma linguagem — Python — do restante do
  robô, requisito 4.1 permite "ferramenta de livre escolha").
- Como o robô sabe que o login deu certo? (espera o elemento `#app` ficar
  visível — se as credenciais estiverem erradas, o `alert()` da página
  aparece e o `#app` nunca fica visível, gerando timeout).
- O que acontece se o GERP simulado estiver fora do ar? (fallback para o
  arquivo local, com aviso no log — não é um erro silencioso).

---

## Pessoa 2 — Processamento dos dados
**Responsabilidade:** ler CSV e Excel, cruzar as informações, calcular os
desvios e identificar divergências (caso crítico do PROJ_REF_02).
**Arquivo principal:** `src/data_processor.py`

### O que foi feito
- **Leitura**: `extrair_dados_financeiros` lê o CSV (separador `;`) com
  pandas; `extrair_dados_producao` lê a aba "Producao" do Excel.
- **Tratamento**: `tratar_dados` normaliza tipos numéricos, remove espaços
  em branco nos códigos de projeto e elimina duplicatas.
- **Cruzamento**: `cruzar_dados` faz um `outer join` pandas por
  `Codigo_Projeto`, garantindo que nenhum projeto seja perdido — mesmo os
  que só aparecem em uma das duas fontes.
- **Cálculo de desvios**:
  - Desvio financeiro (R$) = Custo Realizado − Faturamento Previsto
  - Desvio financeiro (%) = desvio ÷ Faturamento Previsto × 100
  - Desvio de produção (un.) = Unidades Planejadas − Unidades Produzidas
  - Desvio de produção (%) = desvio ÷ Unidades Planejadas × 100
- **Classificação** (`_classificar`):
  - **CRÍTICO**: custo realizado > faturamento previsto **e** status de
    produção diferente de "Normal" — é exatamente o caso do
    `PROJ_REF_02` (previsto R$ 800.000, custo R$ 850.000, status
    "Atrasado" → desvio financeiro +6,25%, desvio de produção +20%).
  - **ATENÇÃO**: desvio financeiro desfavorável ou desvio de produção
    acima do limiar configurável (padrão 5%), ou dados incompletos entre
    as duas fontes.
  - **NORMAL**: dentro dos limiares esperados.

### Perguntas que essa pessoa deve saber responder
- Por que usar `outer join` e não `inner join`? (inner join descartaria
  silenciosamente projetos sem par nas duas bases; outer join expõe isso
  como uma divergência de integração, o que é mais seguro para auditoria).
- Por que o PROJ_REF_02 é crítico e não apenas "atenção"? (porque combina
  as duas condições de risco ao mesmo tempo: estouro de custo **e**
  atraso de produção — um problema financeiro que tende a se agravar
  porque a entrega física também está atrasada).
- Um desvio financeiro favorável (custo bem abaixo do previsto) também
  gera alerta? (não — só desvios desfavoráveis, custo acima do previsto
  ou produção abaixo do planejado, disparam "atenção"/"crítico").

---

## Pessoa 3 — Relatório, logs e alertas
**Responsabilidade:** gerar o relatório final, registrar os logs do
processamento e implementar o alerta para situações críticas.
**Arquivos principais:** `src/report_generator.py`, `src/logger.py`

### O que foi feito
- **Relatório**: `gerar_relatorio` lê o modelo
  `modelo_relatorio_final_diretoria.txt` e substitui os placeholders
  (`{{SEMANA}}`, `{{RESUMO}}`, `{{INDICADORES}}`, `{{DIVERGENCIAS}}`,
  `{{VALIDACAO_HUMANA}}`) com o conteúdo calculado a partir da lista de
  projetos analisados. O arquivo final é salvo com timestamp em
  `output/relatorio_final_diretoria_<timestamp>.txt`.
- **Logs**: `get_logger` configura três destinos —
  1. console (acompanhamento em tempo real);
  2. `logs/execucao_<timestamp>.log` (log completo da execução: dados
     processados, cálculos, divergências, erros);
  3. `logs/alerts.log` (acumulativo entre execuções, só com alertas
     `CRITICAL`, para auditoria rápida).
  Todos os timestamps respeitam o fuso `America/Manaus` exigido na
  avaliação (formatter customizado com `zoneinfo`).
- **Alertas**: `emitir_alerta_critico` é chamado sempre que um projeto é
  classificado como `CRITICO` (ex.: PROJ_REF_02) e também em caso de erro
  irrecuperável no pipeline (ex.: falha total na extração).
- Também é gerado um **JSON estruturado**
  (`output/resultado_analise_<timestamp>.json`) com todos os campos de
  cada projeto, para rastreabilidade/auditoria fora do texto do relatório.

### Perguntas que essa pessoa deve saber responder
- Como o gestor sabe que existe um caso crítico sem ler o log inteiro?
  (o `alerts.log` é dedicado só a alertas `CRITICAL`, e o próprio
  relatório final também lista as divergências na seção
  "Divergências").
- Por que gerar um JSON além do `.txt`? (o `.txt` é para leitura humana;
  o JSON preserva todos os valores brutos e calculados, permitindo
  reprocessamento ou auditoria automatizada depois).
- Por que os logs são timestampados por execução em vez de um arquivo
  único? (evita sobrescrever o histórico — cada execução fica rastreável
  separadamente).

---

## Pessoa 4 — Docker e testes
**Responsabilidade:** Dockerfile, Docker Compose, volumes, variáveis de
ambiente e testes com pytest. Também apoio na integração final.
**Arquivos principais:** `Dockerfile`, `docker-compose.yml`, `.env.example`, `tests/`

### O que foi feito
- **Dockerfile**: baseado na imagem oficial `mcr.microsoft.com/playwright/python`
  (já traz o Chromium instalado, evitando downloads extras). Define
  timezone `America/Manaus`, roda com usuário não-root (`robo`) por
  segurança, instala as dependências do `requirements.txt` e usa
  `ENTRYPOINT ["python", "-m", "src.main"]`.
- **Docker Compose**: dois serviços —
  - `gerp-fake`: serve o `gerp_fake_server/` (HTML + CSV) via
    `python -m http.server`, com `healthcheck` para garantir que só
    sobe o robô depois que o "GERP" estiver respondendo.
  - `robo-relatorios`: builda a imagem do robô, depende do `gerp-fake`
    estar saudável (`depends_on: condition: service_healthy`), recebe as
    variáveis de ambiente via `.env` e monta os **volumes**
    `data/`, `output/` e `logs/` para persistir os arquivos no host.
- **Variáveis de ambiente**: tudo sensível/configurável (URL do GERP,
  credenciais, caminhos, timezone, limiares de desvio) vem do `.env`,
  nunca hardcoded no código (`src/config.py`).
- **Testes (pytest)**: 12 testes em `tests/`, cobrindo:
  - leitura do CSV e do Excel;
  - tratamento (normalização de tipos, remoção de duplicatas);
  - cruzamento (inclusive projetos sem correspondência);
  - cálculo de desvios financeiros e de produção;
  - classificação correta do PROJ_REF_02 como crítico e dos demais como
    normais;
  - geração do relatório (todos os placeholders substituídos).

### Perguntas que essa pessoa deve saber responder
- Por que dois containers (`gerp-fake` e `robo-relatorios`) e não um só?
  (simula de forma mais realista um robô que acessa um sistema externo
  via rede, e permite o `healthcheck` garantir a ordem de subida).
- Por que usar volumes em vez de copiar os dados para dentro da imagem?
  (permite trocar os dados de entrada e inspecionar as saídas sem
  rebuildar a imagem — mais próximo de um cenário de produção).
- Como os testes garantem que o caso do PROJ_REF_02 nunca "quebra" sem
  ninguém perceber? (há um teste específico,
  `test_projeto_ref_02_e_classificado_como_critico`, que falha
  imediatamente se a lógica de classificação for alterada de forma que
  esse caso pare de ser crítico).

---

## Consolidado — respostas às 6 perguntas oficiais da avaliação

**1. Como os dados financeiros e operacionais são cruzados?**
Via `pandas.merge` (outer join) pela chave `Codigo_Projeto`, depois de
lidos (CSV/Excel) e tratados (tipos e duplicatas). *(Pessoa 2)*

**2. Como o robô identifica uma divergência?**
Pela função `_classificar`, que aplica as regras de CRÍTICO / ATENÇÃO /
NORMAL descritas acima. *(Pessoa 2)*

**3. Como é calculado o desvio?**
Desvio financeiro = Custo Realizado − Faturamento Previsto (R$ e %);
desvio de produção = Unidades Planejadas − Unidades Produzidas (un. e %).
*(Pessoa 2)*

**4. Por que o PROJ_REF_02 deve gerar um alerta?**
Porque o custo realizado (R$ 850.000) supera o faturamento previsto
(R$ 800.000) **e** o status de produção é "Atrasado" ao mesmo tempo —
combinação de risco financeiro e operacional. *(Pessoas 2 e 3)*

**5. Como o relatório é gerado?**
Preenchendo os placeholders do modelo `modelo_relatorio_final_diretoria.txt`
com os dados calculados, salvo com timestamp em `output/`. *(Pessoa 3)*

**6. Como a equipe garante rastreabilidade dos dados?**
Logs por execução + log dedicado de alertas críticos + JSON estruturado
de auditoria + testes automatizados que documentam o comportamento
esperado das regras de negócio. *(Pessoas 3 e 4)*
