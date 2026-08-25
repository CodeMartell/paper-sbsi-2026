from pathlib import Path

from src.data_processor import (
    tratar_dados,
    cruzar_dados,
    analisar_e_identificar_divergencias,
)
from src.config import Settings
from src.report_generator import gerar_relatorio, montar_divergencias, montar_resumo

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _projetos(df_financeiro, df_producao):
    fin, prod = tratar_dados(df_financeiro, df_producao)
    cruzado = cruzar_dados(fin, prod)
    return analisar_e_identificar_divergencias(cruzado, Settings())


def test_montar_resumo_contabiliza_classificacoes(df_financeiro, df_producao):
    projetos = _projetos(df_financeiro, df_producao)
    resumo = montar_resumo(projetos)
    assert "3 projeto" in resumo
    assert "1 crítico" in resumo or "1 crítico(s)" in resumo


def test_montar_divergencias_inclui_projeto_critico(df_financeiro, df_producao):
    projetos = _projetos(df_financeiro, df_producao)
    texto = montar_divergencias(projetos)
    assert "PROJ_REF_02" in texto
    assert "CRITICO" in texto


def test_gerar_relatorio_substitui_todos_os_placeholders(tmp_path, df_financeiro, df_producao):
    projetos = _projetos(df_financeiro, df_producao)
    saida = tmp_path / "relatorio.txt"

    caminho = gerar_relatorio(DATA_DIR / "modelo_relatorio_final_diretoria.txt", projetos, saida)

    conteudo = caminho.read_text(encoding="utf-8")
    for placeholder in ["{{SEMANA}}", "{{RESUMO}}", "{{INDICADORES}}", "{{DIVERGENCIAS}}", "{{VALIDACAO_HUMANA}}"]:
        assert placeholder not in conteudo
    assert "PROJ_REF_02" in conteudo
