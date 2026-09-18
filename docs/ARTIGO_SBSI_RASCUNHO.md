# Artefato rastreável para consolidação de dados operacionais: avaliação sintética de qualidade, atualidade e revisão humana

> **Status:** rascunho de pesquisa, não pronto para submissão. Remover nomes, instituições, URLs identificadoras e referências ao repositório durante a preparação da versão duplamente anônima. Confirmar integralmente a chamada e o template SBC vigente antes de exportar PDF.

## Structured abstract

**Research Context.** Operational information systems consolidate data from multiple sources to support managerial decisions, but source failures, incomplete fields, duplicates, and uncertainty about the reference period can turn invalid inputs into apparently valid indicators.

**Scientific and/or Practical Problem.** Conventional reconciliation automation may discard, impute, or merge problematic records without making treatment decisions explicit, thereby releasing operational classifications that cannot be independently explained or reproduced.

**Proposed Solution and/or Analysis.** We designed an extensible local artifact that preserves inputs, associates hashes and temporal metadata with sources, validates schemas and records before business rules, separates data-quality issues from operational classifications, and stores human-review events separately from automatic results.

**Related IS Theory.** The study draws on data quality as a multidimensional construct, data provenance, and Design Science Research in Information Systems.

**Research Method.** A design-science evaluation uses a predeclared oracle and three synthetic two-source process instances. Six controlled input conditions are repeated three times. The financial/production instance is also compared with the identified historical implementation using equivalent inputs.

**Summary of Results.** In 54 synthetic base items per enhanced instance, the artifact handled all items according to the oracle and released no silent-error event under the study definition. In the financial/production comparison, the historical implementation handled 39 of 54 base items according to the oracle, missed 27 expected quality alerts, and produced 45 silent-error events. These results apply only to the constructed scenarios.

**Contributions and Impact to IS area.** The work offers a reproducible artifact and evaluation protocol for treating data quality and source freshness as first-class conditions in operational information systems. It also delineates evidence that remains necessary before claims of organizational impact or cross-domain reuse.

## 1. Introduction

Organizations use operational data from heterogeneous sources to produce indicators and exceptions. A calculation can be arithmetically correct while its input is incomplete, duplicated, outdated, or unmatched. If the system converts unknown values to zero, silently removes rows, or performs a join that hides a missing counterpart, the resulting classification can be interpreted as normal even though the evidence is insufficient. This is an information-systems problem because the consequence is not merely a data-processing error: people may use an unsupported output in an organizational procedure.

This work investigates an artifact for traceable operational reconciliation. Its first instance combines financial and production data. To avoid inferring requirements of other author projects, the evaluation adds two explicitly synthetic instances called sourcing and materials; their names are labels for hypothetical schemas only. No meaning of ECOs is assumed or implemented.

The study asks RQ1, RQ2 and RQ3 as stated in `docs/AVALIACAO_MULTIPROCESSO.md`. It does not claim that the artifact improves human productivity, organizational performance, or decisions in production. Those claims require participants and authorized field data.

## 2. Background and related work

Data quality is broader than accuracy: consumers evaluate multiple dimensions of whether data are fit for use [Wang and Strong, 1996]. Pipino, Lee and Wang [2002] argue for usable metrics rather than ad hoc quality measures. In this work, required columns, valid keys, parseable finite numbers, duplicate conflict, correspondence, and denominator validity operationalize a limited, explicit quality policy. The policy does not claim to cover all data-quality dimensions.

Provenance concerns the lineage and context that make a result inspectable. Simmhan, Plale and Gannon [2005] survey provenance in e-science; Cheney, Chiticariu and Tan [2009] discuss why, how and where provenance is represented in databases. The artifact adapts this concern to a local operational setting by preserving source copies, hashes, source mode, reference interval, configuration and stage durations. A hash detects a change relative to a preserved manifest but does not authenticate origin or make local files immutable.

Hevner et al. [2004] frame Design Science Research as construction and evaluation of innovative artifacts at the intersection of people, organizations and technology. The artifact is evaluated as a design-science instantiation: it solves a defined problem, has explicit requirements and behavior, and is evaluated against a predeclared oracle. The evaluation is technical and synthetic; it is not a behavioral field study.

## 3. Artifact design

The artifact organizes a run into configuration, acquisition, validation, analysis and reporting. It assigns a UUID, preserves inputs and their hashes, records a policy and code identity, and writes manifest/result artifacts. The quality gate runs before business analysis. Missing schema, empty source and no eligible pairs block the run. Invalid keys, unknown/non-finite numbers, missing required text, denominator zero, conflicting duplicates and unmatched records create decisions and retain original values in the ledger. Depending on policy, a run with quality issues can be provisional or blocked.

Freshness uses a reference interval, not the file modification timestamp. A sidecar metadata file binds `obtained_at`, `reference_start`, `reference_end` and the reference basis to the source hash. A current download of an old reference period remains stale. Unknown temporal evidence produces an explicit `unknown` state. The report, JSON and dashboard expose these states.

The dashboard reads stored results rather than recalculating business rules. A reviewer may record pending, confirmed or discarded events with a justification and self-declared identity. This is a local, append-only application history, not authentication, a digital signature or a tamper-proof audit trail.

Two extension points are used in the evaluation: a schema declares key, numeric, text and denominator fields; a process declares loaders, rules and report rendering. Financial/production remains the original business-specific instance. The new instances use their own labels and rule parameters, but share quality, provenance, policy, preservation and review infrastructure.

## 4. Method

The study uses controlled synthetic evaluation. Each instance contains three synthetic identifiers. The normal case produces two normal records and one critical record. Five fault conditions alter one input: invalid numeric value, missing key, conflicting duplicate, unmatched record, or zero denominator. The expected quality events and eligible classifications are defined in code before execution. Each condition is executed three times.

The primary measures are correctly handled base items, true/false/missed quality alerts, incorrect operational classifications released and silent-error events. A base item is correctly handled if it receives the expected label when eligible or is withheld when the oracle requires withholding. A silent-error event is an incorrect released classification plus a missed expected quality event when the run releases output. It is an event count, not a probability or a count of people affected.

For RQ3, the runner loads the historical `data_processor.py` from commit `7e1768daf5d4081450ee5d6e904c8c0d3a5a983d` via Git and applies it to the equivalent financial/production DataFrames. The original version has no quality-event model; its detected-quality set is therefore empty. The comparison is limited to this historical process instance. The two synthetic extensions have no baseline because they did not exist in the original repository.

## 5. Results

Across 18 enhanced runs for each process instance (six conditions × three repetitions), the enhanced artifact handled 54 of 54 base items as specified. It identified 27 expected quality events, reported no false or missed alert and released zero silent-error event for each instance. Normal cases completed; fault cases became provisional under the configured partial-quality policy.

In financial/production, the historical version handled 39 of 54 base items according to the synthetic oracle. It exposed no structured quality alert, missed 27 expected quality events, released 15 classifications that the oracle would withhold, and therefore accumulated 45 silent-error events under the stated definition. These differences arise in the fault conditions; both versions handle the normal synthetic case as expected.

The result supports RQ1 for the defined fault set: explicit validation prevents classifications from being released for affected inputs. It supports RQ2 only as a demonstration that common infrastructure executes with two altered schemas/rule labels. It supports RQ3 as a historical technical comparison, not as an organizational impact comparison.

## 6. Discussion

The salient design decision is separating quality from operations. A missing counterpart is not treated as a zero quantity; a denominator equal to zero does not yield a zero percent deviation; a conflicting duplicate is not resolved by retaining an arbitrary row. These choices may be conservative. An organization can set a blocking policy, but must validate its own semantics, acceptable age, exceptions and escalation procedure.

The result also illustrates a boundary for claims about emerging technologies. The contribution is not novelty from a fashionable tool. It is the engineered composition of validation, provenance, freshness policy, reproducibility and review in an operational information-system artifact. This speaks to technological transparency and accountability, data/information management and organizational IS. The theme “Tecnologias emergentes aplicadas a sistemas de informação” should only be selected if the final paper explains this contribution as a current technical approach rather than equating programming libraries with scientific novelty.

## 7. Threats to validity and ethics

All scenarios and their oracle were created by the development team; they are small and cannot represent enterprise distributions or human work. Repetition chiefly detects execution instability. It does not support hypothesis testing or a claim of universal reliability. The baseline executes historical code under current runtime dependencies. The paper must identify this fact.

No personal or enterprise data were used. Future manual or manager evaluation requires informed procedures appropriate to the institution and organization. Inputs preserved by the artifact can contain sensitive data in a real deployment, so access and retention must be defined. The system lacks authentication, nonrepudiation, immutable storage and concurrency coordination.

## 8. Conclusion and future work

The study presents a reproducible artifact that makes quality failures, temporal uncertainty and operational rules visible as different classes of evidence. The synthetic experiment shows that the artifact follows its predeclared handling policy in three controlled instances and avoids the silent-error events observed in the frozen financial/production baseline. The result is a technical proof of behavior under explicit conditions, not proof of organizational benefit.

Next steps are a systematic literature review, validation of process semantics with responsible stakeholders, implementation of independently specified process instances, a human comparison on equivalent inputs, and deployment-oriented controls for access, retention and provenance authenticity.

## References

Cheney, J., Chiticariu, L., & Tan, W.-C. (2009). Provenance in Databases: Why, How, and Where. *Foundations and Trends in Databases*, 1(4), 379–474. https://doi.org/10.1561/1900000006

Hevner, A. R., March, S. T., Park, J., & Ram, S. (2004). Design Science in Information Systems Research. *MIS Quarterly*, 28(1), 75–105. https://doi.org/10.2307/25148625

Pipino, L. L., Lee, Y. W., & Wang, R. Y. (2002). Data quality assessment. *Communications of the ACM*, 45(4), 211–218. https://doi.org/10.1145/505248.506010

Simmhan, Y. L., Plale, B., & Gannon, D. (2005). A survey of data provenance in e-science. *ACM SIGMOD Record*, 34(3), 31–36. https://doi.org/10.1145/1084805.1084812

Wang, R. Y., & Strong, D. M. (1996). Beyond Accuracy: What Data Quality Means to Data Consumers. *Journal of Management Information Systems*, 12(4), 5–33. https://doi.org/10.1080/07421222.1996.11518099
