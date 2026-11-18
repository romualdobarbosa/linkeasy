"""Detector determinístico de padrões de escrita de IA em português.

Serve para medir o /humanizer de forma reproduzível: conta padrões num texto, antes e
depois da reescrita. Mesma entrada, mesmo número. Não usa modelo nenhum, só regex.

Fontes
------
1. Wikipédia em português, "Sinais de texto gerado por inteligência artificial":
   https://pt.wikipedia.org/wiki/Wikip%C3%A9dia:Sinais_de_texto_gerado_por_intelig%C3%AAncia_artificial
   Seções citadas: 4.1 (importância inflada), 4.3 (gerúndio raso), 4.4 (linguagem
   promocional), 4.6 (atribuição vaga), 4.7 (desafios e perspectivas), 5.1 (vocabulário,
   com as glosas em português), 5.3 (paralelismo negativo) e 7.1 (resíduo de chatbot).
2. Curadoria própria: a seção "Padrões em Português (PT-BR)" do humanizer deste repo
   (.claude/skills/humanizer/SKILL.md) e as regras de voz do CLAUDE.md. O campo `secao`
   de cada padrão aponta para o § do humanizer mais próximo.

Limite
------
A própria página da Wikipédia avisa que traduzir a lista em inglês não valida os sinais em
português. Estas listas também não foram validadas com corpus em português: são
heurísticas para comparar versões de um mesmo texto, não um classificador de "texto de
IA". Na dúvida, as regex preferem deixar de contar a contar errado. Falsos positivos
conhecidos: uso literal de "mergulhar no/na", "robusto" técnico (regressão robusta),
"transformador" elétrico e `__nome__` fora de crase (conta como negrito).

Antes de contar, o texto perde o frontmatter YAML do início, blocos de código cercados,
código inline, tags HTML, imagens em Markdown e URLs (link em Markdown fica com o texto).

Uso:
    uv run padroes.py ARQ                    # tabela com os padrões encontrados
    uv run padroes.py ANTES DEPOIS           # tabela antes/depois/diferença
    uv run padroes.py ... --json             # mesma coisa em JSON
    uv run padroes.py --snapshot DIR         # JSON com as contagens de DIR/*-antes.md e *-depois.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_F = re.IGNORECASE


def _rx(*padroes: str, flags: int = _F) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(p, flags) for p in padroes)


@dataclass(frozen=True)
class Padrao:
    """Um padrão de escrita de IA.

    `cede_a` lista padrões que têm precedência: um trecho deste padrão que se sobrepõe a um
    trecho de algum deles não conta (evita contar "papel crucial" como importância inflada
    e de novo como vocabulário). `so_prosa` aplica as regex só às linhas de prosa (ver
    `_linhas_de_prosa`).
    """

    id: str
    nome: str
    secao: str | None
    fonte: str
    regexes: tuple[re.Pattern[str], ...]
    cede_a: tuple[str, ...] = ()
    so_prosa: bool = False


# Faixas de pictográficos. Não inclui Latin-1 nem letras acentuadas.
_PICTO = (
    "\U0001f000-\U0001faff"  # emoticons, símbolos, transporte, bandeiras, suplementares
    "☀-➿"  # símbolos diversos e dingbats
    "⬀-⯿"  # setas e símbolos (⭐, ⬆)
    "⌚⌛⏩-⏺"  # relógio, ampulheta, botões de mídia
)
_MOD = "︎️\U0001f3fb-\U0001f3ff"  # variation selectors e tons de pele
_EMOJI = (
    rf"[0-9#*]️?⃣"  # keycap: 1️⃣
    rf"|[{_PICTO}][{_MOD}]*(?:‍[{_PICTO}][{_MOD}]*)*"  # sequência com ZWJ conta uma vez
    rf"|[︎️]"  # variation selector solto
)

_GERUNDIOS = (
    "destacando|sublinhando|enfatizando|garantindo|refletindo|simbolizando|contribuindo|"
    "fomentando|cultivando|abrangendo|aprimorando|fortalecendo|possibilitando|consolidando|"
    "impulsionando|promovendo"
)

PADROES: tuple[Padrao, ...] = (
    Padrao(
        "paralelismo_negativo",
        "Paralelismo negativo (não X, mas Y)",
        "§1",
        "pt.wikipedia",
        _rx(
            r"\bnão (?:apenas|só|somente|simplesmente)\b[^.!?\n]{1,80}?\bmas\b",
            r"\bnão (?:é|era|foi) (?:só|apenas|somente|sobre)\b[^!?\n]{1,60}?[,;.]\s*"
            r"(?:é|era|foi|trata-se)\b",
            r"\bnão se trata (?:apenas |só |somente )?de\b[\s\S]{1,150}?\btrata-se\b",
            r"\bnão (?:é|era|foi|são)\b[^.!?\n,;]{1,60}[,;]\s*(?:é|era|foi|são)\b",
        ),
    ),
    Padrao(
        "vocabulario_ia",
        "Vocabulário típico de IA",
        "§12",
        "pt.wikipedia",
        _rx(
            # wiki 5.1 (glosas em português)
            r"\bcruci(?:al|ais)\b",
            r"\b(?:me|se|nos) aprofund\w*|\baprofund\w*-(?:me|se|nos)\b",
            r"\bmergulh\w*\s+(?:em|n[oa]s?|num|numa)\b",
            r"\benfatiz\w*",
            r"\bduradour[oa]s?\b",
            r"\baprimor\w*",
            r"\bfoment\w*",
            r"\bangari\w*",
            r"\bintrincad[oa]s?\b",
            r"\bcenário (?:atual|em evolução|de dados|tecnológico|digital)\b",
            r"\bmeticulos\w*",
            r"\bdecisiv[oa]s?\b",
            r"\brobust\w*",
            r"\btapeçarias?\b",
            r"\btestemunhos? d[eoa]s?\b",
            r"\bsublinh(?:a|am|ar|ando|ou|aram|ei|amos)\b",
            r"\bvibrantes?\b",
            # curadoria PT-BR do humanizer
            r"\bressalt(?:a|am|ar|ando|ou|ei|amos|e)\b",
            r"\balavanc\w*|\balavanqu\w*",
            r"\bagreg\w* valor\b",
            r"\bvislumbr\w*",
            r"\babrangentes?\b",
            r"\bde ponta\b(?! a ponta)",
            r"\binovador(?:a|es|as)?\b",
            r"\btransformador(?:a|es|as)?\b",
            r"\becossistemas?\b",
            r"\bsinergias?\b",
            r"\bjornadas?\b(?! de trabalho)",
            r"\bpotencializ\w*",
            r"\binsights? valios[oa]s?\b",
            r"\bnaveg\w*\s+(?:por|pel[oa]s?)\s+(?:(?:o|a|os|as|esse|essa|este|esta)\s+)?"
            r"(?:complexidades?|desafios?|cenários?|mundo)\b",
            r"\bconstru\w* pontes\b",
        ),
        cede_a=(
            "importancia_inflada",
            "gerundio_raso",
            "preenchimento",
            "introducao_encenada",
        ),
    ),
    Padrao(
        "importancia_inflada",
        "Importância inflada",
        "§13",
        "pt.wikipedia",
        _rx(
            r"\bserv(?:e|em|iu|iram|indo|ir) como\b",
            r"\bé um (?:verdadeiro )?testemunho\b",
            r"\b(?:papel|papéis|momento|momentos) (?:crucial|cruciais|decisivos?|vital|vitais|"
            r"fundamental|fundamentais|significativos?)\b",
            r"\breflete(?:m)? (?:uma )?tendências? mais amplas?\b",
            r"\bprepar\w* o terreno\b",
            r"\bponto de virada\b",
            r"\bcenários? em (?:constante )?evolução\b",
            r"\bmarcas? indeléve(?:l|is)\b",
            r"\bprofundamente enraizad\w*",
            r"\bapesar (?:desses|destes|dos) desafios\b",
            r"\bperspectivas futuras\b",
        ),
    ),
    Padrao(
        "gerundio_raso",
        "Gerúndio raso depois de vírgula",
        "§15",
        "pt.wikipedia",
        _rx(rf",\s*(?:{_GERUNDIOS})\b"),
    ),
    Padrao(
        "linguagem_promocional",
        "Linguagem promocional",
        "§16",
        "pt.wikipedia",
        _rx(
            r"\bostent(?:a|am|ava|ando)\b",
            r"\bno coração d[aoe]s?\b",
            r"\baninhad[oa]s? entre\b",
            r"\bde tirar o fôlego\b",
            r"\bgama diversificada\b",
            r"\brenomad\w*",
            r"\bcompromisso com a excelência\b",
            r"\brumo (?:à|a) excelência\b",
        ),
    ),
    Padrao(
        "atribuicao_vaga",
        "Atribuição vaga de autoridade",
        "§17",
        "pt.wikipedia",
        _rx(
            r"\bespecialistas (?:argumentam|afirmam|apontam|dizem)\b",
            r"\bobservadores (?:citaram|apontam)\b",
            r"\brelatórios do setor\b",
            r"\balguns críticos\b",
            r"\bestudos (?:mostram|apontam|indicam)\b",
        ),
    ),
    Padrao(
        "preenchimento",
        "Frase de preenchimento",
        "§9",
        "curadoria",
        _rx(
            r"\bcom o objetivo de\b",
            r"\btendo em vista\b",
            r"\bno que diz respeito\b",
            r"\bé (?:importante|fundamental|essencial|crucial) (?:destacar|ressaltar|observar|"
            r"lembrar|mencionar|notar) que\b",
            r"\bvale (?:a pena )?(?:destacar|ressaltar|mencionar|lembrar)\b",
            r"\ba fim de\b",
            r"\bdiante disso\b",
            r"\bnesse sentido\b",
            r"(?:^[ \t>*_-]*|(?<=[.!?])\s+)além disso\b",
            flags=_F | re.MULTILINE,
        ),
    ),
    Padrao(
        "introducao_encenada",
        "Introdução encenada",
        "§4",
        "curadoria",
        _rx(
            r"\bvamos explorar\b",
            r"\bvamos mergulhar\b",
            r"\baqui está o que você precisa saber\b",
            r"\bsem mais delongas\b",
            r"\ba verdade é que\b",
            r"\bo ponto é\b",
            r"\bspoiler:",
            r"\be aqui vai o ponto\b",
        ),
    ),
    Padrao(
        "encerramento_generico",
        "Encerramento genérico",
        "§2",
        "curadoria",
        _rx(
            r"\bo futuro é promissor\b",
            r"\btempos empolgantes\b",
            r"\bo céu é o limite\b",
            r"\be você,? (?:o que acha|já)\b",
            r"\bvamos juntos\b",
        ),
    ),
    Padrao(
        "residuo_chatbot",
        "Resíduo de chatbot",
        "§22",
        "pt.wikipedia",
        _rx(
            r"\bespero que (?:isso|isto) (?:ajude|seja útil)\b",
            r"\bcertamente!",
            r"\bclaro!",
            r"\bótima pergunta\b",
            r"\bvocê tem toda (?:a )?razão\b",
            r"\bme avise se\b",
            r"\baqui está (?:o|a|um|uma)\b",
        ),
        cede_a=("introducao_encenada",),
    ),
    Padrao("travessao", "Travessão (— ou –)", "§8", "curadoria", _rx(r"[—–]")),
    Padrao(
        "negrito",
        "Negrito",
        "§19",
        "curadoria",
        _rx(r"\*\*(?=\S)[^\n]+?(?<=\S)\*\*", r"(?<!\w)__(?=\S)[^\n]+?(?<=\S)__(?!\w)"),
    ),
    Padrao("emoji", "Emoji", "§20", "curadoria", _rx(_EMOJI, flags=0)),
    Padrao("hashtag", "Hashtag", None, "curadoria", _rx(r"(?<!\S)#[^\W\d_][\w-]*")),
    Padrao(
        "dois_pontos_prosa",
        "Dois-pontos no meio da prosa",
        None,
        "curadoria",
        _rx(r":[*_]*[ \t]+\S"),
        cede_a=("introducao_encenada",),
        so_prosa=True,
    ),
    Padrao("aspas_curvas", "Aspas curvas", "§21", "curadoria", _rx(r"[“”‘’]", flags=0)),
)

IDS: tuple[str, ...] = tuple(p.id for p in PADROES)

_FRONTMATTER = re.compile(r"\A﻿?---[ \t]*\n.*?\n---[ \t]*(?:\n|\Z)", re.DOTALL)
_CODIGO_CERCADO = re.compile(r"^[ \t]*(`{3,}|~{3,})[^\n]*\n.*?(?:^[ \t]*\1[ \t]*$|\Z)", re.M | re.S)
_CODIGO_INLINE = re.compile(r"`+[^`\n]+?`+")
_URL = re.compile(r"\b(?:https?://|www\.)[^\s<>()\]]+", re.IGNORECASE)
_HTML = re.compile(r"<[^>\n]+>")
_IMAGEM_MD = re.compile(r"!\[[^\]\n]*\]\([^)\n]*\)")
_LINK_MD = re.compile(r"\[([^\]\n]*)\]\([^)\n]*\)")
_ITEM_DE_LISTA = re.compile(r"^(?:[-*+•]|\d+[.)])\s")


def limpar(texto: str) -> str:
    """Tira do texto o que não é prosa.

    Saem frontmatter, código cercado, código inline, tags HTML, imagens em Markdown (com o
    texto alternativo) e URLs. Link em Markdown fica só com o texto do link.
    """
    texto = _FRONTMATTER.sub("", texto)
    texto = _CODIGO_CERCADO.sub("", texto)
    texto = _CODIGO_INLINE.sub(" ", texto)
    texto = _HTML.sub(" ", texto)
    texto = _IMAGEM_MD.sub(" ", texto)
    texto = _LINK_MD.sub(r"\1", texto)
    return _URL.sub(" ", texto)


def _linhas_de_prosa(texto: str) -> str:
    """Só as linhas de prosa, para a contagem de dois-pontos.

    Heurística: descarta linha vazia, cabeçalho (#), item de lista (-, *, +, •, 1. ou 1)),
    linha de tabela (|) e linha que termina em ":" (anuncia uma lista ou citação logo
    abaixo; negrito no fim, como "**Resumo:**", também conta como fim em ":"). O prefixo de
    citação (>) é removido e o resto da linha passa pelas mesmas regras. Horários como
    12:30 não contam porque a regex exige espaço depois dos dois-pontos.
    """
    saida = []
    for linha in texto.split("\n"):
        s = linha.strip().lstrip(">").strip()
        descarta = not s or s.startswith(("#", "|")) or bool(_ITEM_DE_LISTA.match(s))
        if descarta or s.rstrip("*_ ").endswith(":"):
            linha = " " * len(linha)  # mantém os offsets alinhados com o texto original
        saida.append(linha)
    return "\n".join(saida)


def _sobrepoe(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def _trechos(padrao: Padrao, texto: str) -> list[tuple[int, int]]:
    """Trechos do padrão no texto, sem sobreposição entre as regex do mesmo padrão."""
    alvo = _linhas_de_prosa(texto) if padrao.so_prosa else texto
    todos = sorted(m.span() for rx in padrao.regexes for m in rx.finditer(alvo))
    aceitos: list[tuple[int, int]] = []
    for t in todos:
        if not aceitos or not _sobrepoe(aceitos[-1], t):
            aceitos.append(t)
    return aceitos


def contar(texto: str) -> dict[str, int]:
    """Conta cada padrão no texto. Devolve todos os ids, na ordem de PADROES, zeros inclusos."""
    limpo = limpar(texto)
    trechos = {p.id: _trechos(p, limpo) for p in PADROES}
    contagem: dict[str, int] = {}
    for p in PADROES:
        rivais = [t for outro in p.cede_a for t in trechos[outro]]
        contagem[p.id] = sum(1 for t in trechos[p.id] if not any(_sobrepoe(t, r) for r in rivais))
    return contagem


def comparar(antes: str, depois: str) -> dict[str, Any]:
    """Contagem por padrão e totais de dois textos: {"padroes": {...}, "total": {...}}."""
    a, d = contar(antes), contar(depois)
    por_padrao = {i: {"antes": a[i], "depois": d[i], "diferenca": d[i] - a[i]} for i in IDS}
    ta, td = sum(a.values()), sum(d.values())
    return {"padroes": por_padrao, "total": {"antes": ta, "depois": td, "diferenca": td - ta}}


def snapshot(arquivos: dict[str, str]) -> dict[str, dict[str, int]]:
    """Contagens de vários textos, indexadas pelo nome."""
    return {nome: contar(texto) for nome, texto in sorted(arquivos.items())}


def tabela(contagem: dict[str, int]) -> str:
    linhas = [f"{'padrão':<24}{'n':>5}"]
    linhas += [f"{i:<24}{n:>5}" for i, n in contagem.items() if n]
    linhas.append(f"{'total':<24}{sum(contagem.values()):>5}")
    return "\n".join(linhas)


def tabela_comparacao(comp: dict[str, Any]) -> str:
    linhas = [f"{'padrão':<24}{'antes':>7}{'depois':>8}{'dif':>6}"]
    for i, c in comp["padroes"].items():
        if c["antes"] or c["depois"]:
            linhas.append(f"{i:<24}{c['antes']:>7}{c['depois']:>8}{c['diferenca']:>+6}")
    t = comp["total"]
    linhas.append(f"{'total':<24}{t['antes']:>7}{t['depois']:>8}{t['diferenca']:>+6}")
    return "\n".join(linhas)


def _json(dado: object) -> str:
    return json.dumps(dado, sort_keys=True, ensure_ascii=False, indent=2)


def _ler(caminho: str) -> str:
    return Path(caminho).read_text(encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="padroes.py", description="Conta padrões de escrita de IA em português."
    )
    parser.add_argument("arquivos", nargs="*", metavar="ARQ", help="um arquivo, ou ANTES DEPOIS")
    parser.add_argument("--json", action="store_true", help="imprime JSON em vez de tabela")
    parser.add_argument(
        "--snapshot",
        metavar="DIR",
        help="imprime em JSON as contagens de DIR/*-antes.md e DIR/*-depois.md",
    )
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code or 0)

    if args.snapshot is not None:
        if args.arquivos:
            print("erro: --snapshot não aceita arquivos avulsos", file=sys.stderr)
            return 2
        pasta = Path(args.snapshot)
        if not pasta.is_dir():
            print(f"erro: pasta não encontrada: {pasta}", file=sys.stderr)
            return 2
        nomes = sorted([*pasta.glob("*-antes.md"), *pasta.glob("*-depois.md")])
        print(_json(snapshot({p.name: p.read_text(encoding="utf-8") for p in nomes})))
        return 0

    if len(args.arquivos) not in (1, 2):
        print("erro: passe um arquivo, ou dois (ANTES DEPOIS)", file=sys.stderr)
        return 2
    try:
        textos = [_ler(a) for a in args.arquivos]
    except (OSError, UnicodeDecodeError) as e:
        print(f"erro: não consegui ler o arquivo: {e}", file=sys.stderr)
        return 2

    if len(textos) == 1:
        c = contar(textos[0])
        print(_json(c) if args.json else tabela(c))
    else:
        comp = comparar(*textos)
        print(_json(comp) if args.json else tabela_comparacao(comp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
