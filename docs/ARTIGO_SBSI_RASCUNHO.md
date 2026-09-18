# Integração rastreável de dados financeiros e de produção por RPA para apoio à decisão organizacional

> **Status:** rascunho de pesquisa, não pronto para submissão. Remover nomes, instituições, URLs identificadoras e referências ao repositório durante a preparação da versão duplamente anônima. Confirmar integralmente a chamada e o template SBC vigente antes de exportar PDF.

## Structured abstract

**Research Context.** Organizational information systems integrate data from distinct operational sources to support managerial processes. However, source failures, incomplete fields, duplicates, and uncertainty about the reference period can transform invalid inputs into apparently valid indicators.

**Scientific and/or Practical Problem.** RPA-supported data integration can silently discard, impute, or merge problematic records. This can release financial and production classifications that are not supported by sufficient evidence and cannot be independently explained or reproduced.

**Proposed Solution and/or Analysis.** We designed an RPA artifact for traceable financial and production data integration. It preserves inputs, associates hashes and temporal metadata with sources, validates schemas and records before business rules, separates data-quality issues from operational classifications, and stores human-review events separately from automatic results.

**Related IS Theory.** The study draws on data quality as a multidimensional construct, data provenance, and Design Science Research in Information Systems.

**Research Method.** A design-science evaluation uses a predeclared oracle and three synthetic two-source process instances. Six controlled input conditions are repeated three times. The financial/production instance is also compared with the identified historical implementation using equivalent inputs.

**Summary of Results.** In 54 synthetic base items per enhanced instance, the artifact handled all items according to the oracle and released no silent-error event under the study definition. In the financial/production comparison, the historical implementation handled 39 of 54 base items according to the oracle, missed 27 expected quality alerts, and produced 45 silent-error events. These results apply only to the constructed scenarios.

**Contributions and Impact to IS area.** The work offers a reproducible RPA artifact and evaluation protocol for treating data quality and source freshness as first-class conditions in organizational information systems. It delineates the evidence required before claims of organizational impact, decision improvement, or cross-domain reuse.

## 1. Introdução

Organizações usam dados financeiros e de produção para acompanhar custos, faturamento, planejamento e realização. Em muitos processos, esses dados são produzidos por fontes distintas e precisam ser integrados antes de formar indicadores e exceções para gestores. A Robotic Process Automation (RPA) permite automatizar extração e movimentação dessas informações, mas a automação não torna, por si só, o resultado confiável para uso organizacional.

Um cálculo pode estar aritmeticamente correto embora seus dados de entrada estejam incompletos, duplicados, desatualizados ou sem correspondência entre fontes. Se uma automação converte valor desconhecido em zero, elimina registros silenciosamente ou usa uma junção que oculta uma contraparte ausente, a classificação produzida pode parecer normal sem que haja evidência suficiente. Esse risco é organizacional: uma pessoa pode tomar uma decisão ou encerrar uma atividade a partir de informação que o próprio sistema não consegue explicar.

Este artigo apresenta um artefato de RPA para integração rastreável de dados financeiros e de produção. O artefato automatiza a extração de uma fonte financeira simulada, integra-a a uma fonte de produção, valida a qualidade antes de aplicar regras de negócio e apresenta resultados, limitações e evidências para a conferência gerencial. O objetivo não é substituir o julgamento do gestor: é reduzir o risco de uma classificação automática ser interpretada como evidência suficiente quando o dado não permite esse julgamento.

As perguntas de pesquisa são:

- **RQ1.** Em quais condições de falha de entrada a validação explícita impede a liberação de classificações operacionais indevidas?
- **RQ2.** Como proveniência, hashes e política de atualidade contribuem para a explicabilidade e a reprodução dos resultados de integração financeira e de produção?
- **RQ3.** Como a versão aprimorada se comporta, nas mesmas entradas sintéticas, em comparação à implementação histórica do fluxo financeiro/produção?

O estudo não afirma melhoria de produtividade, redução de custos, melhor decisão humana ou impacto organizacional. Essas conclusões exigem avaliação com participantes e dados autorizados de uma organização. As instanciações sintéticas adicionais existem apenas para examinar a infraestrutura comum; elas não definem requisitos de sourcing, materiais ou ECOs.

## 2. Fundamentação e trabalhos relacionados

A qualidade de dados é mais ampla que precisão: consumidores avaliam diversas dimensões para decidir se os dados são adequados ao uso [Wang e Strong, 1996]. Pipino, Lee e Wang [2002] defendem métricas úteis às organizações, em vez de medidas criadas apenas ad hoc. Neste trabalho, colunas obrigatórias, chaves válidas, números finitos conversíveis, duplicatas, correspondência entre fontes e denominadores válidos operacionalizam uma política limitada e explícita de qualidade. A política não pretende cobrir todas as dimensões de qualidade de dados.

Proveniência trata da linhagem e do contexto que tornam um resultado inspecionável. Simmhan, Plale e Gannon [2005] discutem proveniência em dados científicos; Cheney, Chiticariu e Tan [2009] tratam de por que, como e onde representá-la em bases de dados. O artefato adapta essa preocupação a um contexto organizacional local ao preservar cópias das fontes, hashes, modo de obtenção, intervalo de referência, configuração e duração das etapas. Um hash detecta alteração em relação ao manifesto preservado, mas não autentica a origem nem torna arquivos locais imutáveis.

Hevner et al. [2004] apresentam Design Science Research como construção e avaliação de artefatos inovadores na interseção entre pessoas, organizações e tecnologia. O artefato é avaliado como uma instanciação de Design Science: responde a um problema definido, explicita requisitos e comportamento e é avaliado contra um oráculo predefinido. A avaliação é técnica e sintética; não é estudo comportamental ou de campo.

## 3. Artefato de RPA para integração organizacional

O artefato organiza cada execução em configuração, aquisição, validação, análise e relatório. A RPA acessa o GERP simulado por Playwright, realiza login e obtém o CSV financeiro. Em caso de indisponibilidade, usa o fallback existente com circuit breaker. A fonte de produção é lida de planilha local. Cada execução recebe UUID, preserva as entradas e seus hashes, registra política e identidade do código e gera manifesto e resultado estruturado.

A porta de qualidade é executada antes das regras financeiras e de produção. Esquema ausente, fonte vazia e ausência de pares elegíveis bloqueiam a execução. Chaves inválidas, números desconhecidos ou não finitos, texto obrigatório ausente, denominador zero, duplicatas conflitantes e registros sem correspondência geram decisões explícitas e preservam os valores originais no ledger. Conforme a política, a execução com problemas pode ser provisória ou bloqueada.

A atualidade usa intervalo de referência, não a data de modificação do arquivo. Um metadado lateral associa `obtained_at`, `reference_start`, `reference_end` e a base da referência ao hash da fonte. Um download atual de período antigo continua desatualizado. Evidência temporal ausente produz o estado explícito `unknown`. Relatório textual, JSON e dashboard apresentam essas condições ao gestor.

O dashboard consome resultados armazenados, sem recalcular regras financeiras ou de produção. Ele apresenta fontes, atualidade, divergências operacionais, problemas de qualidade, valores utilizados e decisões de tratamento. Um revisor pode registrar ocorrência pendente, confirmada ou descartada com justificativa e identidade autodeclarada. Isso é histórico local de aplicação, não autenticação, assinatura digital ou trilha inviolável.

Dois pontos de extensão são usados na avaliação: um esquema declara chave, campos numéricos, campos textuais e denominadores; um processo declara leitores, regras e geração de relatório. Finanças/produção permanece a instância específica de negócio original. As novas instâncias usam rótulos e parâmetros próprios, mas compartilham infraestrutura de qualidade, proveniência, política, preservação e revisão.

## 4. Método de avaliação

O estudo usa avaliação controlada com dados sintéticos claramente identificados. A instanciação financeira/produção contém três projetos sintéticos. O cenário normal produz dois projetos normais e um crítico segundo as regras existentes. Cinco condições de falha alteram uma entrada: número inválido, chave ausente, duplicata conflitante, registro sem correspondência e denominador zero. Os eventos de qualidade e as classificações elegíveis esperadas são definidos no código antes de qualquer execução. Cada condição é executada três vezes.

As métricas são itens-base tratados corretamente, alertas de qualidade verdadeiros/falsos/perdidos, classificações operacionais indevidas liberadas e eventos de erro silencioso. Um item-base é tratado corretamente quando recebe a classificação esperada, se elegível, ou é retido quando o oráculo exige retenção. Evento de erro silencioso é a soma de uma classificação incorreta liberada e de um problema de qualidade esperado que não foi detectado em execução que libera saída. É contagem de eventos, não probabilidade ou número de pessoas afetadas.

Para a RQ3, o executor carrega via Git o `data_processor.py` histórico do commit `7e1768daf5d4081450ee5d6e904c8c0d3a5a983d` e o aplica aos DataFrames financeiros e de produção equivalentes. A versão original não possui modelo de evento de qualidade; seu conjunto de problemas detectados é, portanto, vazio. A comparação limita-se a essa instância histórica. As duas extensões sintéticas não possuem baseline porque não existiam no repositório original.

## 5. Resultados

Em 18 execuções da versão aprimorada para cada instância de processo (seis condições × três repetições), o artefato tratou os 54 de 54 itens-base conforme especificado. Ele identificou 27 eventos de qualidade esperados, não reportou alerta falso ou perdido e não liberou evento de erro silencioso em cada instância. Casos normais foram concluídos; casos com falha tornaram-se provisórios sob a política configurada de qualidade parcial.

Em finanças/produção, a versão histórica tratou 39 dos 54 itens-base conforme o oráculo sintético. Ela não expôs alerta estruturado de qualidade, deixou de detectar 27 eventos esperados, liberou 15 classificações que o oráculo reteria e, portanto, acumulou 45 eventos de erro silencioso na definição adotada. Essas diferenças surgem nas condições de falha; ambas as versões tratam o caso sintético normal conforme esperado.

O resultado apoia a RQ1 para o conjunto de falhas definido: a validação explícita impede que classificações sejam liberadas para entradas afetadas. Ele apoia a RQ2 apenas como demonstração de que a infraestrutura comum executa com dois esquemas e rótulos de regras alterados. Ele apoia a RQ3 como comparação técnica histórica, não como comparação de impacto organizacional.

## 6. Discussão para Sistemas de Informação Organizacionais

A principal decisão de projeto é separar qualidade de dados e classificação operacional. Uma contraparte ausente não é tratada como quantidade zero; denominador zero não resulta em desvio percentual zero; duplicata conflitante não é resolvida pela retenção arbitrária de uma linha. Essas escolhas são conservadoras e fazem sentido quando a integração alimenta procedimentos organizacionais. Contudo, cada organização deve validar semântica dos indicadores, idade aceitável dos dados, exceções e regras de escalonamento.

O RPA é o mecanismo técnico de extração e integração, mas a contribuição do artefato para Sistemas de Informação Organizacionais está no apoio à decisão: torna visível quais dados foram usados, quais foram retidos, qual período é representado, quais regras foram aplicadas e onde é necessário julgamento humano. Assim, o resultado entregue ao gestor não é apenas um indicador; é uma informação contextualizada, com limites explícitos para seu uso.

O trabalho pode dialogar com o tema “Tecnologias emergentes aplicadas a sistemas de informação”, mas não deve justificar sua novidade apenas pelo uso de bibliotecas ou dashboard. A contribuição reside na composição de RPA, validação, proveniência, política de atualidade, reprodutibilidade e revisão humana em um artefato de SI organizacional.

## 7. Ameaças à validade e aspectos éticos

Todos os cenários e seu oráculo foram criados pela equipe de desenvolvimento; são pequenos e não representam distribuições empresariais ou trabalho humano. A repetição detecta principalmente instabilidade de execução. Ela não sustenta teste de hipótese ou alegação de confiabilidade universal. A baseline executa código histórico sob dependências atuais; o artigo deve identificar esse fato.

Nenhum dado pessoal ou empresarial foi usado. Uma futura avaliação manual ou com gestores exige procedimentos apropriados à instituição e à organização. Entradas preservadas pelo artefato podem conter dados sensíveis em implantação real; acesso e retenção devem ser definidos. O sistema não possui autenticação, não repúdio, armazenamento imutável ou coordenação de concorrência.

## 8. Conclusão e trabalhos futuros

O estudo apresenta um artefato de RPA reproduzível para integração rastreável de dados financeiros e de produção voltada ao apoio à decisão organizacional. O experimento sintético mostra que o artefato segue a política de tratamento predefinida nas condições controladas e evita os eventos de erro silencioso observados na baseline congelada de finanças/produção. O resultado é evidência técnica de comportamento sob condições explícitas, não prova de benefício organizacional.

Os próximos passos são revisão sistemática da literatura, validação da semântica do processo com responsáveis, implementação de instâncias especificadas independentemente, comparação humana com entradas equivalentes e controles de acesso, retenção e autenticidade de proveniência voltados à implantação.

## References

Cheney, J., Chiticariu, L., & Tan, W.-C. (2009). Provenance in Databases: Why, How, and Where. *Foundations and Trends in Databases*, 1(4), 379–474. https://doi.org/10.1561/1900000006

Hevner, A. R., March, S. T., Park, J., & Ram, S. (2004). Design Science in Information Systems Research. *MIS Quarterly*, 28(1), 75–105. https://doi.org/10.2307/25148625

Pipino, L. L., Lee, Y. W., & Wang, R. Y. (2002). Data quality assessment. *Communications of the ACM*, 45(4), 211–218. https://doi.org/10.1145/505248.506010

Simmhan, Y. L., Plale, B., & Gannon, D. (2005). A survey of data provenance in e-science. *ACM SIGMOD Record*, 34(3), 31–36. https://doi.org/10.1145/1084805.1084812

Wang, R. Y., & Strong, D. M. (1996). Beyond Accuracy: What Data Quality Means to Data Consumers. *Journal of Management Information Systems*, 12(4), 5–33. https://doi.org/10.1080/07421222.1996.11518099
