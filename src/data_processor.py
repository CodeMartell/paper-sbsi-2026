"""
Tratar -> Cruzar -> Analisar -> Identificar divergências.

Regras de negócio:

- Desvio financeiro (R$) = Custo_Realizado - Faturamento_Previsto
  Desvio financeiro (%)  = Desvio financeiro / Faturamento_Previsto * 100
  (positivo = custo estourou o faturamento previsto)

- Desvio de produção (un.) = Unidades_Planejadas - Unidades_Produzidas
  Desvio de produção (%)   = Desvio de produção / Unidades_Planejadas * 100
  (positivo = produção abaixo do planejado)

- Classificação por projeto:
    CRÍTICO  -> custo realizado > faturamento previsto  E  status de
                produção != "Normal" (ex.: "Atrasado"). Este é
                exatamente o cenário do PROJ_REF_02 descrito na
                avaliação.
    ATENCAO  -> desvio financeiro ou desvio de produção acima do
                limiar configurado (padrão 5%), mas sem configurar
                o caso crítico acima.
    NORMAL   -> dentro dos limiares e status de produção normal.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List

import pandas as pd
import math

from src.config import Settings, settings as default_settings


@dataclass
class ProjetoAnalisado:
    codigo_projeto: str
    faturamento_previsto: float
    custo_realizado: float
    horas_faturadas: float
    status_financeiro: str
    unidades_planejadas: float
    unidades_produzidas: float
    status_producao: str
    desvio_financeiro_valor: float
    desvio_financeiro_pct: float
    desvio_producao_valor: float
    desvio_producao_pct: float
    classificacao: str
    motivo: str

    def as_dict(self) -> dict:
        return asdict(self)


def extrair_dados_financeiros(csv_path: Path) -> pd.DataFrame:
    """Lê o CSV financeiro (separador ';', exportado do GERP simulado)."""
    try:
        raw = pd.read_csv(csv_path, sep=";", encoding="utf-8-sig", dtype=str, keep_default_na=False, header=None)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()
    df = raw.iloc[1:].reset_index(drop=True)
    df.columns = [str(c).strip() for c in raw.iloc[0]]
    return df


def extrair_dados_producao(xlsx_path: Path) -> pd.DataFrame:
    """Lê a planilha de produção física real."""
    raw = pd.read_excel(xlsx_path, sheet_name="Producao", dtype=str, keep_default_na=False, header=None)
    if raw.empty:
        return pd.DataFrame()
    df = raw.iloc[1:].reset_index(drop=True)
    df.columns = [str(c).strip() for c in raw.iloc[0]]
    return df


def tratar_dados(df_financeiro: pd.DataFrame, df_producao: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Limpeza/normalização básica: tipos numéricos, strings sem espaço, sem duplicatas."""
    fin = df_financeiro.copy()
    prod = df_producao.copy()

    fin["Codigo_Projeto"] = fin["Codigo_Projeto"].astype(str).str.strip()
    prod["Codigo_Projeto"] = prod["Codigo_Projeto"].astype(str).str.strip()

    for col in ["Faturamento_Previsto", "Custo_Realizado", "Horas_Faturadas"]:
        fin[col] = pd.to_numeric(fin[col], errors="coerce")

    for col in ["Unidades_Planejadas", "Unidades_Produzidas"]:
        prod[col] = pd.to_numeric(prod[col], errors="coerce")

    for raw in (df_financeiro, df_producao):
        normalized = raw.copy()
        normalized["Codigo_Projeto"] = normalized["Codigo_Projeto"].astype("string").str.strip()
        distinct = normalized.drop_duplicates()
        if distinct["Codigo_Projeto"].duplicated().any():
            raise ValueError("Conflicting duplicates require explicit quality validation")
    fin.attrs["identical_duplicates_removed"] = int(fin.duplicated().sum())
    prod.attrs["identical_duplicates_removed"] = int(prod.duplicated().sum())
    fin = fin.drop_duplicates(subset=["Codigo_Projeto"])
    prod = prod.drop_duplicates(subset=["Codigo_Projeto"])

    return fin, prod


def cruzar_dados(fin: pd.DataFrame, prod: pd.DataFrame) -> pd.DataFrame:
    """Cruza financeiro x produção pela chave Codigo_Projeto (outer join)."""
    cruzado = pd.merge(fin, prod, on="Codigo_Projeto", how="outer", indicator=True, validate="one_to_one")
    return cruzado


def _classificar(
    desvio_financeiro_valor: float,
    desvio_financeiro_pct: float,
    desvio_producao_pct: float,
    status_producao: str,
    limiar_fin: float,
    limiar_prod: float,
) -> tuple[str, str]:
    status_producao_norm = (status_producao or "").strip().lower()
    estourou_custo = desvio_financeiro_valor > 0

    if estourou_custo and status_producao_norm not in ("normal", ""):
        return (
            "CRITICO",
            f"Custo realizado excede o faturamento previsto (desvio de "
            f"{desvio_financeiro_pct:.1f}%) e produção com status '{status_producao}'.",
        )

    # Só sinaliza "atenção" para desvios desfavoráveis: custo estourando o
    # previsto além do limiar, ou produção abaixo do planejado além do
    # limiar (ou com status diferente de "Normal"). Um desvio favorável
    # (ex.: custo bem abaixo do previsto) não é tratado como problema.
    custo_acima_do_limiar = desvio_financeiro_pct >= limiar_fin
    producao_abaixo_do_limiar = desvio_producao_pct >= limiar_prod
    producao_com_status_atipico = status_producao_norm not in ("normal", "")

    if custo_acima_do_limiar or producao_abaixo_do_limiar or producao_com_status_atipico:
        return (
            "ATENCAO",
            f"Desvio financeiro de {desvio_financeiro_pct:+.1f}%, desvio de produção "
            f"de {desvio_producao_pct:+.1f}% e status de produção '{status_producao}'.",
        )

    return "NORMAL", "Dentro dos limiares esperados."


def analisar_e_identificar_divergencias(
    df_cruzado: pd.DataFrame, cfg: Settings = default_settings
) -> List[ProjetoAnalisado]:
    """Calcula desvios e classifica cada projeto. Retorna registros faltantes como divergência de integração."""
    resultados: List[ProjetoAnalisado] = []

    for _, row in df_cruzado.iterrows():
        codigo = row["Codigo_Projeto"]

        numeric = ["Faturamento_Previsto", "Custo_Realizado", "Horas_Faturadas",
                   "Unidades_Planejadas", "Unidades_Produzidas"]
        def number(value):
            try:
                parsed = float(value)
                return parsed if math.isfinite(parsed) else None
            except (TypeError, ValueError):
                return None
        values = [number(row.get(c)) for c in numeric]
        invalid = (row.get("_merge", "both") != "both" or any(v is None for v in values)
                   or values[0] == 0 or values[3] == 0
                   or pd.isna(row.get("Status_Producao")) or not str(row.get("Status_Producao", "")).strip())
        if invalid:
            resultados.append(ProjetoAnalisado(
                codigo_projeto=codigo, faturamento_previsto=values[0], custo_realizado=values[1],
                horas_faturadas=values[2], status_financeiro=str(row.get("Status_Financeiro", "")),
                unidades_planejadas=values[3], unidades_produzidas=values[4],
                status_producao=str(row.get("Status_Producao", "")),
                desvio_financeiro_valor=None, desvio_financeiro_pct=None,
                desvio_producao_valor=None, desvio_producao_pct=None,
                classificacao="DADOS_INVALIDOS", motivo="Dados financeiros/produção inválidos ou sem correspondência; indicadores não calculados."))
            continue

        faturamento_previsto = float(row["Faturamento_Previsto"])
        custo_realizado = float(row["Custo_Realizado"])
        unidades_planejadas = float(row["Unidades_Planejadas"])
        unidades_produzidas = float(row["Unidades_Produzidas"])
        status_producao = str(row["Status_Producao"])

        desvio_fin_valor = custo_realizado - faturamento_previsto
        desvio_fin_pct = (desvio_fin_valor / faturamento_previsto * 100) if faturamento_previsto else 0.0

        desvio_prod_valor = unidades_planejadas - unidades_produzidas
        desvio_prod_pct = (desvio_prod_valor / unidades_planejadas * 100) if unidades_planejadas else 0.0

        classificacao, motivo = _classificar(
            desvio_fin_valor,
            desvio_fin_pct,
            desvio_prod_pct,
            status_producao,
            cfg.limiar_desvio_financeiro_atencao,
            cfg.limiar_desvio_producao_atencao,
        )

        resultados.append(
            ProjetoAnalisado(
                codigo_projeto=codigo,
                faturamento_previsto=faturamento_previsto,
                custo_realizado=custo_realizado,
                horas_faturadas=float(row["Horas_Faturadas"]),
                status_financeiro=str(row["Status_Financeiro"]),
                unidades_planejadas=unidades_planejadas,
                unidades_produzidas=unidades_produzidas,
                status_producao=status_producao,
                desvio_financeiro_valor=desvio_fin_valor,
                desvio_financeiro_pct=desvio_fin_pct,
                desvio_producao_valor=desvio_prod_valor,
                desvio_producao_pct=desvio_prod_pct,
                classificacao=classificacao,
                motivo=motivo,
            )
        )

    return resultados
