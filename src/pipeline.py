"""Local execution store, quality gate and replay. No credentials in manifests."""
from contextlib import contextmanager
from dataclasses import replace, asdict
from datetime import datetime, timezone, timedelta
import json
import math
from importlib.metadata import version
import platform
from pathlib import Path
import shutil
import subprocess
import time
import uuid

from src.config import settings as defaults
from src.process import FinanceProduction
from src.provenance import digest, freshness, read_metadata, utcnow, write_json
from src.quality import validate
from src.report_generator import gerar_relatorio

ROOT = Path(__file__).resolve().parent.parent


def load_policy(path=None):
    policy = json.loads((Path(path) if path else ROOT / "config/policy.json").read_text(encoding="utf-8"))
    if set(policy) != {"quality_mode", "freshness_policy", "max_age_days", "rules_version", "financial_threshold", "production_threshold"}:
        raise ValueError("Unexpected/missing policy fields")
    if policy["quality_mode"] not in {"partial", "block"} or policy["freshness_policy"] not in {"provisional", "block"}:
        raise ValueError("Invalid policy")
    for key in ("max_age_days", "financial_threshold", "production_threshold"):
        if isinstance(policy[key], bool) or not isinstance(policy[key], (int, float)) or not math.isfinite(policy[key]) or policy[key] < 0:
            raise ValueError("Invalid policy number")
    if policy["rules_version"] != "finance-production-1":
        raise ValueError("Unsupported rules version; version must identify actual implementation")
    return policy


def code_identity():
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True))
    except (OSError, subprocess.CalledProcessError):
        commit, dirty = None, None
    files = sorted((ROOT / "src").glob("*.py")) + [ROOT / "requirements.txt"]
    return dict(commit=commit, dirty=dirty, files={str(p.relative_to(ROOT)): digest(p) for p in files})


def execute(cfg=defaults, policy_path=None, local=False, replay=None, source_provider=None, process=None):
    process = process or FinanceProduction()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "_" + uuid.uuid4().hex
    folder = Path(cfg.output_dir) / "runs" / run_id
    (folder / "inputs").mkdir(parents=True)
    started = time.perf_counter()
    manifest = dict(run_id=run_id, started_at=utcnow(), state="running", stages=[], sources={},
                    process=dict(name=process.name, version=process.version), code=code_identity(), counts={})
    manifest["runtime"] = dict(python=platform.python_version(), platform=platform.platform(),
                              packages={p: version(p) for p in ("pandas", "openpyxl", "playwright", "streamlit")})
    manifest["schemas"] = {name: asdict(schema) for name, schema in process.schemas.items()}
    result = dict(run_id=run_id, state="running", publication_allowed=False, provisional=True,
                  operational=[], quality=[], decisions=[], limitations=[])

    @contextmanager
    def stage(name):
        entry = dict(name=name, started_at=utcnow())
        clock = time.perf_counter()
        manifest["stages"].append(entry)
        try:
            yield
            entry["state"] = "completed"
        except Exception:
            entry["state"] = "failed"
            raise
        finally:
            entry.update(ended_at=utcnow(), duration_seconds=time.perf_counter()-clock)

    try:
        with stage("configuration"):
            original = None
            if replay:
                original = json.loads((Path(replay) / "manifest.json").read_text(encoding="utf-8"))
                manifest["replay_of"] = original["run_id"]
                if original["process"] != manifest["process"]:
                    raise ValueError("Incompatible replay process")
            policy = load_policy(policy_path or (Path(replay) / "policy.json" if replay else None))
            if policy_path is None and not replay:
                policy["financial_threshold"] = cfg.limiar_desvio_financeiro_atencao
                policy["production_threshold"] = cfg.limiar_desvio_producao_atencao
                # Revalidate environment overrides as well.
                for k in ("financial_threshold", "production_threshold"):
                    if not math.isfinite(policy[k]) or policy[k] < 0:
                        raise ValueError("Invalid threshold")
            manifest["policy"] = policy
            write_json(folder / "policy.json", policy)
            rule_cfg = replace(cfg, limiar_desvio_financeiro_atencao=policy["financial_threshold"],
                               limiar_desvio_producao_atencao=policy["production_threshold"])
        with stage("acquisition"):
            if replay:
                sources = {}
                for name, info in original["sources"].items():
                    path = Path(replay) / "inputs" / Path(info["file"]).name
                    if digest(path) != info["sha256"]:
                        raise ValueError("Replay input hash mismatch")
                    sources[name] = dict(path=path, mode=info["mode"], metadata=info["metadata"])
            elif source_provider:
                sources = source_provider(cfg)
            else:
                from src.extractor import extract_source
                finance = dict(path=cfg.financeiro_path, mode="contingency") if local else extract_source(cfg)
                sources = {"finance": finance, "production": dict(path=cfg.producao_path, mode="local_file")}
            if set(sources) != set(process.schemas):
                raise ValueError("Sources must match process schemas")
            for name, info in sources.items():
                path = Path(info["path"])
                destination = folder / "inputs" / (name + path.suffix)
                shutil.copyfile(path, destination)
                metadata = info.get("metadata", read_metadata(path))
                if digest(destination) != digest(path):
                    raise ValueError("Source changed during preservation")
                # Providers must use the same non-sensitive metadata vocabulary.
                metadata = {k: v for k, v in metadata.items() if k in {"obtained_at", "reference_start", "reference_end", "reference_basis", "temporal_evidence"}}
                manifest["sources"][name] = dict(file=destination.name, original_name=path.name,
                    sha256=digest(destination), mode=info["mode"], metadata=metadata,
                    preserved_at=utcnow(), freshness=freshness(metadata, policy["max_age_days"]))
            template = Path(replay) / "inputs/template.txt" if replay else cfg.template_path
            if replay and digest(template) != original["template_sha256"]:
                raise ValueError("Replay template hash mismatch")
            shutil.copyfile(template, folder / "inputs/template.txt")
            manifest["template_sha256"] = digest(folder / "inputs/template.txt")
        with stage("validation"):
            frames = {name: process.loaders[name](folder / "inputs" / info["file"]) for name, info in manifest["sources"].items()}
            for name, frame in frames.items():
                info = manifest["sources"][name]
                if "reference_end" not in info["metadata"] and "Semana" in frame and not frame.empty:
                    try:
                        weeks = [datetime.strptime(str(w) + "-1", "%G-W%V-%u").replace(tzinfo=timezone.utc) for w in frame["Semana"]]
                        info["metadata"].update(reference_start=min(weeks).isoformat(),
                            reference_end=(max(weeks)+timedelta(days=7, microseconds=-1)).isoformat(),
                            reference_basis="Coluna Semana da entrada preservada; intervalo observado")
                        info["freshness"] = freshness(info["metadata"], policy["max_age_days"])
                    except (ValueError, TypeError):
                        pass
            quality = validate(frames, process.schemas, policy["quality_mode"])
            result.update(quality=quality["issues"], decisions=quality["ledger"])
            manifest["counts"] = quality["counts"]
            temporal = any(s["freshness"]["state"] != "current" for s in manifest["sources"].values())
            if temporal:
                result["limitations"].append("Atualidade desatualizada ou desconhecida em pelo menos uma fonte; obtenção não comprova período de referência.")
            if quality["issues"]:
                result["limitations"].append("Problemas de qualidade: consultar decisões por registro; resultados não representam todas as entradas.")
            blocked = quality["blocked"] or (temporal and policy["freshness_policy"] == "block")
            if blocked:
                for count in manifest["counts"].values():
                    count["analyzed"] = 0
                for entry in result["decisions"]:
                    if entry["decision"] == "analyzed":
                        entry["decision"] = "withheld_run_blocked"
        with stage("analysis"):
            projects = [] if blocked else process.analyze(quality["frames"], rule_cfg)
            result["operational"] = [dict(id=f"operational-{i+1}", **p.as_dict()) for i, p in enumerate(projects)]
            for project in result["operational"]:
                if any(isinstance(v, float) and not math.isfinite(v) for v in project.values()):
                    raise ValueError("Nonfinite calculated indicator")
            result["state"] = "blocked" if blocked else "provisional" if temporal or quality["issues"] else "completed"
            result["publication_allowed"] = not blocked
            result["provisional"] = result["state"] != "completed"
        with stage("report"):
            header = [f"EXECUÇÃO {run_id} — {result['state'].upper()}",
                      "Resultados automáticos; revisão humana separada. Períodos de referência abaixo."]
            for name, info in manifest["sources"].items():
                header.append(f"Fonte {name}: {info['mode']} | atualidade {info['freshness']['state']} | referência {info['metadata'].get('reference_start', '?')} a {info['metadata'].get('reference_end', '?')} | obtido {info['metadata'].get('obtained_at', 'desconhecido')}")
            header.extend(result["limitations"])
            header.append("Qualidade: " + str(len(result["quality"])) + " ocorrência(s).")
            header.extend(f"[{q['type']}] {q['source']} linhas {q['rows']}: {q['decision']}" for q in result["quality"])
            report = folder / "relatorio.txt"
            if blocked:
                body = "PUBLICAÇÃO BLOQUEADA. Nenhuma conclusão operacional liberada."
            else:
                periods = "; ".join(f"{name}: {s['metadata'].get('reference_start', '?')} a {s['metadata'].get('reference_end', '?')}" for name, s in manifest["sources"].items())
                gerar_relatorio(folder / "inputs/template.txt", projects, report, tz=cfg.tz, reference_period=periods)
                body = report.read_text(encoding="utf-8")
            report.write_text("\n".join(header) + "\n\n" + body, encoding="utf-8")
    except Exception as exc:
        # Exception strings/tracebacks from external systems can contain secrets.
        result.update(state="failed", publication_allowed=False, provisional=True, operational=[])
        manifest["error"] = dict(type=type(exc).__name__, stage=manifest["stages"][-1]["name"] if manifest["stages"] else "initialization")
        result["limitations"].append("Falha técnica; nenhuma conclusão operacional liberada. Consulte tipo e etapa no manifesto.")
        (folder / "relatorio.txt").write_text(f"EXECUÇÃO {run_id}: FAILED — PUBLICAÇÃO BLOQUEADA\n" + result["limitations"][-1], encoding="utf-8")
    finally:
        manifest.update(state=result["state"], ended_at=utcnow(), duration_seconds=time.perf_counter()-started,
                        used_contingency=any(s["mode"] == "contingency" for s in manifest["sources"].values()))
        result["sources"] = manifest["sources"]
        result["counts"] = manifest["counts"]
        write_json(folder / "result.json", result)
        manifest["artifacts"] = {n: digest(folder / n) for n in ("result.json", "relatorio.txt")}
        write_json(folder / "manifest.json", manifest)
    return folder, result
