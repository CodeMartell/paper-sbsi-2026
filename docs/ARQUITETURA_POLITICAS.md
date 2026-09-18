# Arquitetura, políticas e adaptação

## Separação de responsabilidades

`extractor.py` mantém Playwright + fallback + circuit breaker. `extract_source` retorna caminho e modo (`current_extraction`, `contingency`); a função legada `extrair_com_fallback` continua retornando um caminho. Cada tentativa bem-sucedida salva metadados vinculados ao hash do CSV. Uma falha de extração usa o arquivo disponível sem afirmar que ele é atual.

`provenance.py`, `quality.py`, `pipeline.py` e `review.py` concentram preservação, validações tabulares, tempos, política temporal e histórico. `process.py` instancia schemas/leitores e chama as regras financeiras/produção de `data_processor.py`. `report_generator.py` mantém o modelo textual. `dashboard.py` lê resultados e metadados já calculados; somente agrega contagens e filtra a apresentação. Não executa cálculos financeiros.

## Tratamento explícito

| Problema | Padrão `partial` | Justificativa |
|---|---|---|
| Coluna obrigatória ausente, cabeçalhos duplicados ou fonte vazia | Bloqueia execução | Sem estrutura mínima para interpretação |
| Chave vazia/ausente/inválida | Rejeita linha | Não é possível relacionar com segurança |
| Número ausente, texto numérico inválido, infinito/NaN | Rejeita linha | Não imputar zero nem liberar indicador indefinido |
| Status obrigatório ausente | Rejeita linha | Evitar normalidade por ausência de informação |
| Duplicata idêntica em todas as colunas | Mantém primeira, rejeita cópias com registro da decisão | Evitar multiplicar peso sem perder evidência |
| Mesma chave com qualquer diferença | Rejeita todas as linhas da chave | Não escolher arbitrariamente uma versão |
| Registro válido sem contraparte válida | Preserva como sem correspondência; exclui dos cálculos | Não substituir fonte ausente por zero |
| Faturamento previsto ou unidades planejadas iguais a zero | Rejeita linha dos indicadores operacionais | Percentuais indefinidos; decisão conservadora |
| Nenhum par válido | Bloqueia execução | Ausência de base para conclusão |

`quality_mode=block` bloqueia diante de qualquer ocorrência, inclusive cópia idêntica. Em `partial`, qualquer ocorrência deixa o relatório provisório. Linhas são numeradas a partir de 1, sem cabeçalho. Os arquivos originais permanecem em `inputs`; o JSON inclui valores originais e decisões. O mesmo registro pode gerar vários problemas; contagem de ocorrências não equivale a registros rejeitados.

Por fonte: `received = valid + rejected`; `valid` significa válido internamente, ainda podendo estar sem contraparte. `unmatched` conta os válidos sem contraparte elegível. `analyzed` conta linhas efetivamente liberadas para cálculo (zero se a execução for bloqueada). Um projeto analisado usa uma linha de cada fonte, portanto somar `analyzed` das fontes não é contar projetos. Duplicatas idênticas rejeitadas também entram em `rejected`. Decisões de bloqueio geral podem reter linhas que individualmente eram válidas.

A chave admite letras ASCII, dígitos, `_`, `.` e `-`, iniciando por letra/dígito; essa é uma convenção conservadora do protótipo, configurável por `Schema.key_pattern`, não uma definição universal de projeto. Espaços nas extremidades são removidos; zeros à esquerda são preservados pelos leitores de texto. Números usam a convenção decimal do arquivo original (ponto). Formatos monetários locais exigem um leitor explícito, não adivinhação.

## Tempo e contingência

Metadados opcionais ficam ao lado de cada entrada em `<arquivo>.meta.json`:

```json
{
  "sha256": "HASH_SHA256_DO_ARQUIVO",
  "obtained_at": "2026-09-18T10:00:00+00:00",
  "reference_start": "2026-09-01T00:00:00+00:00",
  "reference_end": "2026-09-07T23:59:59+00:00",
  "reference_basis": "Período declarado pela fonte; indicar origem da informação"
}
```

Não preencha datas apenas para liberar um relatório. Metadados de arquivo cujo hash mudou são ignorados como evidência temporal. O financeiro baixado obtém a semana declarada na interface simulada. Na produção, sem intervalo explícito, a coluna `Semana` permite derivar o intervalo ISO semanal observado (UTC). Data de preservação é registrada separadamente; não é data de obtenção original nem de referência. Sem evidência, a atualidade é `unknown`. Intervalo invertido, sem fuso ou terminado no futuro também é desconhecido.

Idade = instante da execução menos fim do período, em dias de 86400 segundos. Idade maior que `max_age_days` → `stale`; no limite exato é `current`. `freshness_policy=block` impede conclusões operacionais; `provisional` permite resultados explicitamente provisórios. A política vale para todas as fontes, inclusive uma extração recém-realizada de período antigo. Referências declaradas não são verificadas externamente. Conciliação temporal por registro/semana e regras para períodos em andamento ainda exigem definição de negócio.

## Extensões simples

Para outro processo, implemente uma classe semelhante a `FinanceProduction`: `name`, `version`, dicionários `schemas` e `loaders`, e método `analyze(frames, settings)`. Injete-a em `execute(process=...)`. Um `source_provider(settings)` pode fornecer fontes como `{nome: {path, mode, metadata}}`. Os nomes precisam coincidir com os schemas. Cada leitor retorna DataFrame; cada schema declara chave, campos numéricos, textuais e denominadores. A validação comum faz a interseção das chaves elegíveis entre as fontes.

O contrato de saída atual e o relatório/dashboard são específicos de projeto financeiro/produção. Outro processo precisará adaptar o objeto retornado por `analyze` (`as_dict`), o relatório, os rótulos da interface, a versão/configuração das regras em `load_policy` e seus indicadores. Validações de domínio (faixas, estados permitidos, múltiplas semanas, chave composta, sinais negativos etc.) exigem código e testes próprios. Acrescente-as antes da análise, emitindo decisões de tratamento no mesmo contrato, sem criar uma linguagem de regras. O CLI atual instancia somente financeiro/produção.

Portanto, há pontos de extensão concretos e componentes candidatos à reutilização; não há evidência de reutilização efetiva em sourcing, materiais ou controle de ECOs. Isso exige requisitos, implementações e medições dos autores.

## Decisões a validar com o gestor

Mantiveram-se os indicadores do código original. Comparar custo com faturamento previsto não é necessariamente desvio de orçamento nem margem contábil: o significado deve ser validado. O teste de atenção usa `>=`, embora a documentação antiga dissesse apenas “acima”. O caso crítico independe do limiar percentual e usa qualquer status não vazio diferente de Normal. Status financeiro e horas são apresentados, mas não decidem a classificação. Valores negativos não foram proibidos por falta de definição de negócio. Não existe regra para consolidar várias semanas do mesmo projeto; isso hoje gera duplicatas conflitantes.

A política padrão de 14 dias, bloqueio por fonte vazia e exclusão integral dos indicadores com denominador zero são decisões conservadoras configuráveis/explicitadas, não requisitos confirmados pelo gestor. Não se imputam valores ausentes. Percentuais calculados não finitos causam falha fechada, sem liberação de resultados.

## Revisão e integridade

Ocorrências de qualidade e divergências operacionais começam pendentes. Cada registro de revisão guarda ID da ocorrência, estado, justificativa, responsável autodeclarado, data UTC e hash do resultado. SQLite usa transação e sequência local; a aplicação acrescenta eventos em vez de modificar anteriores. NORMAL não é ocorrência para revisão. A decisão humana não altera a regra nem desbloqueia publicação: corrija a fonte/política e execute novamente. Dashboard e revisão conferem hash do resultado; arquivos e manifesto continuam modificáveis por quem tem acesso ao disco.

As mensagens persistidas evitam credenciais, URLs completas e texto bruto de exceções externas. O manifesto guarda apenas tipo e etapa de falhas; a investigação detalhada pode exigir reprodução local controlada. Dados sensíveis podem existir nos artefatos de entrada e de revisão: esta proteção de logs não equivale a anonimização.
