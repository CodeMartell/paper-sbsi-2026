# Revisão de literatura inicial e rastreável

Esta não é uma revisão sistemática concluída. É uma base verificável para o rascunho do artigo, construída a partir de busca temática e metadados conferidos no Crossref em 18/09/2026. Antes da submissão, a equipe deve ampliar a busca em bases como Scopus, Web of Science, ACM DL, AIS e anais do SBSI/iSys, definir strings, critérios de inclusão/exclusão e registrar o fluxo de seleção.

## Lentes teóricas úteis

| Lente | Papel no artigo | Fonte de partida |
|---|---|---|
| Qualidade de dados | Qualidade tem múltiplas dimensões além de precisão; sustenta separar dados inválidos de resultado operacional. | Wang e Strong (1996), [DOI](https://doi.org/10.1080/07421222.1996.11518099) |
| Avaliação de qualidade | Métricas devem ser úteis para organizações e não criadas apenas ad hoc. | Pipino, Lee e Wang (2002), [DOI](https://doi.org/10.1145/505248.506010) |
| Proveniência | Fundamenta registrar origem, transformação e contexto de dados para inspeção posterior. | Simmhan, Plale e Gannon (2005), [DOI](https://doi.org/10.1145/1084805.1084812); Cheney, Chiticariu e Tan (2009), [DOI](https://doi.org/10.1561/1900000006) |
| Design Science Research | Orienta construir e avaliar um artefato de SI no nexo pessoas–organizações–tecnologia. | Hevner et al. (2004), [DOI](https://doi.org/10.2307/25148625) |

## Síntese e lacuna investigada

Os trabalhos de qualidade de dados fornecem conceitos para avaliar registros; os de proveniência explicam por que origem e transformação precisam ser preservadas; Design Science orienta a avaliação do artefato. O problema específico deste estudo é que automações de consolidação podem converter ausência, conflito ou desatualização de dado em valores calculáveis, fazendo um resultado parecer normal sem evidência suficiente.

A contribuição pretendida não é alegar uma nova teoria de qualidade nem uma plataforma universal. É propor e avaliar uma composição de mecanismos: porta de qualidade explícita, política de atualidade, preservação de entradas e hashes, separação de classificação automática e revisão humana, e pontos de extensão de esquema/regra. A avaliação mede o comportamento dessa composição em condições sintéticas conhecidas.

## Protocolo para completar a revisão

1. Buscar em português e inglês combinações de `data quality`, `data provenance`, `traceability`, `accountability`, `operational information systems`, `design science`, `data integration` e `human review`.
2. Incluir estudos de SI que definam construtos, métodos de avaliação ou artefatos comparáveis; excluir textos sem relação com SI organizacional ou sem informação bibliográfica verificável.
3. Registrar base, data, string, total, duplicatas, títulos/resumos avaliados, textos completos e motivo de exclusão.
4. Extrair: problema, domínio, teoria/lente, método, dados, métricas, resultados, ameaças e relação com as RQs.
5. Incluir trabalhos publicados pela comunidade brasileira de SI, como os anais e anais estendidos do SBSI e a iSys, conforme a chamada do evento solicita.

As quatro referências acima são verificadas, mas insuficientes para sustentar sozinhas uma revisão de 15–20 páginas. Não invente estudos, resultados ou citações para completar a bibliografia.
