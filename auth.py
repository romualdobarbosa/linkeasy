import html
import json
import os
import secrets
import urllib.parse
import webbrowser
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
    response = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
    )
    response.raise_for_status()
    return response.json()


def main():
    state = new_state()
    print("Abrindo LinkedIn para autenticacao...")
    webbrowser.open(get_auth_url(state))

    server = CallbackServer((CALLBACK_HOST, CALLBACK_PORT), state)
    print(f"Aguardando callback em {REDIRECT_URI} ...")
    while server.auth_code is None and server.error is None:
        server.handle_request()
    server.server_close()

    if server.error:
        print(f"Erro: {server.error}")
        return 1

    print("Trocando codigo por token...")
    token_data = exchange_code_for_token(server.auth_code)

    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)

    print(f"Token salvo em {TOKEN_FILE}")
    print(f"Expira em: {token_data.get('expires_in', '?')} segundos (~60 dias)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
