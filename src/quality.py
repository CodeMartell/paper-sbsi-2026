"""Validation primitives; row numbers are 1-based data rows, excluding headers."""
from dataclasses import dataclass
import math
import re
import json
import pandas as pd


@dataclass(frozen=True)
class Schema:
    key: str
    numeric: tuple[str, ...]
    text: tuple[str, ...]
    denominators: tuple[str, ...]
    key_pattern: str = r"[A-Za-z0-9][A-Za-z0-9_.-]*"


FINANCE = Schema("Codigo_Projeto", ("Faturamento_Previsto", "Custo_Realizado", "Horas_Faturadas"), ("Status_Financeiro",), ("Faturamento_Previsto",))
PRODUCTION = Schema("Codigo_Projeto", ("Unidades_Planejadas", "Unidades_Produzidas"), ("Status_Producao",), ("Unidades_Planejadas",))


def validate(frames, schemas, mode="partial"):
    """Return eligible frames, explicit issues, a decision for every input row, counts."""
    if mode not in {"partial", "block"}:
        raise ValueError("Invalid quality mode")
    issues, ledger, clean, counts = [], [], {}, {}
    blocked = False

    def issue(source, kind, rows, key, decision, column=None):
        issues.append(dict(id=f"quality-{len(issues)+1}", source=source, type=kind,
                           rows=rows, key=key, column=column, decision=decision))

    for source, raw in frames.items():
        schema = schemas[source]
        df = raw.copy().reset_index(drop=True)
        original_rows = json.loads(raw.to_json(orient="records")) if not raw.columns.duplicated().any() else [{} for _ in range(len(raw))]
        decisions = {i: [] for i in df.index}
        missing = sorted(set((schema.key,) + schema.numeric + schema.text) - set(df.columns))
        if missing or df.columns.duplicated().any() or df.empty:
            kind = "missing_column" if missing else "duplicate_column" if df.columns.duplicated().any() else "empty_source"
            issue(source, kind, [], None, "block_run", ", ".join(missing) or None)
            blocked = True
            for i in df.index:
                decisions[i].append(kind)
            clean[source] = pd.DataFrame(columns=[schema.key, *schema.numeric, *schema.text])
        else:
            df[schema.key] = df[schema.key].map(lambda v: str(v).strip() if pd.notna(v) else "")
            for i, row in df.iterrows():
                key = row[schema.key]
                if not re.fullmatch(schema.key_pattern, key) or key.lower() in {"nan", "none", "null"}:
                    decisions[i].append("invalid_key")
                    issue(source, "invalid_key", [i+1], key or None, "reject_row", schema.key)
            for col in schema.numeric:
                values = pd.to_numeric(df[col], errors="coerce")
                for i, value in values.items():
                    kind = "invalid_numeric" if pd.isna(value) or not math.isfinite(float(value)) else "zero_denominator" if col in schema.denominators and value == 0 else None
                    if kind:
                        decisions[i].append(kind)
                        issue(source, kind, [i+1], df.at[i, schema.key], "reject_row", col)
                df[col] = values
            for col in schema.text:
                for i, value in df[col].items():
                    if pd.isna(value) or not str(value).strip():
                        decisions[i].append("missing_text")
                        issue(source, "missing_text", [i+1], df.at[i, schema.key], "reject_row", col)
            # Compare original values (all columns), before numerical coercion hides conflicts.
            for key, group in df.groupby(schema.key, sort=False):
                if len(group) < 2 or not key:
                    continue
                indices = list(group.index)
                identical = len(raw.reset_index(drop=True).loc[indices].drop_duplicates()) == 1
                affected = indices[1:] if identical else indices
                kind = "identical_duplicate" if identical else "conflicting_duplicate"
                issue(source, kind, [i+1 for i in indices], key,
                      "keep_first_reject_copies" if identical else "reject_all_for_key")
                for i in affected:
                    decisions[i].append(kind)
            clean[source] = df.loc[[i for i in df.index if not decisions[i]]].copy()
        counts[source] = dict(received=len(df), valid=len(clean[source]), rejected=len(df)-len(clean[source]), analyzed=0)
        for i in df.index:
            ledger.append(dict(source=source, row=i+1, decision="rejected" if decisions[i] else "valid",
                               reasons=decisions[i], key=str(df.at[i, schema.key]) if schema.key in df else None,
                               original_values=original_rows[i],
                               normalization="Trim de chave e conversão numérica explícita; entrada original preservada"))

    # A row with an invalid counterpart is ineligible too; never silently inner-join it away.
    common = set.intersection(*(set(clean[s][schemas[s].key]) for s in clean))
    by_row = {(e["source"], e["row"]): e for e in ledger}
    for source, df in clean.items():
        key_col = schemas[source].key
        for i, row in df.iterrows():
            eligible = row[key_col] in common
            entry = by_row[source, i+1]
            entry["decision"] = "analyzed" if eligible else "unmatched"
            if not eligible:
                entry["reasons"].append("unmatched")
                issue(source, "unmatched", [i+1], row[key_col], "exclude_from_business_analysis")
        clean[source] = df[df[key_col].isin(common)]
        counts[source]["analyzed"] = len(clean[source])
        counts[source]["unmatched"] = counts[source]["valid"] - len(clean[source])
    blocked = blocked or (mode == "block" and bool(issues)) or not common
    if blocked:
        for count in counts.values():
            count["analyzed"] = 0
        for entry in ledger:
            if entry["decision"] == "analyzed":
                entry["decision"] = "withheld_run_blocked"
    return dict(frames=clean, issues=issues, ledger=ledger, counts=counts, blocked=blocked)
