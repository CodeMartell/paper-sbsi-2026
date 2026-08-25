"""
Gerar relatório — preenche modelo_relatorio_final_diretoria.txt com os
resultados da análise (Extrair -> Tratar -> Cruzar -> Analisar ->
Identificar divergências -> Gerar relatório).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List
from zoneinfo import ZoneInfo

from src.data_processor import ProjetoAnalisado


def _fmt_moeda(valor: float) -> str:
    texto = f"R$ {valor:,.2f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def montar_resumo(projetos: List[ProjetoAnalisado]) -> str:
    total = len(projetos)
    criticos = sum(1 for p in projetos if p.classificacao == "CRITICO")
    atencao = sum(1 for p in projetos if p.classificacao == "ATENCAO")
    normais = total - criticos - atencao
    return (
        f"Foram analisados {total} projeto(s) cruzando dados financeiros (GERP) "
        f"e dados de produção física real. Resultado da classificação: "
        f"{normais} normal(is), {atencao} em atenção e {criticos} crítico(s)."
    )


def montar_indicadores(projetos: List[ProjetoAnalisado]) -> str:
    linhas = []
    for p in projetos:
        linhas.append(
            f"- {p.codigo_projeto}: previsto {_fmt_moeda(p.faturamento_previsto)} | "
            f"custo {_fmt_moeda(p.custo_realizado)} | desvio financeiro "
            f"{p.desvio_financeiro_pct:+.1f}% | produção "
            f"{p.unidades_produzidas:.0f}/{p.unidades_planejadas:.0f} un. "
            f"({p.desvio_producao_pct:+.1f}%) | status produção: {p.status_producao}"
        )
    return "\n".join(linhas) if linhas else "Nenhum indicador disponível."


def montar_divergencias(projetos: List[ProjetoAnalisado]) -> str:
    divergentes = [p for p in projetos if p.classificacao != "NORMAL"]
    if not divergentes:
        return "Nenhuma divergência identificada no período."

    linhas = []
    for p in divergentes:
        linhas.append(f"[{p.classificacao}] {p.codigo_projeto}: {p.motivo}")
    return "\n".join(linhas)


def montar_validacao_humana(projetos: List[ProjetoAnalisado]) -> str:
    criticos = [p.codigo_projeto for p in projetos if p.classificacao == "CRITICO"]
    if criticos:
        return (
            "Recomenda-se validação do gestor responsável antes do fechamento contábil, "
            f"com atenção prioritária aos projetos críticos: {', '.join(criticos)}. "
            "Pendente de assinatura/validação humana."
        )
    return "Sem ocorrências críticas no período. Pendente de validação/ciência do gestor."


def gerar_relatorio(
    template_path: Path,
    projetos: List[ProjetoAnalisado],
    output_path: Path,
    tz: str = "America/Manaus",
) -> Path:
    template = template_path.read_text(encoding="utf-8")

    agora = datetime.now(ZoneInfo(tz))
    semana = agora.strftime("%Y-W%V")

    conteudo = (
        template.replace("{{SEMANA}}", semana)
        .replace("{{RESUMO}}", montar_resumo(projetos))
        .replace("{{INDICADORES}}", montar_indicadores(projetos))
        .replace("{{DIVERGENCIAS}}", montar_divergencias(projetos))
        .replace("{{VALIDACAO_HUMANA}}", montar_validacao_humana(projetos))
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(conteudo, encoding="utf-8")
    return output_path
