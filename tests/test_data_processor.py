from pathlib import Path

import pandas as pd

from src.config import Settings
from src.data_processor import (
    extrair_dados_financeiros,
    extrair_dados_producao,
    tratar_dados,
    cruzar_dados,
    analisar_e_identificar_divergencias,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


# ---------- Leitura dos dados ----------

def test_extrair_dados_financeiros_le_csv_com_ponto_e_virgula():
    df = extrair_dados_financeiros(DATA_DIR / "GERP_faturamento_bruto.csv")
    assert list(df.columns) == [
        "Codigo_Projeto",
        "Faturamento_Previsto",
        "Custo_Realizado",
        "Horas_Faturadas",
        "Status_Financeiro",
    ]
    assert len(df) == 3
    assert "PROJ_REF_02" in df["Codigo_Projeto"].values


def test_extrair_dados_producao_le_xlsx():
    df = extrair_dados_producao(DATA_DIR / "producao_fisica_real.xlsx")
    assert len(df) == 3
    assert "Unidades_Produzidas" in df.columns


# ---------- Tratamento ----------

def test_tratar_dados_normaliza_tipos_e_remove_duplicatas(df_financeiro, df_producao):
    df_financeiro_dup = pd.concat([df_financeiro, df_financeiro.iloc[[0]]], ignore_index=True)
    fin, prod = tratar_dados(df_financeiro_dup, df_producao)

    assert len(fin) == 3  # duplicata removida
    assert pd.api.types.is_numeric_dtype(fin["Faturamento_Previsto"])
    assert pd.api.types.is_numeric_dtype(prod["Unidades_Planejadas"])


# ---------- Cruzamento ----------

def test_cruzar_dados_junta_pela_chave_codigo_projeto(df_financeiro, df_producao):
    fin, prod = tratar_dados(df_financeiro, df_producao)
    cruzado = cruzar_dados(fin, prod)

    assert len(cruzado) == 3
    linha_02 = cruzado[cruzado["Codigo_Projeto"] == "PROJ_REF_02"].iloc[0]
    assert linha_02["Custo_Realizado"] == 850000
    assert linha_02["Unidades_Produzidas"] == 1200


def test_cruzar_dados_preserva_projeto_sem_correspondencia(df_financeiro, df_producao):
    df_producao_incompleto = df_producao[df_producao["Codigo_Projeto"] != "PROJ_REF_03"]
    fin, prod = tratar_dados(df_financeiro, df_producao_incompleto)
    cruzado = cruzar_dados(fin, prod)

    linha_03 = cruzado[cruzado["Codigo_Projeto"] == "PROJ_REF_03"].iloc[0]
    assert linha_03["_merge"] == "left_only"


# ---------- Cálculo de desvios e identificação de divergências ----------

def test_calculo_de_desvios(df_financeiro, df_producao):
    fin, prod = tratar_dados(df_financeiro, df_producao)
    cruzado = cruzar_dados(fin, prod)
    resultados = {p.codigo_projeto: p for p in analisar_e_identificar_divergencias(cruzado, Settings())}

    ref02 = resultados["PROJ_REF_02"]
    assert ref02.desvio_financeiro_valor == 50000  # 850000 - 800000
    assert round(ref02.desvio_financeiro_pct, 2) == 6.25  # 50000 / 800000 * 100
    assert ref02.desvio_producao_valor == 300  # 1500 - 1200
    assert round(ref02.desvio_producao_pct, 2) == 20.0


def test_projeto_ref_02_e_classificado_como_critico(df_financeiro, df_producao):
    """Caso crítico descrito na avaliação: previsto (800k) < custo (850k) e status 'Atrasado'."""
    fin, prod = tratar_dados(df_financeiro, df_producao)
    cruzado = cruzar_dados(fin, prod)
    resultados = {p.codigo_projeto: p for p in analisar_e_identificar_divergencias(cruzado, Settings())}

    assert resultados["PROJ_REF_02"].classificacao == "CRITICO"


def test_projetos_normais_nao_sao_marcados_como_criticos(df_financeiro, df_producao):
    fin, prod = tratar_dados(df_financeiro, df_producao)
    cruzado = cruzar_dados(fin, prod)
    resultados = {p.codigo_projeto: p for p in analisar_e_identificar_divergencias(cruzado, Settings())}

    assert resultados["PROJ_REF_01"].classificacao == "NORMAL"
    assert resultados["PROJ_REF_03"].classificacao == "NORMAL"


def test_projeto_sem_dados_de_producao_gera_divergencia_de_integracao(df_financeiro, df_producao):
    df_producao_incompleto = df_producao[df_producao["Codigo_Projeto"] != "PROJ_REF_01"]
    fin, prod = tratar_dados(df_financeiro, df_producao_incompleto)
    cruzado = cruzar_dados(fin, prod)
    resultados = {p.codigo_projeto: p for p in analisar_e_identificar_divergencias(cruzado, Settings())}

    assert resultados["PROJ_REF_01"].classificacao == "ATENCAO"
    assert "produção" in resultados["PROJ_REF_01"].motivo.lower()
