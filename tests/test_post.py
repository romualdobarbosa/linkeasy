"""Testes do post.py. Toda chamada HTTP é mockada com `responses`; nada vai para a rede."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
import responses

import post

POSTS_URL = f"{post.API_BASE}/posts"
INIT_URL = f"{post.API_BASE}/images?action=initializeUpload"
UPLOAD_URL = "https://upload.exemplo.invalid/img"


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
def token_file(tmp_path, monkeypatch):
    path = tmp_path / ".token.json"
    monkeypatch.setattr(post, "TOKEN_FILE", str(path))
    return path


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
