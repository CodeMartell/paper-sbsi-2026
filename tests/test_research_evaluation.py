from dataclasses import replace
import json
from pathlib import Path

from src.config import Settings
from src.pipeline import execute
from src.research_evaluation import run
from src.research_processes import materials_synthetic, sourcing_synthetic


def _provider(reference, observed):
    return lambda _cfg: {"reference": {"path": reference, "mode": "synthetic_file"},
                         "observed": {"path": observed, "mode": "synthetic_file"}}


def test_declared_synthetic_processes_execute_and_preserve_results(tmp_path):
    import pandas as pd
    for process in (sourcing_synthetic(), materials_synthetic()):
        key = process.identifier
        reference = tmp_path / f"{process.name}-reference.csv"
        observed = tmp_path / f"{process.name}-observed.csv"
        pd.DataFrame({key: ["X1", "X2"], process.reference: [100, 100],
                      process.reference_state: ["Normal", "Normal"]}).to_csv(reference, sep=";", index=False)
        pd.DataFrame({key: ["X1", "X2"], process.observed: [100, 110],
                      process.observed_state: ["Normal", "Atrasado"]}).to_csv(observed, sep=";", index=False)
        cfg = Settings(output_dir=tmp_path / process.name, logs_dir=tmp_path / "logs",
                       template_relatorio=Path(__file__).resolve().parent.parent / "data" / "modelo_relatorio_final_diretoria.txt")
        folder, result = execute(cfg, process=process, source_provider=_provider(reference, observed))
        assert result["state"] == "provisional"  # no temporal metadata is intentional here
        assert [x["classificacao"] for x in result["operational"]] == ["NORMAL", "CRITICO"]
        assert "Cenário hipotético" in (folder / "relatorio.txt").read_text(encoding="utf-8")
        assert json.loads((folder / "manifest.json").read_text(encoding="utf-8"))["process"]["name"] == process.name


def test_research_evaluation_compares_frozen_baseline(tmp_path):
    root, metrics, summary = run(tmp_path / "research", repetitions=1)
    assert len(metrics) == 24
    enhanced = [row for row in metrics if row["method"] == "enhanced"]
    original = [row for row in metrics if row["method"] == "original"]
    assert all(row["silent_errors"] == 0 for row in enhanced)
    assert any(row["silent_errors"] > 0 for row in original)
    assert set(summary["process"]) == {"finance-production", "sourcing-synthetic", "materials-synthetic"}
    assert (root / "protocol.json").exists()
