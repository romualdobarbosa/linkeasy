# Identidade

Você está ajudando Romualdo a construir uma vitrine profissional no LinkedIn, focada em dados e tecnologia. O objetivo é gerar conteúdo de valor que mostre autoridade e atraia oportunidades.

---

## Fluxo de trabalho

```
input (tema ou contexto)
        ↓
   studio/           ← redator gera o texto do post
        ↓
  /humanizer         ← remove padrões de IA, ajusta voz
        ↓
     ┌──────────────────────┐
     ↓                      ↓
carousel_studio/      infographic/       ← escolha depende do formato
  /carrossel           /infografista
     ↓                      ↓
     └──────────────────────┘
              ↓
        posting/queue/     ← aguarda publicação (scheduled_at)
              ↓
         uv run post.py    ← publica via API do LinkedIn e grava post_id
              ↓
           history/        ← registro após publicar (o post.py move sozinho)
```

**Quando usar cada formato visual:**
- `/carrossel`: quando o conteúdo tem estrutura de lista, passos ou narrativa com vários pontos (8 a 12 slides, exporta PDF). O `post.py` não publica PDF, então carrossel é publicado à mão no LinkedIn.
- `/infografista`: quando o conteúdo tem um dado central, comparação ou sequência curta (1 imagem PNG, publicada pelo `post.py`)

---

## Skills disponíveis

| Skill | Quando usar |
|---|---|
| `/humanizer` | Sempre antes de aprovar um post, remove padrões de IA |
| `/carrossel` | Gera carrossel PDF de 8 a 12 slides a partir de tema ou post |
| `/infografista` | Gera infográfico PNG a partir de post aprovado |

---

## Mapa de pastas

| Pasta | Propósito | Detalhes |
|---|---|---|
| `data/` | Currículo, certificados e dados do Romualdo | `data/CONTEXT.md` |
| `studio/` | Criação de posts (texto) | `studio/CONTEXT.md` |
| `carousel_studio/` | Criação de carrosséis PDF | `carousel_studio/CONTEXT.md` |
| `infographic/` | Gerador de infográficos PNG | `infographic/render.mjs` |
| `posting/` | Fila de publicação | `posting/CONTEXT.md` |
| `history/` | Registro imutável dos posts publicados | `history/CONTEXT.md` |
| `auth.py` | Etapa de publicação: OAuth 2.0 com o LinkedIn, grava `.token.json` | `README.md` |
| `post.py` | Etapa de publicação: publica a fila vencida e move para `history/` | `posting/CONTEXT.md` |
| `examples/` | Post, carrossel e infográfico genéricos, usados no smoke test do render | `tests/render-smoke.mjs` |
| `tests/` | Testes do `auth.py` e do `post.py` (API mockada) e smoke test do render | `Makefile` |

---

## Regras

- Linguagem simples e direta
- Sem hashtags, sem emojis, sem travessão (—)
- Escreva na primeira pessoa, voz do Romualdo
- Pergunte antes de fazer suposições
- Nunca edite posts em `history/`, são registro histórico
- Respeite o fluxo `studio → posting/queue → history` e nunca pule etapas
- Quem move post da fila para `history/` é o `post.py`, não mova à mão
- `status: published`, `published_at` e `post_id` no frontmatter são gravados pelo `post.py`; não preencha nem edite esses campos
- Post com `post_id` não é publicado de novo; se ele travou na fila, rode `uv run post.py` para terminar o registro
