"""Synthetic fault-injection experiment; no claims about real business impact."""
import argparse
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import platform
import uuid
from unittest.mock import patch

import pandas as pd
from src.config import Settings
from src.pipeline import execute, load_policy, ROOT
from src.provenance import digest, utcnow, write_json


def base_frames():
    return (pd.DataFrame({
        "Codigo_Projeto": ["SYN01", "SYN02", "SYN03"],
        "Faturamento_Previsto": [100, 100, 100], "Custo_Realizado": [90, 110, 90],
        "Horas_Faturadas": [10, 10, 10], "Status_Financeiro": ["Normal"]*3}),
        pd.DataFrame({"Codigo_Projeto": ["SYN01", "SYN02", "SYN03"],
        "Unidades_Planejadas": [100, 100, 100], "Unidades_Produzidas": [100, 80, 100],
        "Status_Producao": ["Normal", "Atrasado", "Normal"]}))


# Oracle declared before running, independent of pipeline classification code.
SCENARIOS = {
    "normal": ("completed", [], [], False),
    "source_unavailable": ("completed", [], [], True),
    "stale_contingency": ("provisional", [], [], True),
    "unknown_contingency": ("provisional", [], [], True),
    "missing_column": ("blocked", [("finance", "missing_column", None, "Horas_Faturadas"),
        *(('production', 'unmatched', k, None) for k in ('SYN01', 'SYN02', 'SYN03'))], ["SYN01", "SYN02", "SYN03"], False),
    "invalid_numeric": ("provisional", [("finance", "invalid_numeric", "SYN01", "Custo_Realizado"),
        ("production", "unmatched", "SYN01", None)], ["SYN01"], False),
    "missing_key": ("provisional", [("finance", "invalid_key", None, "Codigo_Projeto"),
        ("production", "unmatched", "SYN01", None)], ["SYN01"], False),
    "conflicting_duplicates": ("provisional", [("finance", "conflicting_duplicate", "SYN01", None),
        ("production", "unmatched", "SYN01", None)], ["SYN01"], False),
    "unmatched": ("provisional", [("finance", "unmatched", "SYN01", None)], ["SYN01"], False),
    "zero_denominator": ("provisional", [("finance", "zero_denominator", "SYN01", "Faturamento_Previsto"),
        ("production", "unmatched", "SYN01", None)], ["SYN01"], False),
}


def prepare(folder, scenario):
    folder.mkdir(parents=True)
    fin, prod = base_frames()
    if scenario == "missing_column":
        fin = fin.drop(columns="Horas_Faturadas")
    elif scenario == "invalid_numeric":
        fin["Custo_Realizado"] = fin["Custo_Realizado"].astype(object)
        fin.loc[0, "Custo_Realizado"] = "invalid"
    elif scenario == "missing_key":
        fin.loc[0, "Codigo_Projeto"] = ""
    elif scenario == "conflicting_duplicates":
        extra = fin.iloc[[0]].copy()
        extra["Custo_Realizado"] = 999
        fin = pd.concat([fin, extra], ignore_index=True)
    elif scenario == "unmatched":
        prod = prod.iloc[1:]
    elif scenario == "zero_denominator":
        fin.loc[0, "Faturamento_Previsto"] = 0
    fin.to_csv(folder / "finance.csv", sep=";", index=False)
    prod.to_excel(folder / "production.xlsx", sheet_name="Producao", index=False)
    now = datetime.now(timezone.utc)
    for name in ("finance.csv", "production.xlsx"):
        days = 30 if scenario == "stale_contingency" and name == "finance.csv" else 2
        meta = dict(sha256=digest(folder / name), obtained_at=utcnow(),
                    reference_start=(now-timedelta(days=days+6)).isoformat(),
                    reference_end=(now-timedelta(days=days)).isoformat(),
                    reference_basis="SYNTHETIC generated reference period; not enterprise data")
        if scenario == "unknown_contingency" and name == "finance.csv":
            meta = {"sha256": digest(folder / name), "obtained_at": utcnow()}
        write_json(folder / (name + ".meta.json"), meta)
    return Settings(data_dir=folder, financeiro_csv="finance.csv", producao_xlsx="production.xlsx",
                    template_relatorio=str(ROOT / "data/modelo_relatorio_final_diretoria.txt"),
                    logs_dir=folder / "logs")


def run_experiments(output="output/experiments", repetitions=1):
    if repetitions < 1:
        raise ValueError("Repetitions must be positive")
    root = Path(output) / uuid.uuid4().hex
    root.mkdir(parents=True)
    write_json(root / "protocol.json", dict(synthetic=True, scenarios=SCENARIOS, repetitions=repetitions,
                                          created_at=utcnow(), python=platform.python_version(), platform=platform.platform()))
    policy = load_policy()
    write_json(root / "policy.json", policy)
    metrics = []
    for repetition in range(repetitions):
        for scenario_index, (scenario, (state, expected_issues, excluded, contingency)) in enumerate(SCENARIOS.items(), start=1):
            # Keep evidence paths portable to Windows paths used by test runners.
            case = root / f"r{repetition+1}_{scenario_index}"
            cfg = replace(prepare(case / "data", scenario), output_dir=case)
            if contingency:
                # Injection only at external acquisition boundary; real fallback/breaker execute.
                with patch("src.extractor.extrair_via_gerp_fake", side_effect=ConnectionError("synthetic unavailability")):
                    folder, result = execute(cfg, policy_path=root / "policy.json")
            else:
                def provider(c):
                    return {"finance": dict(path=c.financeiro_path, mode="synthetic_file"),
                            "production": dict(path=c.producao_path, mode="synthetic_file")}
                folder, result = execute(cfg, policy_path=root / "policy.json", source_provider=provider)
            manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
            expected = {tuple(e) for e in expected_issues}
            detected = {(q['source'], q['type'], q['key'], q['column']) for q in result['quality']}
            expected_labels = {"SYN01": "NORMAL", "SYN02": "CRITICO", "SYN03": "NORMAL"}
            expected_labels = {k: v for k, v in expected_labels.items() if k not in excluded}
            observed = {p["codigo_projeto"]: p["classificacao"] for p in result["operational"]}
            correct = sum(observed.get(k) == expected_labels.get(k) for k in ("SYN01", "SYN02", "SYN03"))
            unexpected_labels = sum(k not in expected_labels or v != expected_labels[k] for k, v in observed.items())
            missing = expected-detected
            passed = (result['state'] == state and detected == expected and observed == expected_labels
                      and manifest['used_contingency'] == contingency)
            metrics.append(dict(scenario=scenario, repetition=repetition+1, run_id=result['run_id'],
                state=result['state'], expected_state=state, duration_seconds=manifest['duration_seconds'],
                records_received=sum(c['received'] for c in result['counts'].values()),
                analyzed_projects=len(observed), correctly_handled_projects=correct, project_denominator=3,
                expected_problems=len(expected), detected_problems=len(detected),
                true_alerts=len(expected & detected), false_alerts=len(detected-expected),
                missed_alerts=len(missing), incorrect_released_classifications=unexpected_labels,
                silent_errors=unexpected_labels+(len(missing) if result['publication_allowed'] else 0),
                passed=passed))
    write_json(root / "metrics.json", metrics)
    pd.DataFrame(metrics).to_csv(root / "metrics.csv", index=False)
    return root, metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="output/experiments")
    parser.add_argument("--repetitions", type=int, default=1)
    args = parser.parse_args()
    path, metrics = run_experiments(args.output, args.repetitions)
    print(f"Synthetic experiment: {path}; {sum(m['passed'] for m in metrics)}/{len(metrics)} scenarios as expected")
    raise SystemExit(0 if all(m['passed'] for m in metrics) else 1)
