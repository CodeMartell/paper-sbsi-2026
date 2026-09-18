# Avaliação multiprocesso sintética

Este artefato avalia a mesma infraestrutura de validação, proveniência, preservação e classificação em três instanciações declaradas. Ele não afirma que os cenários descrevem sourcing, materiais ou ECOs reais, nem que os autores implementaram esses outros projetos.

## Instanciações e fronteiras semânticas

| Instanciação | Chave | Fonte de referência | Fonte observada | Regra sintética |
|---|---|---|---|---|
| `finance-production` | `Codigo_Projeto` | faturamento/custo | produção | regra existente do projeto |
| `sourcing-synthetic` | `Solicitacao_ID` | `Valor_Referencia` | `Valor_Proposto` | desvio ≥ limiar e estado atípico → crítico |
| `materials-synthetic` | `Material_ID` | `Quantidade_Planejada` | `Quantidade_Registrada` | mesma forma matemática, com rótulos próprios |

Os nomes sourcing e materiais apenas ajudam a distinguir os conjuntos hipotéticos. `Valor_Referencia`, `Valor_Proposto`, `Quantidade_Planejada`, `Quantidade_Registrada` e seus estados foram definidos exclusivamente para este experimento. Não inferem cadastros, métricas, políticas, chaves ou responsabilidades dos projetos dos autores. ECO não foi modelado.

## Perguntas de pesquisa

- **RQ1.** Em quais falhas de entrada a camada explícita de qualidade evita a liberação de classificações operacionais indevidas?
- **RQ2.** A infraestrutura comum mantém o comportamento esperado quando os esquemas e regras de reconciliação variam entre instâncias sintéticas?
- **RQ3.** Como a versão aprimorada se comporta, nos mesmos cenários financeiros/produção, em relação ao código histórico identificado pela baseline?

Não há RQ sobre tempo humano, aceitação de gestores ou impacto organizacional, pois não foram coletados participantes ou dados empresariais.

## Desenho executável

```powershell
.\.venv\Scripts\python.exe -m src.research_evaluation --repetitions 3
```

`src/research_evaluation.py` registra um protocolo antes das execuções, cria entradas e metadados sintéticos, executa o pipeline real e preserva todos os artefatos. Em finanças/produção, carrega o conteúdo de `src/data_processor.py` do commit baseline `7e1768daf5d4081450ee5d6e904c8c0d3a5a983d` diretamente do Git. Não reimplementa a baseline por aproximação.

Cada uma das três instanciações usa seis condições: normal, número inválido, chave ausente, duplicata conflitante, registro sem correspondência e denominador zero. O oráculo é especificado pelo script antes do resultado e identifica tanto a classificação esperada dos três itens-base quanto as ocorrências de qualidade esperadas. Cada condição é repetida três vezes.

Para a baseline, a ausência de uma estrutura de ocorrência de qualidade é observada como ausência de alerta. A baseline não é aplicada às duas instanciações novas, pois elas não existiam no projeto original. Esta é uma comparação histórica pareada apenas para a instanciação financeira/produção.

## Resultados observados

O diretório completo da última execução está em `output/research-evaluation/c4ee18b06193476980e9c6f20dd4e37e/`; o resumo versionado está em [research_summary.csv](evidence/research_summary.csv). Cada linha de resumo agrega 18 execuções: seis condições × três repetições. `base_projects` é sempre 54 (três itens-base por execução), inclusive quando um item deve ser retido.

| Processo / método | Itens tratados corretamente | Alertas verdadeiros | Alertas perdidos | Classificações indevidas liberadas | Erros silenciosos |
|---|---:|---:|---:|---:|---:|
| Financeiro/produção aprimorado | 54/54 | 27 | 0 | 0 | 0 |
| Financeiro/produção baseline | 39/54 | 0 | 27 | 15 | 45 |
| Sourcing sintético aprimorado | 54/54 | 27 | 0 | 0 | 0 |
| Materiais sintético aprimorado | 54/54 | 27 | 0 | 0 | 0 |

“Erro silencioso” é a soma de classificações liberadas incorretamente e problemas esperados ausentes quando uma execução liberou resultados. Isso pode contar mais de um erro em uma execução; não é uma taxa de falhas por registro. Para a baseline, as 15 classificações indevidas e 27 problemas não detectados formam 45 eventos nessa definição. Como não houve alerta falso ou perdido na versão aprimorada, precisão e sensibilidade são 1,0 **somente nesses 27 alertas sintéticos** por processo; não devem ser apresentadas como precisão do sistema em ambiente empresarial.

## Comparação manual: preparada, não simulada como humana

O protocolo manual está em [coleta_comparacao.csv](coleta_comparacao.csv). Ele permite coletar, para as mesmas entradas preservadas, início/fim, decisões, alertas e justificativas de uma pessoa. Não há linhas de resultado humano: produzir números sem participantes seria fabricação de evidência. O oráculo do experimento é uma adjudicação de referência codificada, não uma execução manual e não mede esforço ou julgamento humano.

Antes da coleta real, os autores devem: definir os critérios junto ao responsável do processo; obter as autorizações apropriadas; atribuir cenários e ordem; preservar saídas; e registrar desistências, correções e divergências. A versão original e a aprimorada já podem ser avaliadas com o mesmo conjunto de entradas financeiras; as outras duas instanciações precisam de requisitos reais antes de qualquer comparação humana.

## Ameaças à validade

- **Construto:** os cenários são pequenos, tabulares e construídos pelos autores; não cobrem semântica, chaves compostas, múltiplos períodos ou políticas empresariais reais.
- **Interna:** o oráculo e as regras foram definidos pela mesma equipe que desenvolveu o artefato. Revisão independente do oráculo reduziria esse risco.
- **Conclusão:** três repetições reduzem variação de execução, mas não criam poder estatístico para inferir desempenho em populações de dados.
- **Externa:** os resultados não demonstram reutilização em sourcing, materiais ou ECOs reais, nem ganhos organizacionais.
- **Comparação:** a baseline representa um commit histórico recuperado do repositório; dependências atuais são usadas para executá-la. O manifesto e o commit permitem auditoria, mas não reproduzem o ambiente original de 2026 por completo.
