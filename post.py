import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN_FILE = ".token.json"
QUEUE_DIR = Path("posting/queue")
PUBLISHED_DIR = Path("posting/published")
PERSON_ID = os.getenv("LINKEDIN_PERSON_ID")

API_BASE = "https://api.linkedin.com/rest"
# Versão da API (header LinkedIn-Version, formato AAAAMM). Última verificação: 2025-06.
# O LinkedIn tira versões de suporte em ~1 ano; quando isso acontecer a API passa a recusar
# as chamadas e é preciso subir esta data. Não deu para conferir sem token: a API responde
# 401 EMPTY_ACCESS_TOKEN antes de validar a versão.
LINKEDIN_VERSION = "202506"

TIMEOUT = (10, 60)  # (conexão, leitura) em segundos
MAX_ATTEMPTS = 3
BACKOFF_BASE = 2.0  # segundos; dobra a cada tentativa
MAX_BACKOFF = 60.0


class PostError(Exception):
    """Erro esperado: vira mensagem curta no terminal e código de saída != 0."""


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


def _wait_time(response: requests.Response | None, attempt: int) -> float:
    if response is not None:
        retry_after = response.headers.get("Retry-After", "")
        if retry_after.strip().isdigit():
            return min(float(retry_after), MAX_BACKOFF)
    return min(BACKOFF_BASE * 2 ** (attempt - 1), MAX_BACKOFF)


def check_response(response: requests.Response, what: str) -> None:
    if response.status_code == 401:
        raise PostError("token expirado ou inválido, rode `uv run auth.py`")
    if not response.ok:
        raise PostError(f"{what} falhou: HTTP {response.status_code}: {response.text}")


def request_with_retry(
    method: str, url: str, what: str, *, retry_server_errors: bool = True, **kwargs
) -> requests.Response:
    """Faz a requisição com timeout e retenta 429 (e 5xx/queda de rede, se permitido).

    Com retry_server_errors=False só retenta 429 e falha ao conectar (ConnectTimeout),
    casos em que o servidor com certeza não processou o pedido.
    """
    kwargs.setdefault("timeout", TIMEOUT)
    for attempt in range(1, MAX_ATTEMPTS + 1):
        last = attempt == MAX_ATTEMPTS
        try:
            response = requests.request(method, url, **kwargs)
        except requests.ConnectTimeout as exc:
            if last:
                raise PostError(f"{what} falhou: sem conexão com o LinkedIn ({exc})") from None
            _sleep(_wait_time(None, attempt))
            continue
        except requests.RequestException as exc:
            if last or not retry_server_errors:
                raise PostError(f"{what} falhou: erro de rede ({exc})") from None
            _sleep(_wait_time(None, attempt))
            continue

        status = response.status_code
        retryable = status == 429 or (retry_server_errors and status >= 500)
        if retryable and not last:
            wait = _wait_time(response, attempt)
            print(f"{what}: HTTP {status}, tentando de novo em {wait:.0f}s.", file=sys.stderr)
            _sleep(wait)
            continue
        if status >= 500 and not retry_server_errors:
            raise PostError(
                f"{what} falhou: HTTP {status}: {response.text}\n"
                "O post pode ter sido criado mesmo assim. Confira no LinkedIn antes de repetir."
            )
        check_response(response, what)
        return response
    raise AssertionError("inalcançável")  # pragma: no cover


def api_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "LinkedIn-Version": LINKEDIN_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
    }


def load_token():
    with open(TOKEN_FILE) as f:
        return json.load(f)["access_token"]


def parse_post(file: Path):
    content = file.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return None, content.strip()

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None, content.strip()

    frontmatter = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            frontmatter[key.strip()] = value.strip()

    body = parts[2].strip()
    return frontmatter, body


def is_due(scheduled_at: str) -> bool:
    try:
        scheduled = datetime.strptime(scheduled_at, "%Y-%m-%d %H:%M")
        return datetime.now() >= scheduled
    except ValueError:
        return False


def upload_image(token: str, image_path: Path) -> str:
    init_response = request_with_retry(
        "POST",
        f"{API_BASE}/images?action=initializeUpload",
        "initializeUpload",
        headers=api_headers(token),
        json={"initializeUploadRequest": {"owner": f"urn:li:person:{PERSON_ID}"}},
    )
    data = init_response.json()["value"]
    upload_url = data["uploadUrl"]
    image_urn = data["image"]

    request_with_retry(
        "PUT",
        upload_url,
        f"upload de {image_path.name}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/octet-stream",
        },
        # bytes, não o arquivo aberto: num retry o conteúdo precisa ser reenviado inteiro
        data=image_path.read_bytes(),
    )
    return image_urn


def find_images(post_file: Path) -> list[Path]:
    image_dir = post_file.parent / post_file.stem
    if not image_dir.is_dir():
        return []
    images = []
    for ext in ("*.png", "*.jpg", "*.jpeg"):
        images.extend(image_dir.glob(ext))
    return sorted(images)


def publish(token: str, text: str, image_paths: list[Path] | None = None) -> str:
    """Publica o post e devolve o ID (header x-restli-id da resposta)."""
    body = {
        "author": f"urn:li:person:{PERSON_ID}",
        "commentary": text,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }

    if image_paths:
        if len(image_paths) == 1:
            print(f"Enviando imagem: {image_paths[0].name}")
            image_urn = upload_image(token, image_paths[0])
            body["content"] = {"media": {"id": image_urn}}
        else:
            images = []
            for image_path in image_paths:
                print(f"Enviando imagem: {image_path.name}")
                image_urn = upload_image(token, image_path)
                images.append({"id": image_urn, "altText": image_path.stem})
            body["content"] = {"multiImage": {"images": images}}

    # Criar post não é idempotente: se o LinkedIn criou o post e respondeu 5xx (ou a conexão
    # caiu depois do envio), retentar publicaria duas vezes. Por isso aqui só há retry em 429
    # e em falha ao conectar, quando o pedido com certeza não foi processado. Em 5xx a
    # execução para e é preciso conferir no LinkedIn antes de rodar de novo.
    response = request_with_retry(
        "POST",
        f"{API_BASE}/posts",
        "publicação do post",
        retry_server_errors=False,
        headers=api_headers(token),
        json=body,
    )
    # A API devolve o ID do post criado no header x-restli-id (ex.: urn:li:share:123).
    return response.headers.get("x-restli-id", "")


def main():
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    PUBLISHED_DIR.mkdir(parents=True, exist_ok=True)

    posts = sorted(QUEUE_DIR.glob("*.md"))
    if not posts:
        print("Nenhum post na fila.")
        return

    token = load_token()
    posted = 0

    for post_file in posts:
        frontmatter, body = parse_post(post_file)

        if frontmatter is None:
            print(f"Ignorando {post_file.name}: sem frontmatter.")
            continue

        if frontmatter.get("status") == "posted":
            continue

        scheduled_at = frontmatter.get("scheduled_at", "")
        if not is_due(scheduled_at):
            print(f"Agendado para {scheduled_at} — ainda nao e a hora.")
            continue

        image_paths = find_images(post_file)
        suffix = f" + {len(image_paths)} imagem(ns)" if image_paths else ""
        print(f"Postando: {post_file.name}{suffix}")
        publish(token, body, image_paths)

        dest = PUBLISHED_DIR / post_file.name
        shutil.move(str(post_file), str(dest))
        print("Publicado e movido para posting/published/")
        posted += 1

    if posted == 0:
        print("Nenhum post para publicar agora.")


def run() -> int:
    try:
        main()
    except PostError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run())
