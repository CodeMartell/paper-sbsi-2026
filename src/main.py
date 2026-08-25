"""
Robô de Relatórios Administrativos — Equipe 04.

Pipeline: Extrair -> Tratar -> Cruzar -> Analisar -> Identificar
divergências -> Gerar relatório.

Uso:
    python -m src.main
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.config import settings
from src.logger import get_logger, emitir_alerta_critico
from src.extractor import extrair_com_fallback, ExtracaoGERPError
from src.data_processor import (
    extrair_dados_financeiros,
    extrair_dados_producao,
    tratar_dados,
    cruzar_dados,
    analisar_e_identificar_divergencias,
)
from src.report_generator import gerar_relatorio


def run() -> int:
    settings.ensure_dirs()
    logger = get_logger()

    logger.info("=" * 70)
    logger.info("Iniciando execução do robô de Relatórios Administrativos — Equipe 04")
    logger.info("Fuso horário configurado: %s", settings.tz)

    try:
        # 1) EXTRAIR
        caminho_csv = extrair_com_fallback(settings, logger)
        logger.info("Arquivo financeiro utilizado: %s", caminho_csv)

        # 2) TRATAR (leitura + limpeza)
        df_financeiro_bruto = extrair_dados_financeiros(caminho_csv)
        df_producao_bruto = extrair_dados_producao(settings.producao_path)
        logger.info(
            "Dados lidos: %d projeto(s) financeiro(s), %d registro(s) de produção.",
            len(df_financeiro_bruto),
            len(df_producao_bruto),
        )

        df_financeiro, df_producao = tratar_dados(df_financeiro_bruto, df_producao_bruto)
        logger.debug("Dados tratados/normalizados com sucesso.")

        # 3) CRUZAR
        df_cruzado = cruzar_dados(df_financeiro, df_producao)
        logger.info("Cruzamento financeiro x produção realizado (%d linha(s)).", len(df_cruzado))

        # 4) ANALISAR + 5) IDENTIFICAR DIVERGÊNCIAS
        projetos = analisar_e_identificar_divergencias(df_cruzado, settings)

        for p in projetos:
            logger.info(
                "Projeto %s -> desvio financeiro %.1f%% | desvio produção %.1f%% | classificação: %s",
                p.codigo_projeto,
                p.desvio_financeiro_pct,
                p.desvio_producao_pct,
                p.classificacao,
            )
            if p.classificacao == "CRITICO":
                emitir_alerta_critico(
                    logger,
                    f"Projeto {p.codigo_projeto} — {p.motivo} "
                    f"(previsto={p.faturamento_previsto:.2f}, custo={p.custo_realizado:.2f}, "
                    f"status_producao={p.status_producao})",
                )

        # 6) GERAR RELATÓRIO
        ts = datetime.now(ZoneInfo(settings.tz)).strftime("%Y%m%d_%H%M%S")
        relatorio_path = Path(settings.output_dir) / f"relatorio_final_diretoria_{ts}.txt"
        gerar_relatorio(settings.template_path, projetos, relatorio_path, tz=settings.tz)
        logger.info("Relatório executivo gerado em: %s", relatorio_path)

        # Também salva o resultado estruturado (rastreabilidade / auditoria)
        resultado_json_path = Path(settings.output_dir) / f"resultado_analise_{ts}.json"
        resultado_json_path.write_text(
            json.dumps([p.as_dict() for p in projetos], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Resultado estruturado (auditoria/rastreabilidade) salvo em: %s", resultado_json_path)

        logger.info("Execução concluída com sucesso.")
        return 0

    except ExtracaoGERPError as exc:
        logger.error("Falha irrecuperável na extração de dados: %s", exc)
        emitir_alerta_critico(logger, f"Falha irrecuperável na extração de dados: {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001
        logger.exception("Erro inesperado durante a execução do robô: %s", exc)
        emitir_alerta_critico(logger, f"Erro inesperado durante a execução: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(run())
