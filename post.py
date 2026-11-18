import json
import os
import re
import shutil
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN_FILE = ".token.json"
QUEUE_DIR = Path("posting/queue")
HISTORY_DIR = Path("history")

API_BASE = "https://api.linkedin.com/rest"
# Versão da API (header LinkedIn-Version, formato AAAAMM). Última verificação: 2026-11-18,
# quando 202606 a 202611 respondiam e 202512 para trás já devolviam 426 NONEXISTENT_VERSION.
# O LinkedIn tira cada versão de suporte em ~1 ano; se aparecer 426, é esta data que sobe.
LINKEDIN_VERSION = "202611"

# Horários do frontmatter são locais deste fuso (sobrescrevível com LINKEASY_TZ).
DEFAULT_TZ = "America/Sao_Paulo"
DATE_FORMAT = "%Y-%m-%d %H:%M"

TOKEN_WARN_DAYS = 7

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
MAX_IMAGES = 20  # multiImage aceita de 2 a 20 imagens

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


def load_token(now: datetime | None = None) -> str:
    """Lê o access_token de TOKEN_FILE e confere a validade se auth.py gravou obtained_at."""
    path = Path(TOKEN_FILE)
    if not path.exists():
        raise PostError(f"{TOKEN_FILE} não encontrado, rode `uv run auth.py`")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        token = data["access_token"]
    except (json.JSONDecodeError, KeyError, TypeError):
        raise PostError(f"{TOKEN_FILE} sem access_token válido, rode `uv run auth.py`") from None

    obtained_at = data.get("obtained_at")
    expires_in = data.get("expires_in")
    if not obtained_at or expires_in is None:
        print(
            f"Aviso: {TOKEN_FILE} sem obtained_at/expires_in, não dá para checar a validade.",
            file=sys.stderr,
        )
        return token
    try:
        obtained = datetime.fromisoformat(obtained_at)
        expires = obtained + timedelta(seconds=int(expires_in))
    except (ValueError, TypeError):
        raise PostError(f"{TOKEN_FILE}: obtained_at/expires_in inválidos") from None
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=get_tz())

    now = now or datetime.now(get_tz())
    if now >= expires:
        raise PostError(f"token expirou em {format_local(expires)}, rode `uv run auth.py`")
    if expires - now < timedelta(days=TOKEN_WARN_DAYS):
        print(
            f"Aviso: o token expira em {format_local(expires)}; renove com `uv run auth.py`.",
            file=sys.stderr,
        )
    return token


# Linha "chave: valor  # comentário opcional" do frontmatter.
_FM_LINE = re.compile(r"^(?P<key>[A-Za-z_][\w-]*)\s*:\s*(?P<value>.*?)(?P<comment>\s+#.*)?$")


def _split_frontmatter(text: str) -> tuple[list[str], int] | None:
    """(linhas com quebra, índice do --- de fechamento), ou None se não houver frontmatter."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].rstrip("\r\n") == "---":
            return lines, i
    return None


def parse_post(file: Path) -> tuple[dict | None, str]:
    text = file.read_text(encoding="utf-8")
    split = _split_frontmatter(text)
    if split is None:
        return None, text.strip()
    lines, end = split
    frontmatter = {}
    for line in lines[1:end]:
        match = _FM_LINE.match(line.rstrip("\r\n"))
        if match:
            frontmatter[match["key"]] = match["value"].strip()
    return frontmatter, "".join(lines[end + 1 :]).strip()


def _write_atomic(file: Path, data: bytes) -> None:
    fd, tmp = tempfile.mkstemp(dir=file.parent, prefix=f".{file.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        shutil.copymode(file, tmp)
        os.replace(tmp, file)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def update_frontmatter(file: Path, updates: dict[str, str]) -> None:
    """Atualiza ou acrescenta chaves no frontmatter, sem mexer no resto do arquivo.

    Linhas existentes (inclusive comentários) ficam na ordem; chave existente troca só o valor
    e mantém o comentário da linha; chave nova entra antes do --- de fechamento. O corpo é
    preservado byte a byte e a escrita é atômica (temporário + os.replace).
    """
    split = _split_frontmatter(file.read_bytes().decode("utf-8"))
    if split is None:
        raise PostError(f"{file.name}: sem frontmatter para atualizar")
    lines, end = split
    newline = "\r\n" if lines[0].endswith("\r\n") else "\n"
    pending = dict(updates)
    for i in range(1, end):
        content = lines[i].rstrip("\r\n")
        match = _FM_LINE.match(content)
        if match and match["key"] in pending:
            value = pending.pop(match["key"])
            eol = lines[i][len(content) :]
            lines[i] = f"{match['key']}: {value}{match['comment'] or ''}{eol}"
    lines[end:end] = [f"{key}: {value}{newline}" for key, value in pending.items()]
    _write_atomic(file, "".join(lines).encode("utf-8"))


def _history_paths(post_file: Path) -> tuple[Path, Path, Path]:
    """(destino do .md, pasta de imagens na fila, destino da pasta de imagens)."""
    return (
        HISTORY_DIR / post_file.name,
        post_file.parent / post_file.stem,
        HISTORY_DIR / post_file.stem,
    )


def check_history_free(post_file: Path) -> None:
    dest, images_src, images_dest = _history_paths(post_file)
    for target in (dest, images_dest if images_src.exists() else None):
        if target is not None and target.exists():
            raise PostError(f"{target} já existe; não vou sobrescrever o histórico, resolva à mão")


def move_to_history(post_file: Path) -> None:
    """Move o .md e a pasta de imagens homônima para HISTORY_DIR, sem sobrescrever nada.

    A pasta vai primeiro: se cair no meio, a próxima execução só precisa mover o .md.
    """
    check_history_free(post_file)
    dest, images_src, images_dest = _history_paths(post_file)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    if images_src.is_dir():
        shutil.move(str(images_src), str(images_dest))
    shutil.move(str(post_file), str(dest))


def get_tz() -> ZoneInfo:
    name = os.getenv("LINKEASY_TZ") or DEFAULT_TZ
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        raise PostError(f"fuso inválido em LINKEASY_TZ: {name!r}") from None


def format_local(moment: datetime) -> str:
    return moment.astimezone(get_tz()).strftime(DATE_FORMAT)


def is_due(frontmatter: dict, now: datetime, source: str) -> bool:
    """True se scheduled_at já passou. `now` precisa ter fuso. Erro se faltar ou for inválido."""
    scheduled_at = frontmatter.get("scheduled_at", "")
    if not scheduled_at:
        raise PostError(f"{source}: frontmatter sem scheduled_at")
    try:
        scheduled = datetime.strptime(scheduled_at, DATE_FORMAT)
    except ValueError:
        raise PostError(
            f"{source}: scheduled_at inválido ({scheduled_at!r}), use o formato AAAA-MM-DD HH:MM"
        ) from None
    return now >= scheduled.replace(tzinfo=get_tz())


def get_person_id() -> str:
    person_id = os.getenv("LINKEDIN_PERSON_ID", "").strip()
    if not person_id:
        raise PostError("LINKEDIN_PERSON_ID não definido; preencha no .env (veja .env.example)")
    return person_id


def upload_image(token: str, image_path: Path) -> str:
    init_response = request_with_retry(
        "POST",
        f"{API_BASE}/images?action=initializeUpload",
        "initializeUpload",
        headers=api_headers(token),
        json={"initializeUploadRequest": {"owner": f"urn:li:person:{get_person_id()}"}},
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
    """Imagens da pasta homônima do post (png/jpg/jpeg), em ordem de nome."""
    image_dir = post_file.parent / post_file.stem
    if not image_dir.is_dir():
        return []
    images, ignored = [], []
    for item in sorted(image_dir.iterdir()):
        if item.name.startswith("."):
            continue
        if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS:
            images.append(item)
        else:
            ignored.append(item.name)
    if ignored:
        print(f"Aviso: ignorando em {image_dir.name}/ (não é png/jpg/jpeg): {', '.join(ignored)}")
    if len(images) > MAX_IMAGES:
        raise PostError(
            f"{image_dir.name}/ tem {len(images)} imagens; o LinkedIn aceita no máximo {MAX_IMAGES}"
        )
    if len(images) > 1:
        names = ", ".join(i.name for i in images)
        print(f"Aviso: {len(images)} imagens, vai como multiImage: {names}")
    return images


def publish(token: str, text: str, image_paths: list[Path] | None = None) -> str:
    """Publica o post e devolve o ID (header x-restli-id da resposta)."""
    body = {
        "author": f"urn:li:person:{get_person_id()}",
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


def finish_handoff(post_file: Path, frontmatter: dict, now: datetime) -> None:
    """Post que já tem post_id: não republica, só completa o estado e move para history/."""
    print(f"{post_file.name}: já publicado ({frontmatter['post_id']}), concluindo o registro.")
    updates = {}
    if frontmatter.get("status") != "published":
        updates["status"] = "published"
    if not frontmatter.get("published_at"):
        updates["published_at"] = format_local(now)
    if updates:
        update_frontmatter(post_file, updates)
    move_to_history(post_file)


def main(now: datetime | None = None) -> None:
    """Publica os posts vencidos da fila. `now` fixo serve para testes.

    Por post: (a) já tem post_id → só termina o registro; (b) senão publica e, logo após o
    2xx, grava status/published_at/post_id no arquivo da fila; (c) move para history/.
    Se a execução cair entre (b) e (c), a próxima cai em (a) e não publica de novo.
    """
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    posts = sorted(QUEUE_DIR.glob("*.md"))
    if not posts:
        print("Nenhum post na fila.")
        return

    tz = get_tz()
    token = None
    done = 0
    for post_file in posts:
        frontmatter, body = parse_post(post_file)
        if frontmatter is None:
            print(f"Ignorando {post_file.name}: sem frontmatter.")
            continue

        if frontmatter.get("post_id"):
            finish_handoff(post_file, frontmatter, now or datetime.now(tz))
            done += 1
            continue

        if not is_due(frontmatter, now or datetime.now(tz), post_file.name):
            when = frontmatter["scheduled_at"]
            print(f"{post_file.name}: agendado para {when}, ainda não é a hora.")
            continue

        check_history_free(post_file)
        image_paths = find_images(post_file)
        if token is None:
            token = load_token(now)
        suffix = f" + {len(image_paths)} imagem(ns)" if image_paths else ""
        print(f"Postando: {post_file.name}{suffix}")
        post_id = publish(token, body, image_paths)
        if not post_id:
            print("Aviso: a API não devolveu x-restli-id; gravando post_id desconhecido.")
            post_id = "desconhecido"
        update_frontmatter(
            post_file,
            {
                "status": "published",
                "published_at": format_local(now or datetime.now(tz)),
                "post_id": post_id,
            },
        )
        move_to_history(post_file)
        print(f"Publicado ({post_id}) e movido para {HISTORY_DIR}/")
        done += 1

    if done == 0:
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
