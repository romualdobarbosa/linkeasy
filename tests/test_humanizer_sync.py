"""Testes do humanizer_sync.py. Todo HTTP é mockado com `responses`; nada vai para a rede."""

import json
from pathlib import Path

import pytest
import requests
import responses

import humanizer_sync as hs

LATEST_URL = f"{hs.API_BASE}/releases/latest"
RELEASES_URL = f"{hs.API_BASE}/releases"

UPSTREAM = """---
name: humanizer
description: teste
---

# Humanizer

### 1. Not X but Y

texto

### 2. One-line closers

texto

## Source

Wikipedia.
"""

PTBR = """## Padrões em Português (PT-BR)

### Paralelismo (§1)

### Encerramento (§2)
"""


def raw_url(tag):
    return f"{hs.RAW_BASE}/{tag}/SKILL.md"


@pytest.fixture(autouse=True)
def isolado(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def pasta(tmp_path):
    p = tmp_path / "skill"
    p.mkdir()
    (p / "pt-br.md").write_text(PTBR, encoding="utf-8")
    return p


def grava_versao(pasta, tag):
    dados = {"repositorio": hs.REPOSITORIO, "tag": tag, "sha256_upstream": "x", "baixado_em": "d"}
    (pasta / "VERSAO.json").write_text(json.dumps(dados), encoding="utf-8")


def roda(*args, pasta=None):
    argv = list(args)
    if pasta is not None:
        argv += ["--pasta", str(pasta)]
    return hs.main(argv)


# --- compor e validar ------------------------------------------------------------------


def test_compor_insere_antes_de_source():
    saida = hs.compor(UPSTREAM, PTBR)
    assert saida.index("## Padrões em Português") < saida.index("## Source")
    assert "### Encerramento (§2)\n\n## Source\n" in saida
    assert saida.startswith(UPSTREAM.split("## Source")[0])
    assert saida.endswith("## Source\n\nWikipedia.\n")


def test_compor_sem_source_vai_para_o_fim():
    upstream = UPSTREAM.split("## Source")[0]
    saida = hs.compor(upstream, PTBR + "\n\n")
    assert saida == upstream.rstrip("\n") + "\n\n" + PTBR


def test_compor_ignora_source_que_nao_e_linha_inteira():
    upstream = "---\nname: humanizer\n---\n\ntexto ## Source no meio\n"
    assert hs.compor(upstream, PTBR).endswith("no meio\n\n" + PTBR)


def test_validar_ok():
    assert hs.validar(UPSTREAM, PTBR) == []


def test_validar_paragrafo_inexistente():
    problemas = hs.validar(UPSTREAM, PTBR + "\n### Outro (§12)\n### De novo (§12)\n")
    assert len(problemas) == 1
    assert "§12" in problemas[0]


def test_validar_sem_frontmatter():
    problemas = hs.validar(UPSTREAM.replace("---\n", "", 1), PTBR)
    assert any("frontmatter" in p for p in problemas)


def test_validar_frontmatter_sem_fechamento():
    problemas = hs.validar("---\nname: humanizer\n### 1. a\n### 2. b\n", PTBR)
    assert problemas == ["upstream sem frontmatter (bloco --- no topo)"]


def test_validar_texto_vazio():
    assert "upstream sem frontmatter (bloco --- no topo)" in hs.validar("", "")


def test_validar_nome_errado():
    problemas = hs.validar(UPSTREAM.replace("name: humanizer", "name: outro"), PTBR)
    assert problemas == ["frontmatter do upstream sem `name: humanizer`"]


# --- --status --------------------------------------------------------------------------


@responses.activate(assert_all_requests_are_fired=True)
def test_status_atualizado(pasta, capsys):
    grava_versao(pasta, "v3.1.0")
    responses.add(responses.GET, LATEST_URL, json={"tag_name": "v3.1.0"})
    assert roda("--status", pasta=pasta) == 0
    out = capsys.readouterr().out
    assert "Instalada: v3.1.0" in out
    assert "atualizada" in out
    req = responses.calls[0].request
    assert req.headers["Accept"] == "application/vnd.github+json"
    assert req.headers["User-Agent"] == "linkeasy-humanizer-sync"
    assert "Authorization" not in req.headers


@responses.activate(assert_all_requests_are_fired=True)
def test_status_desatualizado_lista_tags(pasta, capsys):
    grava_versao(pasta, "v3.1.0")
    responses.add(responses.GET, LATEST_URL, json={"tag_name": "v4.0.0"})
    pagina1 = [{"tag_name": f"v1.0.{i}"} for i in range(28)]
    pagina1 += [{"tag_name": "v4.0.0"}, {"tag_name": "v3.2.0"}]
    pagina2 = [
        {"tag_name": "v3.1.0"},
        {"tag_name": "v5.0.0", "draft": True},
        {"tag_name": "nightly"},
    ]
    responses.add(
        responses.GET,
        RELEASES_URL,
        json=pagina1,
        match=[responses.matchers.query_param_matcher({"per_page": "30", "page": "1"})],
    )
    responses.add(
        responses.GET,
        RELEASES_URL,
        json=pagina2,
        match=[responses.matchers.query_param_matcher({"per_page": "30", "page": "2"})],
    )
    assert roda("--status", pasta=pasta) == 0
    out = capsys.readouterr().out
    assert "Última no upstream: v4.0.0" in out
    assert "Tags depois da instalada: v3.2.0, v4.0.0" in out
    assert "--notas" in out


@responses.activate(assert_all_requests_are_fired=True)
def test_status_sem_versao_json(pasta, capsys):
    responses.add(responses.GET, LATEST_URL, json={"tag_name": "v3.1.0"})
    responses.add(responses.GET, RELEASES_URL, json=[])
    assert roda("--status", pasta=pasta) == 0
    out = capsys.readouterr().out
    assert "sem VERSAO.json" in out
    assert "Tags depois da instalada: v3.1.0" in out


def test_status_versao_json_invalido(pasta, capsys):
    (pasta / "VERSAO.json").write_text("{quebrado", encoding="utf-8")
    assert roda("--status", pasta=pasta) == 1
    assert "JSON válido" in capsys.readouterr().err


@responses.activate
@pytest.mark.parametrize(
    ("status", "headers"),
    [(429, {}), (403, {"X-RateLimit-Remaining": "0"})],
)
def test_status_rate_limit(pasta, capsys, status, headers):
    responses.add(responses.GET, LATEST_URL, status=status, headers=headers)
    assert roda("--status", pasta=pasta) == 1
    assert "limite de requisições" in capsys.readouterr().err


@responses.activate
def test_status_403_sem_rate_limit_e_erro_http(pasta, capsys):
    responses.add(responses.GET, LATEST_URL, status=403, body="proibido")
    assert roda("--status", pasta=pasta) == 1
    assert "HTTP 403: proibido" in capsys.readouterr().err


@responses.activate
def test_status_erro_de_rede(pasta, capsys):
    responses.add(responses.GET, LATEST_URL, body=requests.ConnectionError("sem rede"))
    assert roda("--status", pasta=pasta) == 1
    assert "erro de rede" in capsys.readouterr().err


# --- --notas ---------------------------------------------------------------------------


@responses.activate(assert_all_requests_are_fired=True)
def test_notas(capsys):
    responses.add(
        responses.GET, f"{hs.API_BASE}/releases/tags/v4.0.0", json={"body": "Mudou tudo."}
    )
    assert roda("--notas", "v4.0.0") == 0
    assert capsys.readouterr().out.strip() == "Mudou tudo."


@responses.activate
def test_notas_sem_corpo(capsys):
    responses.add(responses.GET, f"{hs.API_BASE}/releases/tags/v4.0.0", json={"body": None})
    assert roda("--notas", "v4.0.0") == 0
    assert "sem notas" in capsys.readouterr().out


@responses.activate
def test_notas_tag_inexistente(capsys):
    responses.add(responses.GET, f"{hs.API_BASE}/releases/tags/v9.9.9", status=404)
    assert roda("--notas", "v9.9.9") == 1
    assert "HTTP 404" in capsys.readouterr().err


# --- --instalar ------------------------------------------------------------------------


@responses.activate(assert_all_requests_are_fired=True)
def test_instalar_grava_skill_e_versao(pasta, capsys):
    responses.add(responses.GET, raw_url("v3.1.0"), body=UPSTREAM)
    assert roda("--instalar", "v3.1.0", pasta=pasta) == 0
    assert (pasta / "SKILL.md").read_text(encoding="utf-8") == hs.compor(UPSTREAM, PTBR)
    texto = (pasta / "VERSAO.json").read_text(encoding="utf-8")
    assert texto.endswith("}\n")
    dados = json.loads(texto)
    assert list(dados) == ["baixado_em", "repositorio", "sha256_upstream", "tag"]
    assert dados["tag"] == "v3.1.0"
    assert dados["repositorio"] == "blader/humanizer"
    assert len(dados["sha256_upstream"]) == 64
    assert "(nenhuma) -> v3.1.0" in capsys.readouterr().out
    assert sorted(p.name for p in pasta.iterdir()) == ["SKILL.md", "VERSAO.json", "pt-br.md"]


@responses.activate
def test_instalar_mostra_versao_anterior_e_e_idempotente(pasta, capsys):
    responses.add(responses.GET, raw_url("v3.1.0"), body=UPSTREAM)
    assert roda("--instalar", "v3.1.0", pasta=pasta) == 0
    primeiro = (pasta / "SKILL.md").read_bytes()
    (pasta / "SKILL.md").chmod(0o640)
    assert roda("--instalar", "v3.1.0", pasta=pasta) == 0
    assert (pasta / "SKILL.md").read_bytes() == primeiro
    assert (pasta / "SKILL.md").stat().st_mode & 0o777 == 0o640
    assert "v3.1.0 -> v3.1.0" in capsys.readouterr().out


@responses.activate
def test_instalar_validacao_falha_nao_grava_nada(pasta, capsys):
    (pasta / "SKILL.md").write_text("antigo", encoding="utf-8")
    responses.add(responses.GET, raw_url("v4.0.0"), body=UPSTREAM.replace("### 2.", "### 9."))
    assert roda("--instalar", "v4.0.0", pasta=pasta) == 1
    err = capsys.readouterr().err
    assert "§2" in err
    assert "nada foi gravado" in err
    assert (pasta / "SKILL.md").read_text(encoding="utf-8") == "antigo"
    assert sorted(p.name for p in pasta.iterdir()) == ["SKILL.md", "pt-br.md"]


@responses.activate
@pytest.mark.parametrize("status", [404, 500, 503])
def test_instalar_erro_http(pasta, capsys, status):
    responses.add(responses.GET, raw_url("v3.1.0"), status=status, body="falhou")
    assert roda("--instalar", "v3.1.0", pasta=pasta) == 1
    assert f"HTTP {status}" in capsys.readouterr().err
    assert [p.name for p in pasta.iterdir()] == ["pt-br.md"]


@responses.activate
def test_instalar_rate_limit(pasta, capsys):
    responses.add(responses.GET, raw_url("v3.1.0"), status=429)
    assert roda("--instalar", "v3.1.0", pasta=pasta) == 1
    assert "limite de requisições" in capsys.readouterr().err


def test_instalar_sem_ptbr(tmp_path, capsys):
    assert roda("--instalar", "v3.1.0", pasta=tmp_path) == 1
    assert "pt-br.md não encontrado" in capsys.readouterr().err


@pytest.mark.parametrize("tag", ["3.1.0", "v3.1", "v3.1.0-rc1", "main", "../v3.1.0"])
def test_tag_invalida(pasta, capsys, tag):
    assert roda("--instalar", tag, pasta=pasta) == 2
    assert "Tag inválida" in capsys.readouterr().err


def test_notas_tag_invalida(capsys):
    assert roda("--notas", "latest") == 2


def test_gravacao_atomica_limpa_tmp_em_erro(tmp_path, monkeypatch):
    def falha(*_):
        raise OSError("disco cheio")

    monkeypatch.setattr(hs.os, "replace", falha)
    with pytest.raises(OSError):
        hs.gravar_atomico(tmp_path / "x.md", "conteudo")
    assert list(tmp_path.iterdir()) == []


# --- uso -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "argv",
    [[], ["--status", "--notas", "v1.0.0"], ["--desconhecido"], ["--instalar"]],
)
def test_uso_errado(argv, capsys):
    assert hs.main(argv) == 2
    assert "usage" in capsys.readouterr().err


def test_help(capsys):
    assert hs.main(["--help"]) == 0
    assert "--instalar" in capsys.readouterr().out


def test_pasta_padrao_relativa_ao_script():
    assert Path(hs.__file__).parent / ".claude/skills/humanizer" == hs.PASTA_PADRAO


# --- isolamento ------------------------------------------------------------------------


@responses.activate
def test_nada_criado_fora_de_tmp_path(tmp_path, pasta):
    repo = Path(hs.__file__).parent
    real = hs.PASTA_PADRAO

    def estado():
        return {p: p.stat().st_mtime_ns for p in [*repo.iterdir(), *real.iterdir()] if p.is_file()}

    antes = estado()
    responses.add(responses.GET, raw_url("v3.1.0"), body=UPSTREAM)
    responses.add(responses.GET, LATEST_URL, json={"tag_name": "v3.1.0"})
    assert roda("--instalar", "v3.1.0", pasta=pasta) == 0
    assert roda("--status", pasta=pasta) == 0
    assert estado() == antes
    criados = {p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*")}
    assert criados == {"skill", "skill/pt-br.md", "skill/SKILL.md", "skill/VERSAO.json"}
