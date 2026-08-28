"""
Configuração central da automação — Equipe 04.

Todas as variáveis sensíveis/ambientais (URLs, credenciais, caminhos,
fuso horário e limiares de negócio) vêm exclusivamente do .env,
conforme exigido pela Avaliação 03 (item 4.2 — Docker / variáveis de ambiente).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _base_dir() -> Path:
    # Raiz do projeto (um nível acima de /src)
    return Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    # Sistema GERP simulado
    gerp_url: str = field(
        default_factory=lambda: os.getenv(
            "GERP_URL", "http://localhost:8000/gerp_fake.html"
        )
    )
    gerp_user: str = field(default_factory=lambda: os.getenv("GERP_USER", "aluno"))
    gerp_password: str = field(
        default_factory=lambda: os.getenv("GERP_PASSWORD", "avaliacao2026")
    )

    # Fuso horário
    tz: str = field(default_factory=lambda: os.getenv("TZ", "America/Manaus"))

    # Diretórios
    data_dir: Path = field(
        default_factory=lambda: Path(os.getenv("DATA_DIR", str(_base_dir() / "data")))
    )
    output_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("OUTPUT_DIR", str(_base_dir() / "output"))
        )
    )
    logs_dir: Path = field(
        default_factory=lambda: Path(os.getenv("LOGS_DIR", str(_base_dir() / "logs")))
    )

    # Nomes de arquivo
    financeiro_csv: str = field(
        default_factory=lambda: os.getenv(
            "FINANCEIRO_CSV", "GERP_faturamento_bruto.csv"
        )
    )
    producao_xlsx: str = field(
        default_factory=lambda: os.getenv("PRODUCAO_XLSX", "producao_fisica_real.xlsx")
    )
    template_relatorio: str = field(
        default_factory=lambda: os.getenv(
            "TEMPLATE_RELATORIO", "modelo_relatorio_final_diretoria.txt"
        )
    )

    # Modo do navegador (Playwright) — true = invisível (Docker/CI), false = visível (debug local)
    headless: bool = field(
        default_factory=lambda: os.getenv("HEADLESS", "true").strip().lower() != "false"
    )

    # Regras de negócio (limiares em %)
    limiar_desvio_financeiro_atencao: float = field(
        default_factory=lambda: float(
            os.getenv("LIMIAR_DESVIO_FINANCEIRO_ATENCAO", "5")
        )
    )
    limiar_desvio_producao_atencao: float = field(
        default_factory=lambda: float(os.getenv("LIMIAR_DESVIO_PRODUCAO_ATENCAO", "5"))
    )

    def ensure_dirs(self) -> None:
        for d in (self.output_dir, self.logs_dir):
            Path(d).mkdir(parents=True, exist_ok=True)

    @property
    def financeiro_path(self) -> Path:
        return Path(self.data_dir) / self.financeiro_csv

    @property
    def producao_path(self) -> Path:
        return Path(self.data_dir) / self.producao_xlsx

    @property
    def template_path(self) -> Path:
        return Path(self.data_dir) / self.template_relatorio


settings = Settings()
