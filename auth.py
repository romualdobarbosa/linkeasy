import os
import json
import urllib.parse
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv
import requests

load_dotenv()

CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8000/callback"
SCOPES = "openid profile w_member_social"
TOKEN_FILE = ".token.json"

auth_code = None


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if "code" in params:
            auth_code = params["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Autenticado! Pode fechar essa aba.")
        else:
            error = params.get("error", ["?"])[0]
            desc = params.get("error_description", ["sem descricao"])[0]
            print(f"Erro do LinkedIn: {error} — {desc}")
            self.send_response(400)
            self.end_headers()
            self.wfile.write(f"Erro: {error} — {desc}".encode())

    def log_message(self, format, *args):
        pass


def get_auth_url():
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": "romualdo_linkedin",
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
    print("Abrindo LinkedIn para autenticacao...")
    webbrowser.open(get_auth_url())

    server = HTTPServer(("localhost", 8000), CallbackHandler)
    print("Aguardando callback em http://localhost:8000/callback ...")
    server.handle_request()

    if not auth_code:
        print("Erro: nao foi possivel capturar o codigo de autorizacao.")
        return

    print("Trocando codigo por token...")
    token_data = exchange_code_for_token(auth_code)

    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)

    print(f"Token salvo em {TOKEN_FILE}")
    print(f"Expira em: {token_data.get('expires_in', '?')} segundos (~60 dias)")


if __name__ == "__main__":
    main()
