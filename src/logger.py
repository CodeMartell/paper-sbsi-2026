"""
Logging e alertas — Equipe 04.

Requisito 4.4 da avaliação: o robô deve registrar dados processados,
cálculos, divergências, erros e resultado final, além de possuir um
mecanismo de alerta para situações críticas.

- Log em arquivo (rotativo por execução, timestampado) + console.
- ALERTA CRÍTICO é logado em nível CRITICAL e também replicado em um
  arquivo separado alerts.log, para que a diretoria/ops consiga varrer
  só os alertas sem precisar ler o log completo.
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.config import settings


class _TZFormatter(logging.Formatter):
    """Formatter que respeita o fuso horário exigido (America/Manaus)."""

    def __init__(self, fmt: str, tz_name: str):
        super().__init__(fmt)
        self._tz = ZoneInfo(tz_name)

    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=self._tz)
        return dt.strftime(datefmt or "%Y-%m-%d %H:%M:%S %Z")


def get_logger(name: str = "equipe04") -> logging.Logger:
    settings.ensure_dirs()
    logger = logging.getLogger(name)

    if logger.handlers:
        # já configurado (evita handlers duplicados em reimportações/testes)
        return logger

    logger.setLevel(logging.DEBUG)

    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    formatter = _TZFormatter(fmt, settings.tz)

    run_ts = datetime.now(ZoneInfo(settings.tz)).strftime("%Y%m%dT%H%M%S")

    # Console
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # Log completo da execução
    file_handler = logging.FileHandler(Path(settings.logs_dir) / f"execucao_{run_ts}.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Log dedicado a alertas críticos (acumulativo entre execuções)
    alert_handler = logging.FileHandler(Path(settings.logs_dir) / "alerts.log", encoding="utf-8")
    alert_handler.setLevel(logging.CRITICAL)
    alert_handler.setFormatter(formatter)
    logger.addHandler(alert_handler)

    return logger


def emitir_alerta_critico(logger: logging.Logger, mensagem: str) -> None:
    """Ponto único de emissão de alertas críticos (log em nível CRITICAL)."""
    logger.critical("ALERTA CRÍTICO — %s", mensagem)
