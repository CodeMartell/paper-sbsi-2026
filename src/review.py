"""Append-only application history in SQLite; local files remain editable by owners."""
import json
from pathlib import Path
import sqlite3
from src.provenance import digest, utcnow


def connect(folder):
    connection = sqlite3.connect(Path(folder) / "reviews.sqlite", timeout=10)
    connection.execute("""CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT, occurrence_id TEXT NOT NULL,
        state TEXT NOT NULL, justification TEXT NOT NULL, reviewer TEXT NOT NULL,
        self_declared INTEGER NOT NULL, at TEXT NOT NULL, result_sha256 TEXT NOT NULL)""")
    return connection


def history(folder):
    if not (Path(folder) / "reviews.sqlite").exists():
        return []
    with connect(folder) as db:
        db.row_factory = sqlite3.Row
        return [dict(r) for r in db.execute("SELECT * FROM reviews ORDER BY id")]


def record_review(folder, occurrence_id, state, justification, reviewer):
    result_path = Path(folder) / "result.json"
    manifest = json.loads((Path(folder) / "manifest.json").read_text(encoding="utf-8"))
    if digest(result_path) != manifest["artifacts"]["result.json"]:
        raise ValueError("Resultado alterado após a execução; revisão bloqueada")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    occurrences = result["quality"] + [p for p in result["operational"] if p["classificacao"] != "NORMAL"]
    if occurrence_id not in {o["id"] for o in occurrences}:
        raise ValueError("Ocorrência inexistente")
    if state not in {"pendente", "confirmada", "descartada"}:
        raise ValueError("Estado inválido")
    if not justification.strip() or not reviewer.strip():
        raise ValueError("Informe justificativa e responsável autodeclarado")
    with connect(folder) as db:
        db.execute("INSERT INTO reviews (occurrence_id,state,justification,reviewer,self_declared,at,result_sha256) VALUES (?,?,?,?,?,?,?)",
                   (occurrence_id, state, justification.strip(), reviewer.strip(), 1, utcnow(), digest(result_path)))
