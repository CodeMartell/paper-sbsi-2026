import time

from src.circuit_breaker import CircuitBreaker, CircuitState


def _breaker(tmp_path, threshold=3, timeout=60):
    return CircuitBreaker(
        state_file=tmp_path / "cb_state.json",
        failure_threshold=threshold,
        reset_timeout_seconds=timeout,
    )


def test_inicia_fechado_e_permite_requisicao(tmp_path):
    cb = _breaker(tmp_path)
    assert cb.state == CircuitState.CLOSED
    assert cb.allow_request() is True


def test_abre_apos_atingir_o_limiar_de_falhas(tmp_path):
    cb = _breaker(tmp_path, threshold=3)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED  # ainda não bateu o limiar
    cb.record_failure()
    assert cb.state == CircuitState.OPEN


def test_circuito_aberto_bloqueia_novas_tentativas_dentro_do_cooldown(tmp_path):
    cb = _breaker(tmp_path, threshold=1, timeout=60)
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.allow_request() is False


def test_circuito_vai_para_half_open_apos_cooldown(tmp_path):
    cb = _breaker(tmp_path, threshold=1, timeout=0)  # cooldown "zero" para o teste
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    time.sleep(0.01)
    assert cb.allow_request() is True
    assert cb.state == CircuitState.HALF_OPEN


def test_sucesso_fecha_o_circuito(tmp_path):
    cb = _breaker(tmp_path, threshold=1)
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    cb.record_success()
    assert cb.state == CircuitState.CLOSED


def test_estado_persiste_entre_instancias(tmp_path):
    state_file = tmp_path / "cb_state.json"
    cb1 = CircuitBreaker(state_file=state_file, failure_threshold=1, reset_timeout_seconds=60)
    cb1.record_failure()
    assert cb1.state == CircuitState.OPEN

    cb2 = CircuitBreaker(state_file=state_file, failure_threshold=1, reset_timeout_seconds=60)
    assert cb2.state == CircuitState.OPEN
