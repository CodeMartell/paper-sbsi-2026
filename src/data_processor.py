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
    df = pd.read_csv(csv_path, sep=";", encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]
    return df


def extrair_dados_producao(xlsx_path: Path) -> pd.DataFrame:
    """Lê a planilha de produção física real."""
    df = pd.read_excel(xlsx_path, sheet_name="Producao")
    df.columns = [c.strip() for c in df.columns]
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

    fin = fin.drop_duplicates(subset=["Codigo_Projeto"])
    prod = prod.drop_duplicates(subset=["Codigo_Projeto"])

    return fin, prod


def cruzar_dados(fin: pd.DataFrame, prod: pd.DataFrame) -> pd.DataFrame:
    """Cruza financeiro x produção pela chave Codigo_Projeto (inner join)."""
    cruzado = pd.merge(fin, prod, on="Codigo_Projeto", how="outer", indicator=True)
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

        if row.get("_merge") == "left_only":
            resultados.append(
                ProjetoAnalisado(
                    codigo_projeto=codigo,
                    faturamento_previsto=float(row.get("Faturamento_Previsto") or 0),
                    custo_realizado=float(row.get("Custo_Realizado") or 0),
                    horas_faturadas=float(row.get("Horas_Faturadas") or 0),
                    status_financeiro=str(row.get("Status_Financeiro") or ""),
                    unidades_planejadas=0.0,
                    unidades_produzidas=0.0,
                    status_producao="SEM_DADOS_PRODUCAO",
                    desvio_financeiro_valor=0.0,
                    desvio_financeiro_pct=0.0,
                    desvio_producao_valor=0.0,
                    desvio_producao_pct=0.0,
                    classificacao="ATENCAO",
                    motivo="Projeto presente no financeiro, mas sem registro correspondente na produção.",
                )
            )
            continue

        if row.get("_merge") == "right_only":
            resultados.append(
                ProjetoAnalisado(
                    codigo_projeto=codigo,
                    faturamento_previsto=0.0,
                    custo_realizado=0.0,
                    horas_faturadas=0.0,
                    status_financeiro="SEM_DADOS_FINANCEIROS",
                    unidades_planejadas=float(row.get("Unidades_Planejadas") or 0),
                    unidades_produzidas=float(row.get("Unidades_Produzidas") or 0),
                    status_producao=str(row.get("Status_Producao") or ""),
                    desvio_financeiro_valor=0.0,
                    desvio_financeiro_pct=0.0,
                    desvio_producao_valor=0.0,
                    desvio_producao_pct=0.0,
                    classificacao="ATENCAO",
                    motivo="Projeto presente na produção, mas sem registro correspondente no financeiro.",
                )
            )
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
