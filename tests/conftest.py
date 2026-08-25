import pandas as pd
import pytest


@pytest.fixture
def df_financeiro():
    return pd.DataFrame(
        {
            "Codigo_Projeto": ["PROJ_REF_01", "PROJ_REF_02", "PROJ_REF_03"],
            "Faturamento_Previsto": [500000, 800000, 1200000],
            "Custo_Realizado": [420000, 850000, 1100000],
            "Horas_Faturadas": [1200, 2100, 2800],
            "Status_Financeiro": ["Normal", "Acima_do_previsto", "Normal"],
        }
    )


@pytest.fixture
def df_producao():
    return pd.DataFrame(
        {
            "Codigo_Projeto": ["PROJ_REF_01", "PROJ_REF_02", "PROJ_REF_03"],
            "Semana": ["2026-W34", "2026-W34", "2026-W34"],
            "Unidades_Planejadas": [1000, 1500, 2200],
            "Unidades_Produzidas": [980, 1200, 2180],
            "Status_Producao": ["Normal", "Atrasado", "Normal"],
        }
    )
