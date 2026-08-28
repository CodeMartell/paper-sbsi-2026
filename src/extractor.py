"""
Extrair — automação da interface web simulada (gerp_fake.html).

Usa Playwright (headless Chromium) para:
  1. Acessar a URL do GERP simulado (GERP_URL);
  2. Autenticar com as credenciais do .env;
  3. Clicar em "Exportar dados", disparando o download do CSV;
  4. Salvar o CSV baixado no diretório de dados do robô.

Isso cumpre o requisito da avaliação de que o robô "deverá interagir
com essa interface web local simulada para realizar o login e a
simulação de download dos dados".
"""

from __future__ import annotations

import logging
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from src.config import Settings, settings as default_settings
from src.circuit_breaker import CircuitBreaker


class ExtracaoGERPError(RuntimeError):
    """Erro ao extrair dados do sistema GERP simulado."""


def extrair_via_gerp_fake(
    cfg: Settings = default_settings, logger: logging.Logger | None = None
) -> Path:
    """Faz login no GERP simulado e captura o download do CSV de faturamento.

    Retorna o caminho do arquivo baixado (salvo em cfg.data_dir).
    """
    log = logger or logging.getLogger("equipe04")
    destino = Path(cfg.data_dir) / cfg.financeiro_csv

    log.info("Iniciando extração via GERP simulado: %s", cfg.gerp_url)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=cfg.headless, slow_mo=0 if cfg.headless else 800)
        page = browser.new_page(accept_downloads=True)
        try:
            page.goto(cfg.gerp_url, wait_until="load", timeout=15000)

            page.fill("#u", cfg.gerp_user)
            page.fill("#p", cfg.gerp_password)
            page.click("button")

            page.wait_for_selector("#app", state="visible", timeout=5000)
            log.info("Login realizado com sucesso no GERP simulado.")

            with page.expect_download(timeout=10000) as download_info:
                page.click("text=Exportar dados")
            download = download_info.value

            download.save_as(str(destino))
            log.info("Download simulado concluído: %s", destino)

        except PlaywrightTimeoutError as exc:
            log.error("Timeout ao interagir com o GERP simulado: %s", exc)
            raise ExtracaoGERPError(
                f"Timeout ao interagir com o GERP simulado: {exc}"
            ) from exc
        finally:
            browser.close()

    if not destino.exists():
        raise ExtracaoGERPError(f"Arquivo esperado não foi baixado: {destino}")

    return destino


def extrair_com_fallback(
    cfg: Settings = default_settings, logger: logging.Logger | None = None
) -> Path:
    """Tenta extrair via automação web protegida por Circuit Breaker; em
    caso de falha (ou circuito aberto), cai para o CSV já fornecido
    localmente (fail-safe), registrando o ocorrido no log.

    Fluxo:
      1. Consulta o circuit breaker: se o circuito estiver ABERTO (várias
         falhas recentes), nem tenta acessar o GERP — usa o fallback
         direto, evitando martelar um sistema já indisponível.
      2. Se permitido (FECHADO ou HALF_OPEN), tenta a extração real.
         Sucesso fecha o circuito; falha incrementa o contador e pode
         abrir o circuito.
      3. Em qualquer falha (ou circuito aberto), usa o CSV local como
         contingência, deixando claro nos logs que a extração
         automatizada não foi bem-sucedida.
    """
    log = logger or logging.getLogger("equipe04")
    breaker = CircuitBreaker(
        state_file=Path(cfg.logs_dir) / "circuit_breaker_state.json",
        failure_threshold=3,
        reset_timeout_seconds=60,
        logger=log,
    )

    caminho_local = Path(cfg.data_dir) / cfg.financeiro_csv

    if breaker.allow_request():
        try:
            caminho = extrair_via_gerp_fake(cfg, log)
            breaker.record_success()
            return caminho
        except Exception as exc:  # noqa: BLE001
            breaker.record_failure()
            log.warning(
                "Extração automatizada via GERP falhou (%s). Utilizando arquivo local já disponível como contingência.",
                exc,
            )
    else:
        log.info(
            "Circuit breaker impediu nova tentativa de acesso ao GERP; usando fallback local diretamente."
        )

    if not caminho_local.exists():
        raise ExtracaoGERPError(
            "Extração via GERP falhou (ou circuito aberto) e não há arquivo local de contingência disponível."
        )
    return caminho_local
