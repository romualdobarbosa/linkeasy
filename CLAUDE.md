# Identidade

Você está ajudando a pessoa dona desta instalação do linkeasy a construir uma vitrine profissional no LinkedIn, na área em que ela atua. O objetivo é gerar conteúdo de valor que mostre autoridade e atraia oportunidades.

Quem é a pessoa: a skill de voz ativa, cujo nome está em `data/voz/ativa`, diz o nome dela e como ela escreve. Os dados dela (currículo, certificados, projetos) ficam em `data/`, e a identidade visual (nome, tagline, foto, linha de seguir e paleta usados pelo `/carrossel` e pelo `/infografista`) em `data/identidade.md`. Se `data/voz/ativa` ou `data/identidade.md` não existirem, a instalação ainda não foi configurada: proponha rodar `/criar-voz`.

---

## Fluxo de trabalho

```
input (tema ou contexto)
        ↓
   studio/           ← redator gera o texto do post (formato e tamanho)
        ↓
  voz ativa          ← skill em data/voz/ativa reescreve na voz da pessoa
        ↓              e chama o /humanizer em modo embutido
        ↓              (padroes.py mede rascunho x voz, ver studio/CONTEXT.md)
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
| voz ativa (`voz-<slug>`) | Sempre antes de aprovar um post: reescreve na voz da pessoa e chama o `/humanizer`. Medida pelo `padroes.py` |
| `/criar-voz` | Configurar o linkeasy para uma pessoa: cria a skill de voz dela e grava em `data/voz/ativa` |
| `/humanizer` | Chamado pela voz ativa; direto só quando não há voz ativa |
| `/carrossel` | Gera carrossel PDF de 8 a 12 slides a partir de tema ou post |
| `/infografista` | Gera infográfico PNG a partir de post aprovado |

---

## Mapa de pastas

| Pasta | Propósito | Detalhes |
|---|---|---|
| `data/` | Currículo, certificados e dados da pessoa, as vozes em `data/voz/` e a identidade visual em `data/identidade.md` | `data/CONTEXT.md`, formato em `examples/identidade-exemplo.md` |
| `studio/` | Criação de posts (texto) | `studio/CONTEXT.md` |
| `carousel_studio/` | Criação de carrosséis PDF | `carousel_studio/CONTEXT.md` |
| `infographic/` | Gerador de infográficos PNG | `infographic/render.mjs` |
| `posting/` | Fila de publicação | `posting/CONTEXT.md` |
| `history/` | Registro imutável dos posts publicados | `history/CONTEXT.md` |
| `auth.py` | Etapa de publicação: OAuth 2.0 com o LinkedIn, grava `.token.json` | `README.md` |
| `post.py` | Etapa de publicação: publica a fila vencida e move para `history/` | `posting/CONTEXT.md` |
| `padroes.py` | Mede a voz ativa: conta padrões de IA no rascunho do redator e na saída da voz | `studio/CONTEXT.md` |
| `examples/` | Post, carrossel e infográfico genéricos, usados no smoke test do render | `tests/render-smoke.mjs` |
| `tests/` | Testes do `auth.py` e do `post.py` (API mockada) e smoke test do render | `Makefile` |

---

## Regras

- Linguagem simples e direta
- Sem hashtags, sem emojis, sem travessão (—)
- Escreva na primeira pessoa, na voz da pessoa
- O texto do post passa pela voz ativa: a skill cujo nome está em `data/voz/ativa` (uma linha, ex. `voz-exemplo`). Se o arquivo não existir, rode `/criar-voz` antes ou use `/humanizer` direto
- Pergunte antes de fazer suposições
- Nunca edite posts em `history/`, são registro histórico
- Respeite o fluxo `studio → posting/queue → history` e nunca pule etapas
- Quem move post da fila para `history/` é o `post.py`, não mova à mão
- `status: published`, `published_at` e `post_id` no frontmatter são gravados pelo `post.py`; não preencha nem edite esses campos
- `padroes_antes` e `padroes_depois` são gravados pelo `padroes.py --gravar` no studio; não preencha à mão
- Post com `post_id` não é publicado de novo; se ele travou na fila, rode `uv run post.py` para terminar o registro
