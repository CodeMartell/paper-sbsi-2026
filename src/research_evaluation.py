"""Reproducible synthetic evaluation for the SBSI research draft.

It evaluates three declared process instances and compares the original
finance/production implementation with the enhanced one.  `reference`
denotes an adjudicated oracle, not observations by human participants.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

import pandas as pd

from src.config import Settings
from src.experiments import base_frames
from src.pipeline import ROOT, execute
from src.provenance import digest, utcnow, write_json
from src.research_processes import materials_synthetic, sourcing_synthetic


BASELINE_COMMIT = "7e1768daf5d4081450ee5d6e904c8c0d3a5a983d"
FAULTS = ("normal", "invalid_numeric", "missing_key", "conflicting_duplicates", "unmatched", "zero_denominator")


def _metadata(path: Path) -> dict:
    now = datetime.now(timezone.utc)
    return {"sha256": digest(path), "obtained_at": utcnow(),
            "reference_start": (now-timedelta(days=3)).isoformat(),
            "reference_end": (now-timedelta(days=1)).isoformat(),
            "reference_basis": "Synthetic controlled interval; not enterprise data"}


def _save_pair(folder: Path, reference: pd.DataFrame, observed: pd.DataFrame) -> tuple[Path, Path]:
    folder.mkdir(parents=True, exist_ok=True)
    a, b = folder / "reference.csv", folder / "observed.csv"
    reference.to_csv(a, sep=";", index=False)
    observed.to_csv(b, sep=";", index=False)
    write_json(Path(str(a) + ".meta.json"), _metadata(a))
    write_json(Path(str(b) + ".meta.json"), _metadata(b))
    return a, b


def _generic_frames(process, fault: str) -> tuple[pd.DataFrame, pd.DataFrame, dict, set[str]]:
    key, ref, obs = process.identifier, process.reference, process.observed
    reference = pd.DataFrame({key: ["SYN01", "SYN02", "SYN03"], ref: [100, 100, 100],
                              process.reference_state: ["Normal"] * 3})
    observed = pd.DataFrame({key: ["SYN01", "SYN02", "SYN03"], obs: [100, 115, 100],
                             process.observed_state: ["Normal", "Atrasado", "Normal"]})
    expected_issues, excluded = set(), set()
    if fault == "invalid_numeric":
        reference[ref] = reference[ref].astype(object)
        reference.loc[0, ref] = "invalid"
        expected_issues = {("reference", "invalid_numeric", "SYN01", ref), ("observed", "unmatched", "SYN01", None)}
        excluded = {"SYN01"}
    elif fault == "missing_key":
        reference.loc[0, key] = ""
        expected_issues = {("reference", "invalid_key", None, key), ("observed", "unmatched", "SYN01", None)}
        excluded = {"SYN01"}
    elif fault == "conflicting_duplicates":
        extra = reference.iloc[[0]].copy()
        extra[ref] = 120
        reference = pd.concat((reference, extra), ignore_index=True)
        expected_issues = {("reference", "conflicting_duplicate", "SYN01", None), ("observed", "unmatched", "SYN01", None)}
        excluded = {"SYN01"}
    elif fault == "unmatched":
        observed = observed.iloc[1:].copy()
        expected_issues = {("reference", "unmatched", "SYN01", None)}
        excluded = {"SYN01"}
    elif fault == "zero_denominator":
        reference.loc[0, ref] = 0
        expected_issues = {("reference", "zero_denominator", "SYN01", ref), ("observed", "unmatched", "SYN01", None)}
        excluded = {"SYN01"}
    labels = {"SYN01": "NORMAL", "SYN02": "CRITICO", "SYN03": "NORMAL"}
    return reference, observed, {k: v for k, v in labels.items() if k not in excluded}, expected_issues


def _finance_frames(fault: str) -> tuple[pd.DataFrame, pd.DataFrame, dict, set[str]]:
    finance, production = base_frames()
    expected_issues, excluded = set(), set()
    if fault == "invalid_numeric":
        finance["Custo_Realizado"] = finance["Custo_Realizado"].astype(object)
        finance.loc[0, "Custo_Realizado"] = "invalid"
        expected_issues = {("finance", "invalid_numeric", "SYN01", "Custo_Realizado"), ("production", "unmatched", "SYN01", None)}
        excluded = {"SYN01"}
    elif fault == "missing_key":
        finance.loc[0, "Codigo_Projeto"] = ""
        expected_issues = {("finance", "invalid_key", None, "Codigo_Projeto"), ("production", "unmatched", "SYN01", None)}
        excluded = {"SYN01"}
    elif fault == "conflicting_duplicates":
        extra = finance.iloc[[0]].copy(); extra["Custo_Realizado"] = 150
        finance = pd.concat((finance, extra), ignore_index=True)
        expected_issues = {("finance", "conflicting_duplicate", "SYN01", None), ("production", "unmatched", "SYN01", None)}
        excluded = {"SYN01"}
    elif fault == "unmatched":
        production = production.iloc[1:].copy()
        expected_issues = {("finance", "unmatched", "SYN01", None)}
        excluded = {"SYN01"}
    elif fault == "zero_denominator":
        finance.loc[0, "Faturamento_Previsto"] = 0
        expected_issues = {("finance", "zero_denominator", "SYN01", "Faturamento_Previsto"), ("production", "unmatched", "SYN01", None)}
        excluded = {"SYN01"}
    labels = {"SYN01": "NORMAL", "SYN02": "CRITICO", "SYN03": "NORMAL"}
    return finance, production, {k: v for k, v in labels.items() if k not in excluded}, expected_issues


def _legacy_module():
    source = subprocess.check_output(["git", "show", f"{BASELINE_COMMIT}:src/data_processor.py"],
                                     cwd=ROOT, text=True, encoding="utf-8")
    spec = importlib.util.spec_from_loader("baseline_data_processor", loader=None)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    exec(compile(source, f"{BASELINE_COMMIT}:src/data_processor.py", "exec"), module.__dict__)
    return module


def _baseline(finance, production) -> tuple[str, dict]:
    legacy = _legacy_module()
    try:
        fin, prod = legacy.tratar_dados(finance, production)
        rows = legacy.cruzar_dados(fin, prod)
        items = legacy.analisar_e_identificar_divergencias(rows, Settings())
        return "completed", {p.codigo_projeto: p.classificacao for p in items}
    except Exception as exc:  # Original behavior is part of the observation.
        return type(exc).__name__, {}


def _score(observed: dict, expected: dict, expected_issues: set, detected: set, state: str) -> dict:
    correct = sum(observed.get(identifier) == expected.get(identifier) for identifier in ("SYN01", "SYN02", "SYN03"))
    released_wrong = sum(identifier not in expected or label != expected[identifier] for identifier, label in observed.items())
    missed = expected_issues - detected
    return {"state": state, "base_projects": 3, "eligible_projects": len(expected), "released_projects": len(observed),
            "correctly_handled_projects": correct, "true_alerts": len(expected_issues & detected),
            "false_alerts": len(detected - expected_issues), "missed_alerts": len(missed),
            "incorrect_released_classifications": released_wrong,
            "silent_errors": released_wrong + (len(missed) if state in {"completed", "provisional"} else 0)}


def run(output: str = "output/research-evaluation", repetitions: int = 3):
    if repetitions < 1:
        raise ValueError("repetitions must be positive")
    root = Path(output) / uuid.uuid4().hex
    root.mkdir(parents=True)
    protocol = {"kind": "synthetic multi-process evaluation", "created_at": utcnow(), "baseline_commit": BASELINE_COMMIT,
                "repetitions": repetitions, "faults": FAULTS,
                "disclaimer": "Reference adjudication is an oracle, not a manual participant study."}
    write_json(root / "protocol.json", protocol)
    metrics = []
    instances = [("finance-production", None), ("sourcing-synthetic", sourcing_synthetic()),
                 ("materials-synthetic", materials_synthetic())]
    process_codes = {"finance-production": "fin", "sourcing-synthetic": "src", "materials-synthetic": "mat"}
    for repetition in range(1, repetitions + 1):
        for process_name, process in instances:
            for fault_index, fault in enumerate(FAULTS, start=1):
                # Short names keep artifacts usable on Windows paths in deep test folders.
                case = root / f"r{repetition}_{process_codes[process_name]}_{fault_index}"
                if process is None:
                    first, second, expected, expected_issues = _finance_frames(fault)
                    first_file, second_file = _save_pair(case / "data", first, second)
                    cfg = Settings(data_dir=case / "data", financeiro_csv=first_file.name, producao_xlsx="unused.xlsx",
                                   template_relatorio=str(ROOT / "data" / "modelo_relatorio_final_diretoria.txt"),
                                   output_dir=case / "o", logs_dir=case / "l")
                    # Use in-memory reader-compatible CSV for both sources.
                    second.to_csv(case / "data" / "production.csv", sep=";", index=False)
                    write_json(case / "data" / "production.csv.meta.json", _metadata(case / "data" / "production.csv"))
                    from src.data_processor import extrair_dados_financeiros
                    from src.process import FinanceProduction
                    finance_process = FinanceProduction()
                    finance_process.loaders = {"finance": extrair_dados_financeiros, "production": extrair_dados_financeiros}
                    provider = lambda _cfg, a=first_file: {"finance": {"path": a, "mode": "synthetic_file"},
                        "production": {"path": case / "data" / "production.csv", "mode": "synthetic_file"}}
                    folder, result = execute(cfg, source_provider=provider, process=finance_process)
                    observed = {p["codigo_projeto"]: p["classificacao"] for p in result["operational"]}
                    detected = {(q["source"], q["type"], q["key"], q["column"]) for q in result["quality"]}
                    enhanced = _score(observed, expected, expected_issues, detected, result["state"])
                    baseline_state, baseline_labels = _baseline(first, second)
                    baseline = _score(baseline_labels, expected, expected_issues, set(), baseline_state)
                    for method, score in (("enhanced", enhanced), ("original", baseline)):
                        metrics.append({"process": process_name, "fault": fault, "repetition": repetition, "method": method, **score})
                else:
                    reference, observed_frame, expected, expected_issues = _generic_frames(process, fault)
                    a, b = _save_pair(case / "data", reference, observed_frame)
                    cfg = Settings(data_dir=case / "data", template_relatorio=str(ROOT / "data" / "modelo_relatorio_final_diretoria.txt"),
                                   output_dir=case / "o", logs_dir=case / "l")
                    provider = lambda _cfg, a=a, b=b: {"reference": {"path": a, "mode": "synthetic_file"},
                        "observed": {"path": b, "mode": "synthetic_file"}}
                    folder, result = execute(cfg, source_provider=provider, process=process)
                    labels = {p["identifier"]: p["classificacao"] for p in result["operational"]}
                    detected = {(q["source"], q["type"], q["key"], q["column"]) for q in result["quality"]}
                    metrics.append({"process": process_name, "fault": fault, "repetition": repetition,
                                    "method": "enhanced", **_score(labels, expected, expected_issues, detected, result["state"])})
    write_json(root / "metrics.json", metrics)
    pd.DataFrame(metrics).to_csv(root / "metrics.csv", index=False)
    summary = pd.DataFrame(metrics).groupby(["process", "method"], as_index=False).agg(
        executions=("fault", "count"), correctly_handled_projects=("correctly_handled_projects", "sum"),
        base_projects=("base_projects", "sum"), eligible_projects=("eligible_projects", "sum"), true_alerts=("true_alerts", "sum"),
        false_alerts=("false_alerts", "sum"), missed_alerts=("missed_alerts", "sum"), silent_errors=("silent_errors", "sum"))
    summary.to_csv(root / "summary.csv", index=False)
    return root, metrics, summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="output/research-evaluation")
    parser.add_argument("--repetitions", type=int, default=3)
    args = parser.parse_args()
    root, metrics, _ = run(args.output, args.repetitions)
    print(f"Synthetic research evaluation: {root}; {len(metrics)} observations")
