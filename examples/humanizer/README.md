# Corpus do humanizer

Quatro pares de posts fictícios sobre dados e tecnologia, usados para medir o `/humanizer` com o detector `padroes.py`. Cada par tem um `NN-slug-antes.md` e um `NN-slug-depois.md`. Nada aqui é sobre uma pessoa ou empresa real.

## Como foi feito

O "antes" foi escrito por um LLM de propósito, do jeito que ele escreve quando ninguém pede outra coisa, com os vícios de sempre (paralelismo negativo, travessão, negrito, emoji, hashtag, fecho genérico). Os pares variam de propósito, o 03 tem poucos padrões e o 01 e o 04 têm muitos.

O "depois" é a reescrita feita por um agente seguindo o humanizer v3.1.0 (`.claude/skills/humanizer/SKILL.md`) em modo arquivo, sem inventar fato nem número. Hashtags e emojis também saíram, pela regra de voz do repositório.

## Como rodar o detector

Um par em modo comparação:

```bash
uv run padroes.py examples/humanizer/01-qualidade-de-dados-antes.md examples/humanizer/01-qualidade-de-dados-depois.md
```

Com `--json` sai a mesma comparação em JSON.

## Snapshot

O `esperado.json` guarda as contagens atuais de cada arquivo, e o `tests/test_padroes.py` confere duas coisas, que o "depois" tem menos padrões que o "antes" em todo par e que as contagens batem com o snapshot. Se eu mudar uma regex de propósito, regenero o arquivo assim:

```bash
uv run padroes.py --snapshot examples/humanizer > examples/humanizer/esperado.json
```

Os números servem para comparar versões de um mesmo texto, não para dizer se um texto foi escrito por IA. As listas de padrões não foram validadas com corpus em português (o docstring do `padroes.py` explica as fontes).
