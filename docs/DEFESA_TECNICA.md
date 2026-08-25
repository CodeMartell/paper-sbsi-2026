# Defesa Técnica — Equipe 04 (Automação do Processo de Relatórios Administrativos)

## 1. Como os dados financeiros e operacionais são cruzados?

O robô lê o CSV financeiro (`GERP_faturamento_bruto.csv`, baixado via automação
web) com `pandas.read_csv` e a planilha de produção (`producao_fisica_real.xlsx`)
com `pandas.read_excel` (função `extrair_dados_financeiros` /
`extrair_dados_producao` em `src/data_processor.py`). Após tratamento (tipos
numéricos, remoção de espaços e duplicatas — `tratar_dados`), os dois conjuntos
são cruzados por `pandas.merge` usando `Codigo_Projeto` como chave, com
`how="outer"` e `indicator=True` (`cruzar_dados`). O `outer join` garante que
nenhum projeto seja "perdido" silenciosamente: projetos presentes em apenas uma
das fontes também aparecem no resultado, marcados para tratamento como
divergência de integração.

## 2. Como o robô identifica uma divergência?

Cada projeto cruzado passa pela função `_classificar` (`src/data_processor.py`),
que aplica três regras, em ordem de prioridade:

1. **Crítico**: custo realizado maior que o faturamento previsto **e** status de
   produção diferente de "Normal" — exatamente o padrão do caso `PROJ_REF_02`
   descrito na avaliação.
2. **Atenção**: desvio financeiro desfavorável (custo acima do previsto) ou
   desvio de produção (produzido abaixo do planejado) além do limiar
   configurável (`LIMIAR_DESVIO_FINANCEIRO_ATENCAO` / `LIMIAR_DESVIO_PRODUCAO_ATENCAO`,
   padrão 5%), ou status de produção diferente de "Normal".
3. **Normal**: nenhum dos casos acima.

Projetos sem correspondência em uma das fontes (ex.: presente no financeiro mas
ausente na produção) são automaticamente marcados como "Atenção", com o motivo
"sem dados de produção/financeiro correspondentes".

## 3. Como é calculado o desvio?

- **Desvio financeiro (R$)** = `Custo_Realizado - Faturamento_Previsto`
- **Desvio financeiro (%)** = `Desvio financeiro (R$) / Faturamento_Previsto × 100`
- **Desvio de produção (unidades)** = `Unidades_Planejadas - Unidades_Produzidas`
- **Desvio de produção (%)** = `Desvio de produção (un.) / Unidades_Planejadas × 100`

Para o `PROJ_REF_02`: desvio financeiro = R$ 850.000 − R$ 800.000 = **R$ 50.000
(+6,25%)**; desvio de produção = 1.500 − 1.200 = **300 unidades (+20%)**.

## 4. Por que o PROJ_REF_02 deve gerar um alerta?

Porque combina duas condições de risco simultâneas: o custo realizado
(R$ 850.000,00) **supera** o faturamento previsto (R$ 800.000,00) — ou seja, o
projeto já está operando com margem negativa — **e** o status de produção está
"Atrasado", indicando que o cronograma físico também não está sendo cumprido.
A combinação de estouro financeiro com atraso operacional é o cenário de maior
risco para a diretoria (perda financeira que tende a se agravar, já que a
entrega também está atrasada), por isso é tratado como **ocorrência crítica de
negócio** e dispara um alerta em nível `CRITICAL` (`emitir_alerta_critico`,
registrado em `logs/alerts.log`), além de ser destacado na seção de
divergências do relatório final.

## 5. Como o relatório é gerado?

A função `gerar_relatorio` (`src/report_generator.py`) lê o modelo
`modelo_relatorio_final_diretoria.txt` e substitui os placeholders
(`{{SEMANA}}`, `{{RESUMO}}`, `{{INDICADORES}}`, `{{DIVERGENCIAS}}`,
`{{VALIDACAO_HUMANA}}`) por conteúdo calculado a partir da lista de projetos
analisados: contagem de projetos por classificação, indicadores por projeto,
lista de divergências e uma recomendação de validação humana (destacando os
projetos críticos, quando existirem). O resultado é salvo em
`output/relatorio_final_diretoria_<timestamp>.txt`, com o timestamp calculado
no fuso `America/Manaus`.

## 6. Como a equipe garante rastreabilidade dos dados?

- **Logs completos por execução** (`logs/execucao_<timestamp>.log`), com dados
  processados, cálculos de desvio, divergências identificadas e erros,
  timestampados no fuso `America/Manaus`.
- **Log dedicado de alertas críticos** (`logs/alerts.log`), acumulativo entre
  execuções, para auditoria rápida de ocorrências críticas.
- **Saída estruturada em JSON** (`output/resultado_analise_<timestamp>.json`)
  com todos os campos de cada projeto (valores brutos, desvios calculados e
  classificação final), permitindo auditoria posterior e reprocessamento sem
  depender do texto do relatório.
- **Testes automatizados (pytest)** que fixam o comportamento esperado do
  cálculo de desvio e da classificação, funcionando como documentação viva das
  regras de negócio.
- Cada execução gera arquivos com timestamp próprio (relatório, JSON e log),
  nunca sobrescrevendo execuções anteriores.
