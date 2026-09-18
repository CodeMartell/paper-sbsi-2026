"""Synthetic, declared process instances used only for the research evaluation.

The scenarios have deliberately limited semantics.  They do not describe the
authors' sourcing, materials, or ECO processes and must not be used as their
requirements.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping

import pandas as pd

from src.data_processor import extrair_dados_financeiros
from src.quality import Schema


@dataclass(frozen=True)
class SyntheticOccurrence:
    identifier: str
    reference_value: float
    observed_value: float
    reference_state: str
    observed_state: str
    deviation_value: float
    deviation_pct: float
    classificacao: str
    motivo: str

    def as_dict(self) -> dict:
        return asdict(self)


class SyntheticReconciliationProcess:
    """Two-source reconciliation with process-specific labels, not business claims."""

    def __init__(self, name: str, version: str, identifier: str, reference: str,
                 observed: str, reference_state: str, observed_state: str,
                 normal_state: str = "Normal"):
        self.name = name
        self.version = version
        self.identifier = identifier
        self.reference = reference
        self.observed = observed
        self.reference_state = reference_state
        self.observed_state = observed_state
        self.normal_state = normal_state
        self.schemas = {
            "reference": Schema(identifier, (reference,), (reference_state,), (reference,)),
            "observed": Schema(identifier, (observed,), (observed_state,), ()),
        }
        self.loaders = {"reference": extrair_dados_financeiros, "observed": extrair_dados_financeiros}

    def analyze(self, frames: Mapping[str, pd.DataFrame], settings) -> list[SyntheticOccurrence]:
        ref = frames["reference"].set_index(self.identifier)
        obs = frames["observed"].set_index(self.identifier)
        items = []
        for identifier in ref.index:
            reference = float(ref.at[identifier, self.reference])
            observed = float(obs.at[identifier, self.observed])
            deviation = observed - reference
            deviation_pct = deviation / reference * 100
            state = str(obs.at[identifier, self.observed_state])
            abnormal = state.strip().lower() != self.normal_state.lower()
            if deviation_pct >= settings.limiar_desvio_financeiro_atencao and abnormal:
                classification = "CRITICO"
                reason = "Desvio acima do limiar com estado observado diferente do estado de referência."
            elif deviation_pct >= settings.limiar_desvio_financeiro_atencao or abnormal:
                classification = "ATENCAO"
                reason = "Desvio acima do limiar ou estado observado diferente do esperado."
            else:
                classification = "NORMAL"
                reason = "Dentro do limiar e com estado observado esperado."
            items.append(SyntheticOccurrence(str(identifier), reference, observed,
                str(ref.at[identifier, self.reference_state]), state, deviation,
                deviation_pct, classification, reason))
        return items

    def render_report(self, projects, output_path: Path, run_id: str, sources: dict) -> str:
        lines = [f"RELATÓRIO SINTÉTICO — {self.name}", f"Execução: {run_id}",
                 "Cenário hipotético para avaliação; não representa processo organizacional real."]
        for item in projects:
            lines.append(f"[{item.classificacao}] {item.identifier}: referência={item.reference_value:.2f}; "
                         f"observado={item.observed_value:.2f}; desvio={item.deviation_pct:+.1f}%; {item.motivo}")
        return "\n".join(lines)


def sourcing_synthetic() -> SyntheticReconciliationProcess:
    return SyntheticReconciliationProcess(
        "sourcing-synthetic", "1", "Solicitacao_ID", "Valor_Referencia", "Valor_Proposto",
        "Estado_Referencia", "Estado_Proposta")


def materials_synthetic() -> SyntheticReconciliationProcess:
    return SyntheticReconciliationProcess(
        "materials-synthetic", "1", "Material_ID", "Quantidade_Planejada", "Quantidade_Registrada",
        "Estado_Planejado", "Estado_Registrado")
