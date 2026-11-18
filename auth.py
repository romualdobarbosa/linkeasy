import html
import json
import os
import secrets
import urllib.parse
import webbrowser
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
CALLBACK_HOST = "localhost"
CALLBACK_PORT = 8000
CALLBACK_PATH = "/callback"
REDIRECT_URI = f"http://{CALLBACK_HOST}:{CALLBACK_PORT}{CALLBACK_PATH}"
SCOPES = "openid profile w_member_social"
TOKEN_FILE = ".token.json"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
HTTP_TIMEOUT = 30  # segundos


class AuthError(Exception):
    """Falha no fluxo de autenticação, com mensagem pronta para o usuário."""


class CallbackServer(HTTPServer):
    """Servidor de callback do OAuth que guarda o resultado em atributos.

    `expected_state` é o state enviado na URL de autorização. Depois de um
    callback, `auth_code` tem o código (state válido) ou `error` tem a
    mensagem de falha.
    """

    def __init__(self, server_address, expected_state):
        super().__init__(server_address, CallbackHandler)
        self.expected_state = expected_state
        self.auth_code = None
        self.error = None


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != CALLBACK_PATH:
            self._reply(404, "Nao encontrado.")
            return

        params = urllib.parse.parse_qs(parsed.query)

        if "error" in params:
            error = params["error"][0]
            desc = params.get("error_description", ["sem descricao"])[0]
            self.server.error = f"Erro do LinkedIn: {error} ({desc})"
            self._reply(400, self.server.error)
            return

        state = params.get("state", [""])[0]
        if not state or not secrets.compare_digest(state, self.server.expected_state):
            self.server.error = "State ausente ou invalido no callback. Codigo descartado."
            self._reply(400, self.server.error)
            return

        code = params.get("code", [""])[0]
        if not code:
            self.server.error = "Callback sem codigo de autorizacao."
            self._reply(400, self.server.error)
            return

        self.server.auth_code = code
        self._reply(200, "Autenticado! Pode fechar essa aba.")

    def _reply(self, status, message):
        body = f"<!doctype html><meta charset='utf-8'><p>{html.escape(message)}</p>"
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format, *args):
        pass


def new_state():
    return secrets.token_urlsafe(32)


def get_auth_url(state):
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
    }
    return f"https://www.linkedin.com/oauth/v2/authorization?{urllib.parse.urlencode(params)}"


def exchange_code_for_token(code):
    try:
        response = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
            },
            timeout=HTTP_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise AuthError(f"Falha de rede ao trocar o codigo por token: {exc}") from exc

    if not response.ok:
        raise AuthError(
            f"LinkedIn recusou a troca do codigo por token "
            f"(HTTP {response.status_code}): {response.text[:500]}"
        )
    return response.json()


def save_token(token_data, path=None, now=None):
    """Grava o token com `obtained_at` (ISO 8601, UTC) e permissão 0600.

    Devolve o dicionário gravado.
    """
    path = path or TOKEN_FILE
    obtained_at = now or datetime.now(UTC)
    data = {**token_data, "obtained_at": obtained_at.isoformat()}
    fd = os.open(path, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    # O mode do os.open só vale na criação; se o arquivo já existia, corrige aqui.
    os.chmod(path, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2)
    return data


def expires_at(token_data):
    """Data de expiração (obtained_at + expires_in) ou None se faltar dado."""
    try:
        obtained = datetime.fromisoformat(token_data["obtained_at"])
        return obtained + timedelta(seconds=int(token_data["expires_in"]))
    except (KeyError, TypeError, ValueError):
        return None


def missing_credentials():
    """Nomes das variáveis de ambiente de credencial que estão vazias."""
    missing = []
    if not CLIENT_ID:
        missing.append("LINKEDIN_CLIENT_ID")
    if not CLIENT_SECRET:
        missing.append("LINKEDIN_CLIENT_SECRET")
    return missing


def main():
    missing = missing_credentials()
    if missing:
        print(f"Erro: faltam credenciais no ambiente (.env): {', '.join(missing)}.")
        return 2

    state = new_state()
    try:
        server = CallbackServer((CALLBACK_HOST, CALLBACK_PORT), state)
    except OSError as exc:
        print(f"Erro: nao consegui abrir o servidor de callback em {REDIRECT_URI}: {exc}")
        return 1

    print("Abrindo LinkedIn para autenticacao...")
    webbrowser.open(get_auth_url(state))
    print(f"Aguardando callback em {REDIRECT_URI} ...")
    try:
        while server.auth_code is None and server.error is None:
            server.handle_request()
    finally:
        server.server_close()

    if server.error:
        print(f"Erro: {server.error}")
        return 1

    print("Trocando codigo por token...")
    try:
        token_data = exchange_code_for_token(server.auth_code)
    except AuthError as exc:
        print(f"Erro: {exc}")
        return 1

    saved = save_token(token_data)
    print(f"Token salvo em {TOKEN_FILE}")
    expiry = expires_at(saved)
    if expiry:
        print(f"Expira em: {expiry.isoformat()}")
    else:
        print("Expiracao desconhecida (LinkedIn nao informou expires_in).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
