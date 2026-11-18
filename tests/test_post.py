"""Testes do post.py. Toda chamada HTTP é mockada com `responses`; nada vai para a rede."""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import responses

import post

POSTS_URL = f"{post.API_BASE}/posts"
INIT_URL = f"{post.API_BASE}/images?action=initializeUpload"
UPLOAD_URL = "https://upload.exemplo.invalid/img"


@pytest.fixture(autouse=True)
def isolado(tmp_path, monkeypatch):
    """Nenhum teste toca a fila, o histórico ou o token reais: tudo aponta para tmp_path."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(post, "QUEUE_DIR", tmp_path / "posting" / "queue")
    monkeypatch.setattr(post, "HISTORY_DIR", tmp_path / "history")
    monkeypatch.setattr(post, "TOKEN_FILE", str(tmp_path / ".token.json"))


@pytest.fixture(autouse=True)
def sem_espera(monkeypatch):
    esperas = []
    monkeypatch.setattr(post, "_sleep", esperas.append)
    return esperas


@pytest.fixture(autouse=True)
def pessoa_ficticia(monkeypatch):
    monkeypatch.setenv("LINKEDIN_PERSON_ID", "pessoa-teste")
    monkeypatch.delenv("LINKEASY_TZ", raising=False)


def registra_post_ok(rsps, post_id="urn:li:share:111"):
    rsps.add(responses.POST, POSTS_URL, status=201, headers={"x-restli-id": post_id})


def registra_upload(rsps, n=1):
    for i in range(n):
        rsps.add(
            responses.POST,
            INIT_URL,
            json={"value": {"uploadUrl": f"{UPLOAD_URL}{i}", "image": f"urn:li:image:{i}"}},
        )
        rsps.add(responses.PUT, f"{UPLOAD_URL}{i}", status=201)


# --- requisições, retry e erros ---------------------------------------------------------


@responses.activate
def test_publish_sem_imagem_devolve_post_id_do_header():
    registra_post_ok(responses)
    assert post.publish("tok", "texto") == "urn:li:share:111"
    req = responses.calls[0].request
    assert req.headers["LinkedIn-Version"] == post.LINKEDIN_VERSION
    assert req.headers["Authorization"] == "Bearer tok"


@responses.activate
def test_publish_usa_timeout(monkeypatch):
    capturado = {}
    original = post.requests.request

    def espia(method, url, **kwargs):
        capturado["timeout"] = kwargs.get("timeout")
        return original(method, url, **kwargs)

    monkeypatch.setattr(post.requests, "request", espia)
    registra_post_ok(responses)
    post.publish("tok", "texto")
    assert capturado["timeout"] == post.TIMEOUT


@responses.activate
def test_401_vira_mensagem_de_token():
    responses.add(responses.POST, POSTS_URL, status=401, json={"code": "EXPIRED"})
    with pytest.raises(post.PostError, match="uv run auth.py"):
        post.publish("tok", "texto")


@responses.activate
def test_429_retenta_respeitando_retry_after(sem_espera):
    responses.add(responses.POST, POSTS_URL, status=429, headers={"Retry-After": "7"})
    registra_post_ok(responses)
    assert post.publish("tok", "texto") == "urn:li:share:111"
    assert len(responses.calls) == 2
    assert sem_espera == [7.0]


@responses.activate
def test_429_esgota_tentativas(sem_espera):
    for _ in range(post.MAX_ATTEMPTS):
        responses.add(responses.POST, POSTS_URL, status=429)
    with pytest.raises(post.PostError, match="429"):
        post.publish("tok", "texto")
    assert len(responses.calls) == post.MAX_ATTEMPTS
    assert sem_espera == [2.0, 4.0]  # backoff exponencial sem Retry-After


@responses.activate
def test_5xx_no_create_nao_retenta():
    responses.add(responses.POST, POSTS_URL, status=503, body="indisponivel")
    with pytest.raises(post.PostError, match="Confira no LinkedIn"):
        post.publish("tok", "texto")
    assert len(responses.calls) == 1


@responses.activate
def test_5xx_no_upload_retenta(sem_espera, tmp_path):
    img = tmp_path / "capa.png"
    img.write_bytes(b"png")
    responses.add(responses.POST, INIT_URL, status=500)
    registra_upload(responses)
    assert post.upload_image("tok", img) == "urn:li:image:0"
    assert len(responses.calls) == 3
    assert len(sem_espera) == 1


@responses.activate
def test_4xx_nao_retenta():
    responses.add(responses.POST, POSTS_URL, status=422, body="campo invalido")
    with pytest.raises(post.PostError, match="HTTP 422: campo invalido"):
        post.publish("tok", "texto")
    assert len(responses.calls) == 1


@responses.activate
def test_falha_ao_conectar_retenta_ate_no_create():
    responses.add(responses.POST, POSTS_URL, body=post.requests.ConnectTimeout("sem rede"))
    registra_post_ok(responses)
    assert post.publish("tok", "texto") == "urn:li:share:111"


@responses.activate
def test_falha_ao_conectar_esgota():
    for _ in range(post.MAX_ATTEMPTS):
        responses.add(responses.POST, POSTS_URL, body=post.requests.ConnectTimeout("x"))
    with pytest.raises(post.PostError, match="sem conexão"):
        post.publish("tok", "texto")


@responses.activate
def test_queda_de_leitura_no_create_nao_retenta():
    responses.add(responses.POST, POSTS_URL, body=post.requests.ReadTimeout("lento"))
    with pytest.raises(post.PostError, match="erro de rede"):
        post.publish("tok", "texto")
    assert len(responses.calls) == 1


@responses.activate
def test_queda_de_leitura_no_upload_retenta(tmp_path):
    img = tmp_path / "capa.png"
    img.write_bytes(b"png")
    responses.add(responses.POST, INIT_URL, body=post.requests.ReadTimeout("lento"))
    registra_upload(responses)
    assert post.upload_image("tok", img) == "urn:li:image:0"


# --- agendamento e configuração ----------------------------------------------------------

SP = ZoneInfo("America/Sao_Paulo")


def test_is_due_vencido_e_futuro():
    fm = {"scheduled_at": "2026-05-15 08:00"}
    assert post.is_due(fm, datetime(2026, 5, 15, 8, 0, tzinfo=SP), "a.md")
    assert not post.is_due(fm, datetime(2026, 5, 15, 7, 59, tzinfo=SP), "a.md")


def test_is_due_compara_no_fuso_configurado(monkeypatch):
    fm = {"scheduled_at": "2026-05-15 08:00"}
    # 10:30 UTC = 07:30 em São Paulo (UTC-3): ainda não venceu
    agora = datetime(2026, 5, 15, 10, 30, tzinfo=ZoneInfo("UTC"))
    assert not post.is_due(fm, agora, "a.md")
    monkeypatch.setenv("LINKEASY_TZ", "UTC")
    assert post.is_due(fm, agora, "a.md")


@pytest.mark.parametrize("fm", [{}, {"scheduled_at": ""}, {"scheduled_at": "15/05/2026 08:00"}])
def test_is_due_invalido_ou_ausente_nomeia_arquivo(fm):
    with pytest.raises(post.PostError, match="meu-post.md: .*scheduled_at"):
        post.is_due(fm, datetime.now(SP), "meu-post.md")


def test_fuso_invalido(monkeypatch):
    monkeypatch.setenv("LINKEASY_TZ", "Marte/Olympus")
    with pytest.raises(post.PostError, match="LINKEASY_TZ"):
        post.get_tz()


def test_person_id_ausente(monkeypatch):
    monkeypatch.delenv("LINKEDIN_PERSON_ID")
    with pytest.raises(post.PostError, match="LINKEDIN_PERSON_ID"):
        post.publish("tok", "texto")


# --- token ------------------------------------------------------------------------------


def grava_token(path, **extra):
    path.write_text(post.json.dumps({"access_token": "tok-ficticio", **extra}))


@pytest.fixture
def token_file(tmp_path):
    return tmp_path / ".token.json"


AGORA = datetime(2026, 5, 15, 9, 0, tzinfo=SP)


def test_token_valido_sem_aviso(token_file, capsys):
    grava_token(token_file, obtained_at="2026-05-01T09:00:00-03:00", expires_in=60 * 86400)
    assert post.load_token(AGORA) == "tok-ficticio"
    assert capsys.readouterr().err == ""


def test_token_expirado(token_file):
    grava_token(token_file, obtained_at="2026-03-01T09:00:00-03:00", expires_in=60 * 86400)
    with pytest.raises(post.PostError, match="expirou .*uv run auth.py"):
        post.load_token(AGORA)


def test_token_quase_expirando_avisa(token_file, capsys):
    grava_token(token_file, obtained_at="2026-03-20T09:00:00-03:00", expires_in=60 * 86400)
    assert post.load_token(AGORA) == "tok-ficticio"
    assert "expira em 2026-05-19 09:00" in capsys.readouterr().err


def test_token_sem_obtained_at_avisa(token_file, capsys):
    grava_token(token_file)
    assert post.load_token(AGORA) == "tok-ficticio"
    assert "não dá para checar" in capsys.readouterr().err


def test_token_obtained_at_sem_fuso_usa_fuso_local(token_file):
    grava_token(token_file, obtained_at="2026-03-01T09:00:00", expires_in=60 * 86400)
    with pytest.raises(post.PostError, match="expirou"):
        post.load_token(AGORA)


def test_token_obtained_at_invalido(token_file):
    grava_token(token_file, obtained_at="ontem", expires_in=10)
    with pytest.raises(post.PostError, match="inválidos"):
        post.load_token(AGORA)


def test_token_arquivo_ausente(token_file):
    with pytest.raises(post.PostError, match="não encontrado"):
        post.load_token(AGORA)


def test_token_arquivo_corrompido(token_file):
    token_file.write_text("{nao e json")
    with pytest.raises(post.PostError, match="sem access_token"):
        post.load_token(AGORA)


# --- imagens ------------------------------------------------------------------------------


@responses.activate
def test_upload_de_uma_imagem_usa_media(tmp_path):
    img = tmp_path / "capa.png"
    img.write_bytes(b"conteudo-png")
    registra_upload(responses)
    registra_post_ok(responses)

    post.publish("tok", "texto", [img])

    urls = [c.request.url for c in responses.calls]
    assert urls == [INIT_URL, f"{UPLOAD_URL}0", POSTS_URL]
    init_body = post.json.loads(responses.calls[0].request.body)
    assert init_body["initializeUploadRequest"]["owner"] == "urn:li:person:pessoa-teste"
    assert responses.calls[1].request.body == b"conteudo-png"
    body = post.json.loads(responses.calls[2].request.body)
    assert body["content"] == {"media": {"id": "urn:li:image:0"}}


@responses.activate
def test_upload_de_duas_imagens_usa_multiimage(tmp_path):
    imgs = []
    for nome in ("a.png", "b.jpg"):
        (tmp_path / nome).write_bytes(b"x")
        imgs.append(tmp_path / nome)
    registra_upload(responses, n=2)
    registra_post_ok(responses)

    post.publish("tok", "texto", imgs)

    body = post.json.loads(responses.calls[-1].request.body)
    assert body["content"] == {
        "multiImage": {
            "images": [
                {"id": "urn:li:image:0", "altText": "a"},
                {"id": "urn:li:image:1", "altText": "b"},
            ]
        }
    }


# --- frontmatter --------------------------------------------------------------------------

EXEMPLO = Path(__file__).resolve().parent.parent / "examples" / "post-exemplo.md"


def test_update_frontmatter_preserva_corpo_ordem_e_comentarios(tmp_path):
    corpo = "\nPrimeira linha.\n\n---\nUm separador no corpo e espaço no fim.  \n"
    arquivo = tmp_path / "p.md"
    arquivo.write_bytes(
        (
            "---\n"
            "# comentário solto\n"
            "scheduled_at: 2026-05-15 08:00   # hora planejada\n"
            "status: queue\n"
            "---" + corpo
        ).encode()
    )
    post.update_frontmatter(arquivo, {"status": "published", "post_id": "urn:li:share:9"})
    assert arquivo.read_bytes().decode() == (
        "---\n"
        "# comentário solto\n"
        "scheduled_at: 2026-05-15 08:00   # hora planejada\n"
        "status: published\n"
        "post_id: urn:li:share:9\n"
        "---" + corpo
    )
    fm, _ = post.parse_post(arquivo)
    assert fm["scheduled_at"] == "2026-05-15 08:00"  # comentário inline não entra no valor


def test_update_frontmatter_preserva_crlf(tmp_path):
    arquivo = tmp_path / "p.md"
    arquivo.write_bytes(b"---\r\nstatus: queue\r\n---\r\ncorpo\r\n")
    post.update_frontmatter(arquivo, {"status": "published", "published_at": "x"})
    esperado = b"---\r\nstatus: published\r\npublished_at: x\r\n---\r\ncorpo\r\n"
    assert arquivo.read_bytes() == esperado


def test_update_frontmatter_preserva_exemplo_byte_a_byte(tmp_path):
    arquivo = tmp_path / "p.md"
    original = EXEMPLO.read_bytes()
    arquivo.write_bytes(original)
    post.update_frontmatter(arquivo, {"post_id": "urn:li:share:1"})
    novo = arquivo.read_bytes()
    assert novo.split(b"\n---\n", 1)[1] == original.split(b"\n---\n", 1)[1]
    assert not list(tmp_path.glob(".*.tmp"))


def test_update_frontmatter_sem_frontmatter(tmp_path):
    arquivo = tmp_path / "p.md"
    arquivo.write_text("só corpo")
    with pytest.raises(post.PostError, match="sem frontmatter"):
        post.update_frontmatter(arquivo, {"status": "published"})


def test_escrita_atomica_limpa_temporario_se_falhar(tmp_path, monkeypatch):
    arquivo = tmp_path / "p.md"
    arquivo.write_text("---\nstatus: queue\n---\ncorpo\n")

    def falha(*_):
        raise OSError("disco cheio")

    monkeypatch.setattr(post.os, "replace", falha)
    with pytest.raises(OSError):
        post.update_frontmatter(arquivo, {"status": "published"})
    assert arquivo.read_text() == "---\nstatus: queue\n---\ncorpo\n"
    assert [p.name for p in tmp_path.iterdir()] == ["p.md"]


def test_parse_post_sem_frontmatter_ou_sem_fechamento(tmp_path):
    a = tmp_path / "a.md"
    a.write_text("texto\n")
    assert post.parse_post(a) == (None, "texto")
    b = tmp_path / "b.md"
    b.write_text("---\nstatus: queue\ntexto sem fechar\n")
    assert post.parse_post(b)[0] is None


# --- fluxo completo (main) ----------------------------------------------------------------

VENCIDO = datetime(2026, 1, 15, 9, 30, tzinfo=SP)  # exemplo está agendado para 09:00


@pytest.fixture
def fila(tmp_path):
    fila = tmp_path / "posting" / "queue"
    fila.mkdir(parents=True)
    grava_token(tmp_path / ".token.json")
    return fila


def enfileira(fila, nome="post-exemplo", conteudo=None):
    arquivo = fila / f"{nome}.md"
    arquivo.write_bytes(conteudo.encode() if conteudo else EXEMPLO.read_bytes())
    return arquivo


@responses.activate
def test_main_publica_vencido_grava_estado_e_move(fila, tmp_path):
    enfileira(fila)
    registra_post_ok(responses, "urn:li:share:42")

    post.main(now=VENCIDO)

    assert not (fila / "post-exemplo.md").exists()
    destino = tmp_path / "history" / "post-exemplo.md"
    fm, corpo = post.parse_post(destino)
    assert fm == {
        "scheduled_at": "2026-01-15 09:00",
        "status": "published",
        "published_at": "2026-01-15 09:30",
        "post_id": "urn:li:share:42",
    }
    assert corpo == post.parse_post(EXEMPLO)[1]
    enviado = post.json.loads(responses.calls[0].request.body)
    assert enviado["commentary"] == corpo


@responses.activate
def test_main_futuro_nao_publica(fila, capsys):
    enfileira(fila)
    post.main(now=datetime(2026, 1, 15, 8, 59, tzinfo=SP))
    assert len(responses.calls) == 0
    assert (fila / "post-exemplo.md").read_bytes() == EXEMPLO.read_bytes()
    assert "ainda não é a hora" in capsys.readouterr().out


@responses.activate
def test_main_scheduled_at_invalido_sai_com_erro(fila, monkeypatch, capsys):
    enfileira(fila, "ruim", "---\nscheduled_at: amanhã\n---\ntexto\n")
    monkeypatch.setattr(post, "datetime", _DatetimeFixo)
    assert post.run() == 1
    err = capsys.readouterr().err
    assert "ruim.md" in err and "scheduled_at" in err
    assert len(responses.calls) == 0


class _DatetimeFixo(datetime):
    @classmethod
    def now(cls, tz=None):
        return VENCIDO.astimezone(tz)


@responses.activate
def test_main_falha_na_api_nao_move_nem_grava(fila, tmp_path):
    enfileira(fila)
    responses.add(responses.POST, POSTS_URL, status=422, body="erro")
    with pytest.raises(post.PostError, match="422"):
        post.main(now=VENCIDO)
    assert (fila / "post-exemplo.md").read_bytes() == EXEMPLO.read_bytes()
    assert not (tmp_path / "history").exists()


@responses.activate
def test_main_para_no_primeiro_erro(fila):
    enfileira(fila, "a-primeiro")
    enfileira(fila, "b-segundo")
    responses.add(responses.POST, POSTS_URL, status=400)
    with pytest.raises(post.PostError):
        post.main(now=VENCIDO)
    assert len(responses.calls) == 1
    assert (fila / "b-segundo.md").exists()


@responses.activate
def test_main_post_com_post_id_nao_republica_e_move(fila, tmp_path):
    texto = EXEMPLO.read_text().replace("status: queue\n", "status: queue\npost_id: share:7\n")
    enfileira(fila, conteudo=texto)
    (fila / "post-exemplo").mkdir()
    (fila / "post-exemplo" / "capa.png").write_bytes(b"x")

    post.main(now=datetime(2025, 1, 1, tzinfo=SP))  # mesmo antes do horário: já foi publicado

    assert len(responses.calls) == 0
    fm, _ = post.parse_post(tmp_path / "history" / "post-exemplo.md")
    assert fm["status"] == "published"
    assert fm["published_at"] == "2025-01-01 00:00"
    assert fm["post_id"] == "share:7"
    assert (tmp_path / "history" / "post-exemplo" / "capa.png").exists()
    assert not (fila / "post-exemplo").exists()


@responses.activate
def test_main_post_ja_completo_so_move(fila, tmp_path):
    texto = EXEMPLO.read_text().replace(
        "status: queue\n", "status: published\npublished_at: 2026-01-15 09:01\npost_id: x\n"
    )
    enfileira(fila, conteudo=texto)
    post.main(now=VENCIDO)
    assert (tmp_path / "history" / "post-exemplo.md").read_text() == texto


@responses.activate
def test_queda_entre_gravar_estado_e_mover_nao_republica(fila, tmp_path, monkeypatch):
    enfileira(fila)
    registra_post_ok(responses, "urn:li:share:5")
    original = post.move_to_history

    def cai(_):
        raise KeyboardInterrupt  # simula o processo morrendo antes de mover

    monkeypatch.setattr(post, "move_to_history", cai)
    with pytest.raises(KeyboardInterrupt):
        post.main(now=VENCIDO)
    fm, _ = post.parse_post(fila / "post-exemplo.md")
    assert fm["post_id"] == "urn:li:share:5"

    monkeypatch.setattr(post, "move_to_history", original)
    post.main(now=VENCIDO)
    assert len(responses.calls) == 1  # só a publicação da primeira rodada
    assert (tmp_path / "history" / "post-exemplo.md").exists()


@responses.activate
def test_main_destino_em_history_ja_existe(fila, tmp_path):
    enfileira(fila)
    (tmp_path / "history").mkdir()
    (tmp_path / "history" / "post-exemplo.md").write_text("registro antigo")
    with pytest.raises(post.PostError, match="já existe"):
        post.main(now=VENCIDO)
    assert len(responses.calls) == 0  # checado antes de publicar
    assert (tmp_path / "history" / "post-exemplo.md").read_text() == "registro antigo"


def test_move_to_history_pasta_de_imagens_ja_existe(fila, tmp_path):
    arquivo = enfileira(fila)
    (fila / "post-exemplo").mkdir()
    (tmp_path / "history" / "post-exemplo").mkdir(parents=True)
    with pytest.raises(post.PostError, match="já existe"):
        post.move_to_history(arquivo)
    assert arquivo.exists()


@responses.activate
def test_main_com_imagem_move_pasta_junto(fila, tmp_path):
    enfileira(fila)
    (fila / "post-exemplo").mkdir()
    (fila / "post-exemplo" / "capa.png").write_bytes(b"png")
    registra_upload(responses)
    registra_post_ok(responses)

    post.main(now=VENCIDO)

    assert (tmp_path / "history" / "post-exemplo" / "capa.png").read_bytes() == b"png"
    body = post.json.loads(responses.calls[-1].request.body)
    assert body["content"] == {"media": {"id": "urn:li:image:0"}}


@responses.activate
def test_main_sem_x_restli_id_grava_desconhecido(fila, tmp_path):
    enfileira(fila)
    responses.add(responses.POST, POSTS_URL, status=201)
    post.main(now=VENCIDO)
    fm, _ = post.parse_post(tmp_path / "history" / "post-exemplo.md")
    assert fm["post_id"] == "desconhecido"


@responses.activate
def test_run_401_mensagem_clara_e_saida_1(fila, monkeypatch, capsys):
    enfileira(fila)
    monkeypatch.setattr(post, "datetime", _DatetimeFixo)
    responses.add(responses.POST, POSTS_URL, status=401, json={"code": "EXPIRED_ACCESS_TOKEN"})
    assert post.run() == 1
    err = capsys.readouterr().err
    assert "token expirado ou inválido, rode `uv run auth.py`" in err
    assert "Traceback" not in err
    assert (fila / "post-exemplo.md").exists()


@responses.activate
def test_run_sucesso_devolve_0(fila, monkeypatch):
    enfileira(fila)
    monkeypatch.setattr(post, "datetime", _DatetimeFixo)
    registra_post_ok(responses)
    assert post.run() == 0


def test_main_fila_vazia_e_sem_frontmatter(tmp_path, capsys):
    post.main(now=VENCIDO)
    assert "Nenhum post na fila" in capsys.readouterr().out
    (tmp_path / "posting" / "queue" / "solto.md").write_text("sem frontmatter")
    post.main(now=VENCIDO)
    out = capsys.readouterr().out
    assert "Ignorando solto.md" in out and "Nenhum post para publicar agora" in out


def test_main_sem_token_nao_chama_api(fila, tmp_path):
    enfileira(fila)
    (tmp_path / ".token.json").unlink()
    with pytest.raises(post.PostError, match="não encontrado"):
        post.main(now=VENCIDO)
