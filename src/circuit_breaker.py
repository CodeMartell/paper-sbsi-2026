"""
Circuit Breaker — protege o pipeline contra falhas repetidas de acesso ao
GERP simulado.

Estados clássicos do padrão Circuit Breaker:
  - FECHADO (CLOSED): funcionamento normal, tenta acessar o GERP.
  - ABERTO (OPEN): após N falhas seguidas, para de tentar acessar o GERP
    por um tempo (cooldown) e usa direto o fallback (arquivo local),
    evitando martelar um sistema que já está indisponível.
  - MEIO-ABERTO (HALF_OPEN): passado o cooldown, permite UMA tentativa de
    acesso real para verificar se o GERP voltou. Se der certo, fecha o
    circuito de novo; se falhar, reabre e reinicia o cooldown.

O estado é persistido em um arquivo JSON (`logs/circuit_breaker_state.json`)
para que decisões tomadas em uma execução (ex.: container) sejam
respeitadas em execuções seguintes dentro da janela de cooldown.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, asdict
from pathlib import Path


class CircuitState:
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass
class _PersistedState:
    state: str = CircuitState.CLOSED
    failure_count: int = 0
    opened_at: float | None = None


class CircuitBreaker:
    """Circuit breaker simples, com estado persistido em disco."""

    def __init__(
        self,
        state_file: Path,
        failure_threshold: int = 3,
        reset_timeout_seconds: int = 60,
        logger: logging.Logger | None = None,
    ):
        self.state_file = Path(state_file)
        self.failure_threshold = failure_threshold
        self.reset_timeout_seconds = reset_timeout_seconds
        self.log = logger or logging.getLogger("equipe04")
        self._state = self._load()

    # ---------- persistência ----------

    def _load(self) -> _PersistedState:
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                return _PersistedState(**data)
            except Exception:  # noqa: BLE001
                return _PersistedState()
        return _PersistedState()

    def _save(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(asdict(self._state)), encoding="utf-8")

    # ---------- máquina de estados ----------

    def allow_request(self) -> bool:
        """Decide se a tentativa real de acesso ao GERP deve ser feita."""
        if self._state.state == CircuitState.CLOSED:
            return True

        if self._state.state == CircuitState.OPEN:
            tempo_aberto = time.time() - (self._state.opened_at or 0)
            if tempo_aberto >= self.reset_timeout_seconds:
                self.log.info(
                    "Circuit breaker: cooldown de %ss expirado — passando para HALF_OPEN "
                    "(uma tentativa de teste será permitida).",
                    self.reset_timeout_seconds,
                )
                self._state.state = CircuitState.HALF_OPEN
                self._save()
                return True
            self.log.warning(
                "Circuit breaker ABERTO — pulando tentativa de acesso ao GERP "
                "(faltam %.0fs para novo teste). Usando fallback direto.",
                self.reset_timeout_seconds - tempo_aberto,
            )
            return False

        # HALF_OPEN: já foi liberado para uma tentativa de teste.
        return True

    def record_success(self) -> None:
        if self._state.state != CircuitState.CLOSED:
            self.log.info("Circuit breaker: acesso ao GERP bem-sucedido — fechando o circuito.")
        self._state = _PersistedState(state=CircuitState.CLOSED, failure_count=0, opened_at=None)
        self._save()

    def record_failure(self) -> None:
        if self._state.state == CircuitState.HALF_OPEN:
            self.log.warning("Circuit breaker: teste em HALF_OPEN falhou — reabrindo o circuito.")
            self._state = _PersistedState(state=CircuitState.OPEN, failure_count=self.failure_threshold, opened_at=time.time())
            self._save()
            return

        self._state.failure_count += 1
        if self._state.failure_count >= self.failure_threshold:
            self.log.error(
                "Circuit breaker: %d falha(s) consecutiva(s) atingida(s) — abrindo o circuito por %ss.",
                self._state.failure_count,
                self.reset_timeout_seconds,
            )
            self._state.state = CircuitState.OPEN
            self._state.opened_at = time.time()
        self._save()

    @property
    def state(self) -> str:
        return self._state.state
