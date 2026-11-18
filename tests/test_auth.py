"""Testes do auth.py. Nada aqui fala com o LinkedIn nem abre navegador."""

import threading
import urllib.parse

import pytest
import requests

import auth

STATE = "state-de-teste-123"


@pytest.fixture
def callback_server():
    """Sobe o CallbackServer em porta livre numa thread e devolve (server, base_url)."""
    server = auth.CallbackServer(("127.0.0.1", 0), STATE)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    yield server, f"http://{host}:{port}"
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def _get(base_url, path, **params):
    query = urllib.parse.urlencode(params)
    return requests.get(f"{base_url}{path}?{query}", timeout=5)


# --- URL de autorização ---------------------------------------------------


def test_auth_url_leva_state_aleatorio():
    s1, s2 = auth.new_state(), auth.new_state()
    assert s1 != s2
    assert len(s1) >= 40  # token_urlsafe(32) gera ~43 caracteres

    query = urllib.parse.parse_qs(urllib.parse.urlparse(auth.get_auth_url(s1)).query)
    assert query["state"] == [s1]
    assert query["redirect_uri"] == [auth.REDIRECT_URI]
    assert query["response_type"] == ["code"]


# --- Callback --------------------------------------------------------------


def test_callback_com_state_certo_captura_codigo(callback_server):
    server, base = callback_server
    resp = _get(base, "/callback", code="codigo-ficticio", state=STATE)
    assert resp.status_code == 200
    assert server.auth_code == "codigo-ficticio"
    assert server.error is None


@pytest.mark.parametrize("params", [{"code": "abc"}, {"code": "abc", "state": "outro-state"}])
def test_callback_com_state_ausente_ou_errado_descarta_codigo(callback_server, params):
    server, base = callback_server
    resp = _get(base, "/callback", **params)
    assert resp.status_code == 400
    assert "state" in resp.text.lower()
    assert server.auth_code is None
    assert server.error


def test_callback_sem_codigo_da_400(callback_server):
    server, base = callback_server
    resp = _get(base, "/callback", state=STATE)
    assert resp.status_code == 400
    assert server.auth_code is None


def test_callback_com_erro_do_linkedin_da_400(callback_server):
    server, base = callback_server
    resp = _get(
        base,
        "/callback",
        error="user_cancelled_login",
        error_description="O usuario cancelou",
        state=STATE,
    )
    assert resp.status_code == 400
    assert "user_cancelled_login" in resp.text
    assert server.auth_code is None
    assert "user_cancelled_login" in server.error


def test_callback_escapa_html_do_erro(callback_server):
    _, base = callback_server
    resp = _get(base, "/callback", error="<script>alert(1)</script>", state=STATE)
    assert resp.status_code == 400
    assert "<script>" not in resp.text
    assert "&lt;script&gt;" in resp.text


def test_callback_fora_do_path_da_404(callback_server):
    server, base = callback_server
    resp = _get(base, "/outra-coisa", code="abc", state=STATE)
    assert resp.status_code == 404
    assert server.auth_code is None
    assert server.error is None
