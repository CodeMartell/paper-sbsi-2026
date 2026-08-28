
# Equipe 04 — Automação do Processo de Relatórios Administrativos

Avaliação 03 — Técnicas de Hyperautomation (Professor Moisés Levy).

Robô que executa o processo  **Extrair → Tratar → Cruzar → Analisar →
Identificar divergências → Gerar relatório** , cruzando dados financeiros
(GERP simulado) com dados de produção física real, para gerar o relatório
executivo semanal da diretoria.

## Arquitetura

```
equipe04-relatorios-administrativos/
├── src/
│   ├── config.py            # variáveis de ambiente / configuração
│   ├── logger.py            # logging estruturado + alertas críticos
│   ├── extractor.py         # automação web (Playwright) no GERP simulado
│   ├── circuit_breaker.py   # circuit breaker (protege contra falhas repetidas no GERP)
│   ├── data_processor.py    # tratar / cruzar / analisar / classificar
│   ├── report_generator.py  # preenchimento do modelo de relatório
│   └── main.py               # orquestrador do pipeline
├── tests/                    # testes pytest
├── .github/workflows/ci.yml  # pipeline CI/CD (testes + build Docker)
├── gerp_fake_server/          # "sistema GERP" simulado, servido via HTTP
├── data/                      # entrada: CSV, XLSX e modelo do relatório (volume)
├── output/                    # saída: relatórios e JSON de auditoria (volume)
├── logs/                      # execução + alertas (volume)
├── docs/DEFESA_TECNICA.md     # respostas às 6 perguntas da defesa técnica
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Como rodar (Docker — forma recomendada)

```bash
cp .env.example .env
docker compose up --build
```

O `docker compose` sobe dois serviços:

* **gerp-fake** : serve `gerp_fake_server/web/gerp_fake.html` (o "GERP" simulado) e o
  CSV de faturamento em `http://localhost:8000`.
* **robo-relatorios** : aguarda o `gerp-fake` ficar saudável, executa o robô
  (login → download → cruzamento → análise → relatório) e encerra. Os
  arquivos gerados aparecem em `./output` e `./logs` no host.

Para rodar novamente sem rebuild: `docker compose up`.

## Como rodar localmente (sem Docker)

```bash
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env   # ajuste GERP_URL para onde você servir o gerp_fake.html localmente
cd gerp_fake_server && python -m http.server 8000   # em um terminal separado
python -m src.main
```

### Ver a automação acontecendo (navegador visível)

Por padrão o Playwright roda em modo **headless** (sem interface, invisível) —
necessário para funcionar no Docker/CI, que não têm tela. Para acompanhar
visualmente o robô fazendo login e clicando em "Exportar dados" no GERP
simulado, adicione ao seu `.env` local:

```
HEADLESS=false
```

Com isso, ao rodar `python -m src.main` uma janela do Chromium abre e mostra
cada passo (com uma pequena pausa entre ações, via `slow_mo`, para dar tempo
de acompanhar). **Não defina essa variável no Docker/CI** — lá não há tela
disponível, e o `docker-compose.yml` já mantém o padrão `HEADLESS=true`
(invisível) independentemente do que estiver no seu `.env` local.

## Testes

```bash
pip install pytest
pytest tests/ -v
```

Os testes cobrem leitura dos dados, cruzamento, cálculo de desvios,
identificação de divergências (incluindo o caso crítico `PROJ_REF_02`) e
geração do relatório.

## Regras de negócio (resumo)

* **Desvio financeiro** = Custo Realizado − Faturamento Previsto (em R$ e %).
* **Desvio de produção** = Unidades Planejadas − Unidades Produzidas (em un. e %).
* **Crítico** : custo acima do previsto **e** status de produção diferente de
  "Normal" (caso do `PROJ_REF_02`).
* **Atenção** : desvio financeiro ou de produção acima do limiar configurado
  (padrão 5%, ajustável via `.env`), ou dados incompletos entre as duas fontes.
* **Normal** : dentro dos limiares esperados.

## Resiliência: Fallback + Circuit Breaker

Se a extração automatizada via GERP falhar, o robô usa o CSV local já
existente como contingência ( **fallback** ). Além disso, um **circuit
breaker** (`src/circuit_breaker.py`) evita tentativas repetidas contra um
sistema indisponível: após 3 falhas consecutivas o circuito abre por 60s
(nesse período o robô vai direto para o fallback); passado o cooldown, uma
tentativa de teste é permitida antes de fechar o circuito de novo.

## CI/CD

`.github/workflows/ci.yml` roda os testes automaticamente em todo
push/PR para `main`, `develop`, `feature/**` e `release/**`, e valida que
a imagem Docker builda corretamente antes de qualquer merge.

Detalhes completos das respostas de defesa técnica em
[`docs/DEFESA_TECNICA.md`](https://claude.ai/chat/docs/DEFESA_TECNICA.md),
[`docs/DEFESA_TECNICA_EQUIPE.md`](https://claude.ai/chat/docs/DEFESA_TECNICA_EQUIPE.md) (por
responsável) e [`docs/REVISAO_AVALIACAO03.md`](https://claude.ai/chat/docs/REVISAO_AVALIACAO03.md)
(checklist de revisão do professor).
