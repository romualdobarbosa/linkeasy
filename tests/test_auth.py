"""Testes do auth.py. Nada aqui fala com o LinkedIn nem abre navegador."""

import json
import os
import stat
import threading
import urllib.parse
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import requests
import responses

import auth

STATE = "state-de-teste-123"


@pytest.fixture(autouse=True)
def isolar_arquivos(monkeypatch, tmp_path):
    """Nenhum teste deste arquivo pode tocar no .token.json real do repositório."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(auth, "TOKEN_FILE", str(tmp_path / "token-ficticio.json"))


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


# --- Troca de código por token ----------------------------------------------


@pytest.fixture
def credenciais_ficticias(monkeypatch):
    monkeypatch.setattr(auth, "CLIENT_ID", "client-id-ficticio")
    monkeypatch.setattr(auth, "CLIENT_SECRET", "client-secret-ficticio")


@responses.activate
def test_troca_de_codigo_envia_campos_certos(credenciais_ficticias):
    responses.post(auth.TOKEN_URL, json={"access_token": "tok", "expires_in": 5184000})

    data = auth.exchange_code_for_token("codigo-ficticio")

    assert data == {"access_token": "tok", "expires_in": 5184000}
    body = urllib.parse.parse_qs(responses.calls[0].request.body)
    assert body == {
        "grant_type": ["authorization_code"],
        "code": ["codigo-ficticio"],
        "redirect_uri": [auth.REDIRECT_URI],
        "client_id": ["client-id-ficticio"],
        "client_secret": ["client-secret-ficticio"],
    }


@responses.activate
def test_troca_de_codigo_com_erro_http(credenciais_ficticias):
    responses.post(auth.TOKEN_URL, status=401, json={"error": "invalid_client"})

    with pytest.raises(auth.AuthError, match="HTTP 401.*invalid_client"):
        auth.exchange_code_for_token("codigo-ficticio")


@responses.activate
def test_troca_de_codigo_com_falha_de_rede(credenciais_ficticias):
    responses.post(auth.TOKEN_URL, body=requests.ConnectionError("sem rede"))

    with pytest.raises(auth.AuthError, match="rede"):
        auth.exchange_code_for_token("codigo-ficticio")


def test_troca_de_codigo_usa_timeout(monkeypatch, credenciais_ficticias):
    chamadas = {}

    class Resp:
        ok = True

        def json(self):
            return {"access_token": "tok"}

    def fake_post(url, **kwargs):
        chamadas.update(kwargs)
        return Resp()

    monkeypatch.setattr(auth.requests, "post", fake_post)
    auth.exchange_code_for_token("x")
    assert chamadas["timeout"] == auth.HTTP_TIMEOUT


# --- Gravação do token -------------------------------------------------------


def test_save_token_grava_obtained_at_e_modo_0600(tmp_path):
    path = tmp_path / "token.json"
    now = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)

    saved = auth.save_token({"access_token": "tok", "expires_in": 3600}, path=path, now=now)

    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    on_disk = json.loads(path.read_text())
    assert on_disk == saved
    assert on_disk["obtained_at"] == "2026-01-02T03:04:05+00:00"
    assert on_disk["expires_in"] == 3600
    assert auth.expires_at(on_disk) == now + timedelta(seconds=3600)


def test_save_token_corrige_permissao_de_arquivo_existente(tmp_path):
    path = tmp_path / "token.json"
    path.write_text("velho")
    path.chmod(0o644)

    saved = auth.save_token({"access_token": "tok"}, path=path)

    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    assert json.loads(path.read_text()) == saved
    assert datetime.fromisoformat(saved["obtained_at"]).tzinfo is not None
    assert auth.expires_at(saved) is None


# --- main ---------------------------------------------------------------------


@pytest.fixture
def main_isolado(monkeypatch, credenciais_ficticias):
    """Prepara main() sem navegador, sem porta 8000 e sem tocar no .token.json real.

    Devolve uma função que define o que o "callback" vai entregar.
    """
    abertos = []
    monkeypatch.setattr(auth.webbrowser, "open", abertos.append)
    monkeypatch.setattr(auth, "CALLBACK_PORT", 0)

    def configurar(auth_code=None, error=None):
        class ServidorFalso(auth.CallbackServer):
            def handle_request(self):
                self.auth_code, self.error = auth_code, error

        monkeypatch.setattr(auth, "CallbackServer", ServidorFalso)
        return abertos

    return configurar


@pytest.mark.parametrize("faltando", ["CLIENT_ID", "CLIENT_SECRET"])
def test_main_sem_credenciais_falha_antes_do_navegador(monkeypatch, capsys, faltando):
    abertos = []
    monkeypatch.setattr(auth.webbrowser, "open", abertos.append)
    monkeypatch.setattr(auth, "CLIENT_ID", "id")
    monkeypatch.setattr(auth, "CLIENT_SECRET", "secret")
    monkeypatch.setattr(auth, faltando, None)

    assert auth.main() != 0
    assert abertos == []
    assert f"LINKEDIN_{faltando}" in capsys.readouterr().out


@responses.activate
def test_main_fluxo_completo_salva_token(main_isolado, capsys):
    abertos = main_isolado(auth_code="codigo-ficticio")
    responses.post(auth.TOKEN_URL, json={"access_token": "tok", "expires_in": 3600})

    assert auth.main() == 0

    assert len(abertos) == 1
    assert "state=" in abertos[0]
    saved = json.loads(Path(auth.TOKEN_FILE).read_text())
    assert saved["access_token"] == "tok"
    assert "obtained_at" in saved
    assert stat.S_IMODE(os.stat(auth.TOKEN_FILE).st_mode) == 0o600
    out = capsys.readouterr().out
    assert f"Expira em: {auth.expires_at(saved).isoformat()}" in out


@responses.activate
def test_main_sem_expires_in_avisa(main_isolado, capsys):
    main_isolado(auth_code="codigo-ficticio")
    responses.post(auth.TOKEN_URL, json={"access_token": "tok"})

    assert auth.main() == 0
    assert "Expiracao desconhecida" in capsys.readouterr().out


def test_main_com_erro_no_callback_sai_com_erro(main_isolado, capsys):
    main_isolado(error="Erro do LinkedIn: user_cancelled_login (cancelou)")

    assert auth.main() != 0
    assert "user_cancelled_login" in capsys.readouterr().out
    assert not os.path.exists(auth.TOKEN_FILE)


@responses.activate
def test_main_com_erro_na_troca_sai_com_erro(main_isolado, capsys):
    main_isolado(auth_code="codigo-ficticio")
    responses.post(auth.TOKEN_URL, status=400, json={"error": "invalid_grant"})

    assert auth.main() != 0
    assert "invalid_grant" in capsys.readouterr().out
    assert not os.path.exists(auth.TOKEN_FILE)


def test_main_com_porta_ocupada_sai_com_erro(monkeypatch, capsys, credenciais_ficticias):
    abertos = []
    monkeypatch.setattr(auth.webbrowser, "open", abertos.append)

    def explode(*args, **kwargs):
        raise OSError("Address already in use")

    monkeypatch.setattr(auth, "CallbackServer", explode)

    assert auth.main() != 0
    assert abertos == []
    assert "Address already in use" in capsys.readouterr().out
