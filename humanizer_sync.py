"""Sincroniza a skill humanizer com o upstream blader/humanizer, numa versão fixa.

O SKILL.md da skill é composto: SKILL.md do upstream na tag escolhida + a seção PT-BR
(pt-br.md, fonte da verdade) inserida antes de "## Source". A versão só muda com
`--instalar TAG`, depois de ler as notas da release com `--notas TAG`.

    uv run humanizer_sync.py --status
    uv run humanizer_sync.py --notas v3.1.0
    uv run humanizer_sync.py --instalar v3.1.0
"""

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import date
from pathlib import Path

import requests

REPOSITORIO = "blader/humanizer"
API_BASE = f"https://api.github.com/repos/{REPOSITORIO}"
RAW_BASE = f"https://raw.githubusercontent.com/{REPOSITORIO}"
PASTA_PADRAO = Path(__file__).parent / ".claude" / "skills" / "humanizer"

SKILL_FILE = "SKILL.md"
PTBR_FILE = "pt-br.md"
VERSAO_FILE = "VERSAO.json"

TIMEOUT = (10, 30)  # (conexão, leitura) em segundos
HEADERS = {"Accept": "application/vnd.github+json", "User-Agent": "linkeasy-humanizer-sync"}
TAG_RE = re.compile(r"^v\d+\.\d+\.\d+$")
SECAO_SOURCE = "## Source"


class SyncError(Exception):
    """Erro esperado: vira mensagem curta no terminal e exit 1."""


# --- funções puras ---------------------------------------------------------------------


def compor(upstream: str, ptbr: str) -> str:
    """Insere a seção PT-BR antes da linha "## Source" do upstream (ou no fim, se não houver)."""
    secao = ptbr.strip("\n") + "\n"
    linhas = upstream.splitlines(keepends=True)
    for i, linha in enumerate(linhas):
        if linha.rstrip("\r\n") == SECAO_SOURCE:
            return "".join(linhas[:i]) + secao + "\n" + "".join(linhas[i:])
    return upstream.rstrip("\n") + "\n\n" + secao


def _frontmatter(texto: str) -> str | None:
    linhas = texto.splitlines()
    if not linhas or linhas[0].strip() != "---":
        return None
    for i, linha in enumerate(linhas[1:], start=1):
        if linha.strip() == "---":
            return "\n".join(linhas[1:i])
    return None


def validar(upstream: str, ptbr: str) -> list[str]:
    """Lista os problemas que impedem compor; vazia quando está tudo certo."""
    problemas = []
    frontmatter = _frontmatter(upstream)
    if frontmatter is None:
        problemas.append("upstream sem frontmatter (bloco --- no topo)")
    elif not re.search(r"^name:\s*humanizer\s*$", frontmatter, re.MULTILINE):
        problemas.append("frontmatter do upstream sem `name: humanizer`")

    existentes = set(re.findall(r"^### (\d+)\.", upstream, re.MULTILINE))
    citados = sorted(set(re.findall(r"§(\d+)", ptbr)), key=int)
    for n in citados:
        if n not in existentes:
            problemas.append(
                f"{PTBR_FILE} cita §{n}, mas o upstream não tem o cabeçalho '### {n}.'"
            )
    return problemas


def _versao_tupla(tag: str) -> tuple[int, ...]:
    return tuple(int(p) for p in tag.lstrip("v").split("."))


# --- rede ------------------------------------------------------------------------------


def _get(url: str, what: str, **kwargs) -> requests.Response:
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT, **kwargs)
    except requests.RequestException as exc:
        raise SyncError(f"{what} falhou: erro de rede ({exc})") from None
    status = response.status_code
    if status == 429 or (status == 403 and response.headers.get("X-RateLimit-Remaining") == "0"):
        raise SyncError(
            f"{what} falhou: limite de requisições do GitHub atingido (HTTP {status}). "
            "Espere uns minutos e tente de novo."
        )
    if status == 404:
        raise SyncError(f"{what} falhou: não encontrado (HTTP 404) em {url}")
    if not response.ok:
        raise SyncError(f"{what} falhou: HTTP {status}: {response.text[:300]}")
    return response


def ultima_release() -> str:
    return _get(f"{API_BASE}/releases/latest", "consulta da última release").json()["tag_name"]


def listar_tags() -> list[str]:
    tags: list[str] = []
    pagina = 1
    while True:
        params = {"per_page": 30, "page": pagina}
        dados = _get(f"{API_BASE}/releases", "listagem das releases", params=params).json()
        tags += [r["tag_name"] for r in dados if not r.get("draft")]
        if len(dados) < 30:
            return tags
        pagina += 1


def notas(tag: str) -> str:
    dados = _get(f"{API_BASE}/releases/tags/{tag}", f"consulta da release {tag}").json()
    return dados.get("body") or "(release sem notas)"


def baixar_skill(tag: str) -> str:
    response = _get(f"{RAW_BASE}/{tag}/{SKILL_FILE}", f"download do {SKILL_FILE} da {tag}")
    response.encoding = "utf-8"
    return response.text


# --- arquivos --------------------------------------------------------------------------


def ler_versao(pasta: Path) -> dict | None:
    path = pasta / VERSAO_FILE
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise SyncError(f"{path} não é um JSON válido") from None


def gravar_atomico(path: Path, conteudo: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(conteudo)
        # mkstemp cria com 0600; mantém o modo do arquivo antigo ou usa o padrão do umask.
        if path.exists():
            modo = path.stat().st_mode & 0o777
        else:
            umask = os.umask(0)
            os.umask(umask)
            modo = 0o666 & ~umask
        os.chmod(tmp, modo)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


# --- comandos --------------------------------------------------------------------------


def cmd_status(pasta: Path) -> None:
    versao = ler_versao(pasta)
    instalada = versao["tag"] if versao else None
    print(f"Instalada: {instalada or f'(sem {VERSAO_FILE})'}")
    ultima = ultima_release()
    print(f"Última no upstream: {ultima}")
    if instalada and _versao_tupla(ultima) <= _versao_tupla(instalada):
        print("Está atualizada.")
        return
    base = _versao_tupla(instalada) if instalada else (-1,)
    novas = sorted(
        (t for t in listar_tags() if TAG_RE.match(t) and _versao_tupla(t) > base),
        key=_versao_tupla,
    )
    print("Há versão nova. Tags depois da instalada: " + ", ".join(novas or [ultima]))
    print(
        "Leia as notas antes de instalar (`--notas TAG`): uma versão nova pode mudar regras "
        "da skill. Só instale com aval explícito."
    )


def cmd_notas(tag: str) -> None:
    print(notas(tag))


def cmd_instalar(tag: str, pasta: Path) -> None:
    ptbr_path = pasta / PTBR_FILE
    if not ptbr_path.exists():
        raise SyncError(f"{ptbr_path} não encontrado")
    ptbr = ptbr_path.read_text(encoding="utf-8")
    upstream = baixar_skill(tag)

    problemas = validar(upstream, ptbr)
    if problemas:
        lista = "\n".join(f"  - {p}" for p in problemas)
        raise SyncError(
            f"{tag} não passou na validação, nada foi gravado:\n{lista}\n"
            f"Revise o mapeamento de § em {ptbr_path}."
        )

    anterior = ler_versao(pasta)
    versao = {
        "repositorio": REPOSITORIO,
        "tag": tag,
        "sha256_upstream": hashlib.sha256(upstream.encode("utf-8")).hexdigest(),
        "baixado_em": date.today().isoformat(),
    }
    gravar_atomico(pasta / SKILL_FILE, compor(upstream, ptbr))
    gravar_atomico(pasta / VERSAO_FILE, json.dumps(versao, sort_keys=True, indent=2) + "\n")

    de = anterior["tag"] if anterior else "(nenhuma)"
    print(f"humanizer: {de} -> {tag}. {SKILL_FILE} e {VERSAO_FILE} gravados em {pasta}.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="humanizer_sync.py", description="Sincroniza a skill humanizer com o upstream."
    )
    acao = parser.add_mutually_exclusive_group(required=True)
    acao.add_argument("--status", action="store_true", help="versão instalada x última release")
    acao.add_argument("--notas", metavar="TAG", help="mostra as notas da release TAG")
    acao.add_argument("--instalar", metavar="TAG", help="baixa a TAG e recompõe o SKILL.md")
    parser.add_argument("--pasta", type=Path, default=PASTA_PADRAO, help="pasta da skill")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)

    tag = args.notas or args.instalar
    if tag is not None and not TAG_RE.match(tag):
        print(f"Tag inválida: {tag!r} (formato esperado: v1.2.3)", file=sys.stderr)
        return 2

    try:
        if args.status:
            cmd_status(args.pasta)
        elif args.notas:
            cmd_notas(args.notas)
        else:
            cmd_instalar(args.instalar, args.pasta)
    except SyncError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
