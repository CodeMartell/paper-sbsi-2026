from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
from src.experiments import base_frames, prepare, run_experiments
from src.pipeline import execute, load_policy
from src.provenance import digest, freshness, read_metadata, write_json
from src.quality import validate, FINANCE, PRODUCTION
from src.review import record_review, history


def check(fin, prod, mode="partial"):
    return validate({"finance": fin, "production": prod}, {"finance": FINANCE, "production": PRODUCTION}, mode)


@pytest.mark.parametrize("value", [None, "", "abc", "NaN", "inf", "-inf"])
def test_unknown_numbers_cannot_be_normal(value):
    fin, prod = base_frames()
    fin["Custo_Realizado"] = fin["Custo_Realizado"].astype(object)
    fin.loc[0, "Custo_Realizado"] = value
    result = check(fin, prod)
    assert result["counts"]["finance"]["rejected"] == 1
    assert "SYN01" not in result["frames"]["finance"]["Codigo_Projeto"].values
    assert {q["type"] for q in result["issues"]} == {"invalid_numeric", "unmatched"}


@pytest.mark.parametrize("value", [None, "", "  ", "bad key", "null"])
def test_invalid_keys_rejected(value):
    fin, prod = base_frames()
    fin.loc[0, "Codigo_Projeto"] = value
    assert any(q["type"] == "invalid_key" for q in check(fin, prod)["issues"])


def test_duplicate_decisions_preserve_raw():
    fin, prod = base_frames()
    repeated = pd.concat([fin, fin.iloc[[0]]], ignore_index=True)
    original = repeated.copy(deep=True)
    quality = check(repeated, prod)
    pd.testing.assert_frame_equal(original, repeated)
    assert quality["counts"]["finance"] == dict(received=4, valid=3, rejected=1, analyzed=3, unmatched=0)
    assert quality["issues"][0]["decision"] == "keep_first_reject_copies"
    repeated.loc[3, "Custo_Realizado"] = 123
    quality = check(repeated, prod)
    assert quality["counts"]["finance"]["rejected"] == 2
    assert not quality["frames"]["finance"]["Codigo_Projeto"].eq("SYN01").any()


def test_strict_quality_blocks_even_partial_valid_records():
    fin, prod = base_frames()
    fin.loc[0, "Faturamento_Previsto"] = 0
    q = check(fin, prod, "block")
    assert q["blocked"]
    assert all(c["analyzed"] == 0 for c in q["counts"].values())
    assert all(e["decision"] != "analyzed" for e in q["ledger"])


@pytest.mark.parametrize("source,column", [("finance", "Faturamento_Previsto"), ("production", "Unidades_Planejadas")])
def test_zero_denominators_excluded(source, column):
    fin, prod = base_frames()
    (fin if source == "finance" else prod).loc[0, column] = 0
    q = check(fin, prod)
    assert any(i["type"] == "zero_denominator" for i in q["issues"])
    assert q["counts"][source]["analyzed"] == 2


def test_metadata_requires_matching_hash_and_real_reference(tmp_path):
    path = tmp_path / "input.csv"
    path.write_text("x")
    now = datetime.now(timezone.utc)
    assert freshness(read_metadata(path), 14)["state"] == "unknown"
    meta = dict(sha256=digest(path), obtained_at=now.isoformat(),
                reference_start=(now-timedelta(days=40)).isoformat(), reference_end=(now-timedelta(days=30)).isoformat())
    write_json(str(path)+".meta.json", meta)
    assert freshness(read_metadata(path), 14)["state"] == "stale"
    path.write_text("changed")
    assert freshness(read_metadata(path), 14)["state"] == "unknown"
    assert freshness(dict(reference_start=now.isoformat(), reference_end=(now+timedelta(days=1)).isoformat()), 14)["state"] == "unknown"


def test_pipeline_replay_and_integrity(tmp_path):
    cfg = replace(prepare(tmp_path / "data", "normal"), output_dir=tmp_path / "output")
    folder, first = execute(cfg, local=True)
    replay_folder, second = execute(cfg, replay=folder)
    assert first["operational"] == second["operational"]
    assert first["run_id"] != second["run_id"]
    assert first["sources"]["finance"]["metadata"] == second["sources"]["finance"]["metadata"]
    manifest = json.loads((replay_folder / "manifest.json").read_text())
    assert manifest["replay_of"] == first["run_id"]
    assert manifest["sources"]["finance"]["sha256"] == digest(folder / "inputs/finance.csv")
    (folder / "inputs/finance.csv").write_text("modified")
    _, broken = execute(cfg, replay=folder)
    assert broken["state"] == "failed"
    assert not broken["publication_allowed"]


@pytest.mark.parametrize("scenario", ["stale_contingency", "unknown_contingency"])
def test_temporal_block_in_structure_and_report(tmp_path, scenario):
    cfg = replace(prepare(tmp_path / "data", scenario), output_dir=tmp_path / "output")
    policy = load_policy()
    policy["freshness_policy"] = "block"
    write_json(tmp_path / "policy.json", policy)
    folder, result = execute(cfg, policy_path=tmp_path / "policy.json", local=True)
    assert result["state"] == "blocked"
    assert not result["operational"]
    assert "PUBLICAÇÃO BLOQUEADA" in (folder / "relatorio.txt").read_text(encoding="utf-8")
    assert all(c["analyzed"] == 0 for c in result["counts"].values())


def test_failure_recorded_without_secret(tmp_path, caplog):
    cfg = replace(prepare(tmp_path / "data", "normal"), output_dir=tmp_path / "output")
    secret = "sensitive-password-DO-NOT-LOG"
    with caplog.at_level(logging.DEBUG), patch("src.extractor.extrair_via_gerp_fake", side_effect=RuntimeError(secret)):
        folder, result = execute(cfg)
    assert result["sources"]["finance"]["mode"] == "contingency"
    assert secret not in caplog.text
    assert secret not in (folder / "manifest.json").read_text()
    cfg.financeiro_path.unlink()
    with patch("src.extractor.extrair_via_gerp_fake", side_effect=RuntimeError(secret)):
        folder, result = execute(cfg)
    assert result["state"] == "failed"
    assert (folder / "manifest.json").exists()
    assert secret not in (folder / "manifest.json").read_text()


def test_reviews_are_separate_history(tmp_path):
    cfg = replace(prepare(tmp_path / "data", "normal"), output_dir=tmp_path / "output")
    folder, result = execute(cfg, local=True)
    before = digest(folder / "result.json")
    occurrence = next(p for p in result["operational"] if p["classificacao"] == "CRITICO")["id"]
    with pytest.raises(ValueError):
        record_review(folder, occurrence, "confirmada", "", "Manager")
    with pytest.raises(ValueError):
        record_review(folder, "not-an-occurrence", "confirmada", "Reviewed", "Manager")
    record_review(folder, occurrence, "confirmada", "Conferido", "Pessoa sintética")
    record_review(folder, occurrence, "descartada", "Revisão posterior", "Pessoa sintética")
    assert digest(folder / "result.json") == before
    assert [r["state"] for r in history(folder)] == ["confirmada", "descartada"]
    assert all(r["self_declared"] and r["result_sha256"] == before for r in history(folder))


def test_experiment_harness_matches_predeclared_oracle(tmp_path):
    _, metrics = run_experiments(tmp_path / "experiments")
    assert len(metrics) == 10
    assert all(m["passed"] and m["silent_errors"] == 0 and m["false_alerts"] == 0 for m in metrics)


def test_dashboard_review_form(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    from src import dashboard
    cfg = replace(prepare(tmp_path / "data", "invalid_numeric"), output_dir=tmp_path / "output")
    folder, _ = execute(cfg, local=True)
    monkeypatch.setattr("src.config.settings", cfg)
    app = AppTest.from_file(str(Path(dashboard.__file__))).run(timeout=20)
    assert not app.exception
    assert app.warning
    app.text_input[0].set_value("Gestor sintético")
    app.text_area[0].set_value("Verificação de teste")
    app.button[0].click().run(timeout=20)
    assert not app.exception
    assert len(history(folder)) == 1


def test_duplicate_headers_are_not_silently_renamed(tmp_path):
    from src.data_processor import extrair_dados_financeiros
    path = tmp_path / "duplicate.csv"
    path.write_text("Codigo_Projeto;Codigo_Projeto;Faturamento_Previsto;Custo_Realizado;Horas_Faturadas;Status_Financeiro\nSYN01;SYN01;100;90;10;Normal\n")
    fin = extrair_dados_financeiros(path)
    _, prod = base_frames()
    q = check(fin, prod)
    assert q["blocked"]
    assert q["issues"][0]["type"] == "duplicate_column"


def test_missing_schema_and_empty_source_block():
    fin, prod = base_frames()
    for invalid in (fin.iloc[:0], fin.drop(columns="Custo_Realizado")):
        q = check(invalid, prod)
        assert q["blocked"]
        assert all(c["analyzed"] == 0 for c in q["counts"].values())


def test_leading_zero_keys_are_preserved(tmp_path):
    from src.data_processor import extrair_dados_financeiros
    fin, _ = base_frames()
    fin["Codigo_Projeto"] = ["001", "002", "003"]
    path = tmp_path / "keys.csv"
    fin.to_csv(path, index=False, sep=";")
    assert extrair_dados_financeiros(path)["Codigo_Projeto"].tolist() == ["001", "002", "003"]


def test_modified_result_cannot_receive_review(tmp_path):
    cfg = replace(prepare(tmp_path / "data", "normal"), output_dir=tmp_path / "output")
    folder, result = execute(cfg, local=True)
    (folder / "result.json").write_text(json.dumps(result) + " ", encoding="utf-8")
    with pytest.raises(ValueError, match="alterado"):
        record_review(folder, "operational-2", "confirmada", "Conferido", "Gestor")


def test_invalid_policy_is_recorded_as_failure(tmp_path):
    cfg = replace(prepare(tmp_path / "data", "normal"), output_dir=tmp_path / "output")
    policy = load_policy()
    policy["financial_threshold"] = -1
    write_json(tmp_path / "policy.json", policy)
    folder, result = execute(cfg, policy_path=tmp_path / "policy.json", local=True)
    assert result["state"] == "failed"
    assert not result["operational"]
    assert json.loads((folder / "manifest.json").read_text())["error"]["stage"] == "configuration"
