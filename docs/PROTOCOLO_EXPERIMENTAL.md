# Protocolo de avaliação experimental (versão 1)

## Pergunta e limites

Investigar como validação, proveniência e política temporal alteram o comportamento observável de uma automação de consolidação, em condições definidas. Separar correção de software, comportamento experimental sintético e utilidade em empresa. Este protocolo não registra tempos manuais, opiniões de gestores nem ganhos percentuais: esses dados ainda não foram coletados.

## Conjunto sintético e oráculo prévio

`src/experiments.py` define `SCENARIOS` antes da execução. `protocol.json` é gravado antes dos cenários, com expectativas, repetições, data e ambiente. As tabelas-base contêm três projetos fictícios: SYN01 NORMAL, SYN02 CRITICO (custo 110 para previsto 100 e produção Atrasado), SYN03 NORMAL. Os números são criados no próprio programa, sem dados empresariais. Datas relativas à execução mantêm cenários atuais e vencidos reproduzíveis como condições; as datas concretas ficam preservadas em cada repetição.

| Cenário | Injeção | Comportamento esperado |
|---|---|---|
| normal | Nenhuma | 3 projetos analisados, concluído |
| source_unavailable | Exceção na aquisição externa | Fallback real, fonte marcada contingência, 3 projetos, concluído se atual |
| stale_contingency | Fallback com fim do período há 30 dias | 3 projetos, provisório, fonte stale |
| unknown_contingency | Fallback sem período | 3 projetos, provisório, fonte unknown |
| missing_column | Remove Horas_Faturadas | Bloqueado, zero projetos liberados |
| invalid_numeric | Custo de SYN01 vira texto inválido | SYN01 excluído; 2 projetos, provisório |
| missing_key | Chave financeira de SYN01 vazia | Linha rejeitada; contraparte sem correspondência; 2 projetos |
| conflicting_duplicates | Segunda versão de SYN01 com custo 999 | Ambas as versões rejeitadas; 2 projetos |
| unmatched | Remove produção de SYN01 | Sem correspondência; 2 projetos |
| zero_denominator | Previsto de SYN01 igual a zero | Indicador não calculado, SYN01 excluído; 2 projetos |

O oráculo contém também as identidades esperadas das ocorrências secundárias (ex.: produção válida cuja contraparte financeira foi rejeitada). Não é gerado a partir das regras calculadas pelo sistema. O detector compara tuplas `(fonte, tipo, chave, coluna)`; múltiplos problemas idênticos nessa unidade são contados uma vez. Essa escolha não mede cobertura por célula em grandes bases.

## Execução e métricas

`python -m src.experiments --repetitions 3` gera diretório UUID, protocolo, entradas de cada cenário e resultados independentes. Não agrega estatísticas de ganho. Falha de aquisição é uma injeção explícita com mock na fronteira de I/O; validação, fallback, circuit breaker, regras e persistência são reais. Leitura externa/latência de navegador não entram nesse cenário. Ordem atual fixa; futuros estudos devem contrabalançar a ordem, aquecimento e aprendizagem.

- **Duração**: relógio monotônico, segundos do pipeline (configuração até relatório, antes de gravar os dois JSON finais); etapas têm início/fim UTC e duração própria. Preparação do conjunto e injeção não fazem parte dessa medida. Não equivale a tempo de trabalho humano.
- **Registros recebidos**: soma de linhas das duas fontes, incluindo duplicatas; **projetos analisados**: quantidade de classificações operacionais liberadas.
- **Projetos tratados corretamente / 3**: para cada projeto-base, rótulo correto quando elegível ou ausência de liberação quando o oráculo prevê exclusão/bloqueio. Ausência indevida de projeto elegível é incorreta. Essa métrica avalia decisão de tratamento, não apenas acerto de classificação. Sua qualidade deve ser lida junto com a métrica de problemas detectados.
- **Problemas esperados, detectados, verdadeiros alertas, falsos alertas, alertas perdidos**: cardinalidade dos conjuntos do oráculo, detector, interseção, detector menos oráculo e oráculo menos detector. Não confundir alertas de qualidade com divergências operacionais.
- **Classificações incorretas liberadas**: projeto excluído que aparece no resultado ou rótulo operacional diferente do oráculo.
- **Erros silenciosos**: classificações incorretas liberadas + problemas esperados ausentes quando há liberação. Pode contar mais de um erro por projeto; não é uma taxa por linha. Falhas técnicas bloqueadas são registradas no estado e em `passed`, não mascaradas como sucesso por terem zero erros silenciosos.
- **passed**: estado, conjunto de problemas, dicionário de classificações e uso de contingência coincidem integralmente com expectativas.

Para relatar precisão = verdadeiros alertas / detectados; sensibilidade = verdadeiros alertas / esperados. Se denominador zero, registrar **não aplicável**, nunca 100% por convenção oculta. Informar contagens brutas e número de repetições. Para duração, guardar medições individuais e só depois calcular mediana/dispersão com desenho e ambiente descritos.

## Comparação pareada futura: manual × original × aprimorado

1. Congelar a baseline no commit de `docs/BASELINE.json`, preservando histórico e alterações atuais. Criar uma cópia isolada usando `git archive 7e1768daf5d4081450ee5d6e904c8c0d3a5a983d --output output/baseline-original.zip`; extrair em diretório novo. Não executar reset sobre a versão aprimorada.
2. Congelar também a versão aprimorada (commit, diff se houver, hashes e dependências). Não basta registrar HEAD se o código está modificado. Os manifestos já guardam hashes de fontes e indicador de alterações locais; arquive código/diff autorizado para a pesquisa.
3. Preparar entradas equivalentes: mesmos bytes CSV/XLSX, hashes, metadados de referência e enunciado dos indicadores. Copiar em cada ambiente isolado e fornecer os mesmos arquivos ao procedimento manual. Registrar data da medição, máquina, versões, experiência dos participantes e ordem. Não usar extrações de momentos diferentes como se fossem pares.
4. Definir e revisar o oráculo por pessoas que conheçam o processo antes da avaliação. Não usar as próprias saídas do protótipo como verdade de referência. Validar significado de indicadores, chaves, ECOs e critérios dos outros projetos separadamente.
5. Definir tarefas equivalentes: identificar divergências, identificar dados não interpretáveis, explicar proveniência e concluir ou recusar publicação. Guardar outputs manuais e automáticos, inclusive erros/crashes, sem corrigir a baseline para favorecer a comparação. A baseline pode não expressar estados de qualidade; registrar como ausência de capacidade, não preencher por inferência favorável.
6. Para manual, coletar início/fim observados e correções/intervenções com consentimento quando aplicável; usar a ficha CSV vazia fornecida. Não extrapolar do tempo de máquina. Contrabalançar ordem e controlar aprendizagem; repetir cenários segundo plano amostral definido antes da coleta.
7. Avaliar acertos, exclusões indevidas, falsos alertas, erros silenciosos, tempo e capacidade de explicar origem contra o mesmo oráculo. Separar desempenho técnico de percepção do gestor. Qualquer estudo com participantes/dados empresariais depende das autorizações e procedimentos institucionais pertinentes ao contexto real.
8. Relatar limitações: base pequena e sintética, cenários isolados, dependência do oráculo, ordem fixa no runner atual, ausência de validação externa e de implantação nos outros processos. Resultados não demonstram impacto empresarial, generalização ou reutilização nos três projetos.

A ficha `docs/coleta_comparacao.csv` é apenas um cabeçalho, sem observações inventadas. `metodo` deve ser manual/original/aprimorado. Guarde a saída original para que outro avaliador possa refazer a pontuação.
