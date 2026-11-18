"""Testes do padroes.py. Só lê o corpus de examples/humanizer/; o resto acontece em tmp_path."""

import json
from pathlib import Path

import pytest

import padroes

CORPUS = Path(__file__).resolve().parent.parent / "examples" / "humanizer"
PARES = sorted(p.name.removesuffix("-antes.md") for p in CORPUS.glob("*-antes.md"))


@pytest.fixture(autouse=True)
def isolado(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


def n(texto: str, padrao: str) -> int:
    return padroes.contar(texto)[padrao]


# --- um caso positivo e um negativo por padrão ------------------------------------------

POSITIVOS = [
    ("paralelismo_negativo", "Não apenas otimiza a query, mas também reduz o custo."),
    ("paralelismo_negativo", "Não é só sobre código, é sobre pessoas."),
    ("paralelismo_negativo", "Não se trata de SQL.\n\nTrata-se de cultura."),
    ("paralelismo_negativo", "O problema não era a ferramenta, era a pergunta."),
    ("vocabulario_ia", "Esse ponto é crucial."),
    ("vocabulario_ia", "Decidi me aprofundar no tema."),
    ("vocabulario_ia", "Mergulhei nos dados por uma semana."),
    ("vocabulario_ia", "Usamos uma solução robusta."),
    ("vocabulario_ia", "Isso ajuda a alavancar resultados."),
    ("vocabulario_ia", "Uma ferramenta de ponta."),
    ("vocabulario_ia", "Minha jornada em dados."),
    ("vocabulario_ia", "É preciso navegar pela complexidade do projeto."),
    ("vocabulario_ia", "O cenário atual pede cuidado."),
    ("importancia_inflada", "O painel serve como referência."),
    ("importancia_inflada", "Teve um papel fundamental no projeto."),
    ("importancia_inflada", "Foi um ponto de virada."),
    ("gerundio_raso", "Entreguei o relatório, garantindo a qualidade."),
    ("linguagem_promocional", "Um escritório no coração da cidade."),
    ("linguagem_promocional", "Uma vila aninhada entre montanhas."),
    ("atribuicao_vaga", "Especialistas apontam que dados custam caro."),
    ("atribuicao_vaga", "Estudos mostram que isso funciona."),
    ("preenchimento", "Com o objetivo de melhorar a carga."),
    ("preenchimento", "É importante destacar que a base mudou."),
    ("preenchimento", "Vale a pena mencionar o custo."),
    ("preenchimento", "Rodei os testes. Além disso, revisei o código."),
    ("introducao_encenada", "Vamos explorar o tema."),
    ("introducao_encenada", "A verdade é que ninguém leu."),
    ("encerramento_generico", "O futuro é promissor."),
    ("encerramento_generico", "E você, já passou por isso?"),
    ("residuo_chatbot", "Espero que isso ajude."),
    ("residuo_chatbot", "Certamente! O valor é 3."),
    ("residuo_chatbot", "Aqui está um resumo do projeto."),
    ("travessao", "A carga — que era lenta — caiu."),
    ("negrito", "Isso é **importante** aqui."),
    ("negrito", "Isso é __importante__ aqui."),
    ("emoji", "Pronto 🚀"),
    ("hashtag", "Fim do post. #dados"),
    ("dois_pontos_prosa", "O resultado foi claro: caiu 10%."),
    ("dois_pontos_prosa", "**Resultado:** caiu 10%."),
    ("aspas_curvas", "Ele disse “ok”."),
]

NEGATIVOS = [
    ("paralelismo_negativo", "Não é fácil, mas vale o esforço."),
    ("paralelismo_negativo", "A query não é lenta. É preciso só reindexar."),
    ("vocabulario_ia", "Aprofundar o conhecimento em SQL levou tempo."),
    ("vocabulario_ia", "Mergulhar é meu hobby de fim de semana."),
    ("vocabulario_ia", "Testei de ponta a ponta."),
    ("vocabulario_ia", "A jornada de trabalho é de oito horas."),
    ("vocabulario_ia", "Naveguei pelo site da prefeitura."),
    ("vocabulario_ia", "O cenário de teste tinha três casos."),
    ("vocabulario_ia", "O texto sublinhado indica o link."),
    ("importancia_inflada", "O papel do analista mudou."),
    ("gerundio_raso", "Estou garantindo que a carga rode."),
    ("linguagem_promocional", "O JSON tem campos aninhados."),
    ("atribuicao_vaga", "Os especialistas do time revisaram o código."),
    ("preenchimento", "Fiz isso a fim."),
    ("preenchimento", "Vale a pena estudar SQL."),
    ("preenchimento", "Rodei os testes e, além disso, revisei o código."),
    ("introducao_encenada", "Vamos rodar a carga amanhã."),
    ("encerramento_generico", "O futuro da empresa depende disso."),
    ("residuo_chatbot", "Claro que funciona."),
    ("travessao", "Um intervalo de 2020-2024 com hífen."),
    ("negrito", "Multiplique 2 * 3 * 4."),
    ("emoji", "Ação, decisão, ênfase, çã, ü, ñ, © e →."),
    ("hashtag", "# Título\n\nO item #3 da lista."),
    ("dois_pontos_prosa", "A reunião é às 12:30."),
    ("dois_pontos_prosa", "Os passos são:\n\n- abrir: o arquivo\n1. rodar: o script"),
    ("dois_pontos_prosa", "## Passo 1: preparar\n\n| a: b |"),
    ("aspas_curvas", 'Ele disse "ok".'),
]


@pytest.mark.parametrize(("padrao", "texto"), POSITIVOS)
def test_positivo(padrao, texto):
    assert n(texto, padrao) >= 1


@pytest.mark.parametrize(("padrao", "texto"), NEGATIVOS)
def test_negativo(padrao, texto):
    assert n(texto, padrao) == 0


def test_todo_padrao_tem_positivo_e_negativo():
    assert {p for p, _ in POSITIVOS} == set(padroes.IDS)
    assert {p for p, _ in NEGATIVOS} == set(padroes.IDS)


# --- casos específicos --------------------------------------------------------------------


def test_contar_devolve_todos_os_ids_em_ordem():
    c = padroes.contar("")
    assert list(c) == list(padroes.IDS)
    assert set(c.values()) == {0}


def test_padroes_tem_metadados():
    for p in padroes.PADROES:
        assert p.fonte in {"pt.wikipedia", "curadoria"}
        assert p.secao is None or p.secao.startswith("§")
        assert p.regexes


def test_frontmatter_ignorado():
    texto = "---\ntitulo: **crucial** — #tag\n---\nTexto normal."
    assert sum(padroes.contar(texto).values()) == 0


def test_tracos_no_meio_nao_sao_frontmatter():
    assert n("Texto.\n---\nÉ crucial.\n---\n", "vocabulario_ia") == 1


def test_codigo_cercado_ignorado():
    texto = "Texto.\n\n```python\nx = '—' # crucial\n```\n\nFim."
    assert sum(padroes.contar(texto).values()) == 0


def test_codigo_inline_ignorado():
    assert sum(padroes.contar("Rode `crucial — **x**` agora.").values()) == 0


def test_url_ignorada():
    texto = "Veja https://exemplo.invalid/robusto#secao e www.exemplo.invalid/crucial"
    assert sum(padroes.contar(texto).values()) == 0


def test_html_e_imagem_markdown_ignorados():
    texto = (
        '<img src="a.png" alt="Slide 4: a estrutura robusta" width="420">\n\n'
        "![Capa: um cenário de dados](capa.png)"
    )
    assert sum(padroes.contar(texto).values()) == 0


def test_link_markdown_mantem_o_texto():
    assert n("Veja [um sistema robusto](https://exemplo.invalid/x) aqui.", "vocabulario_ia") == 1
    assert n("Requisitos [uv](https://exemplo.invalid/a: b) e Node.", "dois_pontos_prosa") == 0


def test_emoji_com_modificadores_conta_uma_vez():
    assert n("Ok 👍🏽", "emoji") == 1
    assert n("Passo 1️⃣", "emoji") == 1
    assert n("Amo ❤️", "emoji") == 1
    assert n("Família 👨‍👩‍👧", "emoji") == 1


def test_travessao_conta_cada_ocorrencia():
    assert n("a — b – c — d", "travessao") == 3


def test_vocabulario_cede_a_padrao_estrutural():
    c = padroes.contar("Teve um papel crucial. É fundamental ressaltar que mudou.")
    assert c["importancia_inflada"] == 1
    assert c["preenchimento"] == 1
    assert c["vocabulario_ia"] == 0


def test_regex_do_mesmo_padrao_nao_contam_em_dobro():
    assert n("Não é só sobre código, é sobre pessoas.", "paralelismo_negativo") == 1


def test_dois_pontos_cede_a_introducao():
    c = padroes.contar("Spoiler: não era.")
    assert c["introducao_encenada"] == 1
    assert c["dois_pontos_prosa"] == 0


def test_dois_pontos_em_citacao_conta():
    assert n("> Ele disse: vai dar certo.", "dois_pontos_prosa") == 1


def test_comparar():
    comp = padroes.comparar("É crucial — mesmo.", "Importa.")
    assert comp["padroes"]["vocabulario_ia"] == {"antes": 1, "depois": 0, "diferenca": -1}
    assert comp["total"] == {"antes": 2, "depois": 0, "diferenca": -2}
    assert list(comp["padroes"]) == list(padroes.IDS)


def test_deterministico():
    texto = (CORPUS / f"{PARES[0]}-antes.md").read_text(encoding="utf-8")
    assert padroes.contar(texto) == padroes.contar(texto)


# --- CLI ----------------------------------------------------------------------------------


@pytest.fixture
def arquivos(tmp_path):
    antes = tmp_path / "antes.md"
    depois = tmp_path / "depois.md"
    antes.write_text("É crucial — **muito**.", encoding="utf-8")
    depois.write_text("Importa.", encoding="utf-8")
    return antes, depois


def test_cli_um_arquivo(arquivos, capsys):
    assert padroes.main([str(arquivos[0])]) == 0
    out = capsys.readouterr().out
    assert "vocabulario_ia" in out
    assert "hashtag" not in out
    assert out.strip().splitlines()[-1].split() == ["total", "3"]


def test_cli_dois_arquivos(arquivos, capsys):
    assert padroes.main([str(a) for a in arquivos]) == 0
    out = capsys.readouterr().out
    assert "antes" in out and "depois" in out
    assert out.strip().splitlines()[-1].split() == ["total", "3", "0", "-3"]


def test_cli_json_um_arquivo(arquivos, capsys):
    assert padroes.main([str(arquivos[0]), "--json"]) == 0
    dado = json.loads(capsys.readouterr().out)
    assert set(dado) == set(padroes.IDS)
    assert dado["negrito"] == 1


def test_cli_json_dois_arquivos(arquivos, capsys):
    assert padroes.main(["--json", *map(str, arquivos)]) == 0
    dado = json.loads(capsys.readouterr().out)
    assert dado["total"] == {"antes": 3, "depois": 0, "diferenca": -3}


def test_cli_arquivo_inexistente(capsys):
    assert padroes.main(["nao-existe.md"]) == 2
    assert "erro" in capsys.readouterr().err


@pytest.mark.parametrize("argv", [[], ["a.md", "b.md", "c.md"], ["--opcao-que-nao-existe"]])
def test_cli_erro_de_uso(argv, capsys):
    assert padroes.main(argv) == 2
    assert capsys.readouterr().err


def test_cli_help(capsys):
    assert padroes.main(["--help"]) == 0
    assert "--snapshot" in capsys.readouterr().out


def test_cli_snapshot(tmp_path, capsys):
    (tmp_path / "01-x-antes.md").write_text("É crucial.", encoding="utf-8")
    (tmp_path / "01-x-depois.md").write_text("Importa.", encoding="utf-8")
    (tmp_path / "README.md").write_text("É crucial.", encoding="utf-8")
    assert padroes.main(["--snapshot", str(tmp_path)]) == 0
    dado = json.loads(capsys.readouterr().out)
    assert list(dado) == ["01-x-antes.md", "01-x-depois.md"]
    assert dado["01-x-antes.md"]["vocabulario_ia"] == 1


def test_cli_snapshot_pasta_inexistente(capsys):
    assert padroes.main(["--snapshot", "nao-existe"]) == 2
    assert "erro" in capsys.readouterr().err


def test_cli_snapshot_com_arquivo_e_erro(tmp_path, capsys):
    assert padroes.main(["--snapshot", str(tmp_path), "a.md"]) == 2
    assert "erro" in capsys.readouterr().err


# --- regressão com o corpus -------------------------------------------------------------


def test_corpus_tem_quatro_pares():
    assert len(PARES) == 4
    for par in PARES:
        assert (CORPUS / f"{par}-depois.md").is_file()


@pytest.mark.parametrize("par", PARES)
def test_humanizer_reduz_padroes(par):
    antes = (CORPUS / f"{par}-antes.md").read_text(encoding="utf-8")
    depois = (CORPUS / f"{par}-depois.md").read_text(encoding="utf-8")
    total = padroes.comparar(antes, depois)["total"]
    assert total["depois"] < total["antes"]


def test_contagens_batem_com_snapshot():
    """Se mudou de propósito: uv run padroes.py --snapshot examples/humanizer > esperado.json"""
    esperado = json.loads((CORPUS / "esperado.json").read_text(encoding="utf-8"))
    atual = {
        p.name: padroes.contar(p.read_text(encoding="utf-8"))
        for p in sorted([*CORPUS.glob("*-antes.md"), *CORPUS.glob("*-depois.md")])
    }
    assert sorted(atual) == sorted(esperado)
    for nome, contagem in atual.items():
        assert contagem == esperado[nome], f"{nome} mudou"
