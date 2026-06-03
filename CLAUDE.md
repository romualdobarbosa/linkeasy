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
        posting/queue/     ← aguarda publicação
              ↓
           history/        ← registro após publicar
```

**Quando usar cada formato visual:**
- `/carrossel` — quando o conteúdo tem estrutura de lista, passos ou narrativa com vários pontos (8–12 slides, exporta PDF)
- `/infografista` — quando o conteúdo tem um dado central, comparação ou sequência curta (1 imagem PNG)

---

## Skills disponíveis

| Skill | Quando usar |
|---|---|
| `/humanizer` | Sempre antes de aprovar um post — remove padrões de IA |
| `/carrossel` | Gera carrossel PDF de 8–12 slides a partir de tema ou post |
| `/infografista` | Gera infográfico PNG a partir de post aprovado |

---

## Mapa de pastas

| Pasta | Propósito | Detalhes |
|---|---|---|
| `data/` | Currículo, certificados e dados do Romualdo | `data/CONTEXT.md` |
| `studio/` | Criação de posts (texto) | `studio/CONTEXT.md` |
| `carousel_studio/` | Criação de carrosséis PDF | `carousel_studio/CONTEXT.md` |
| `infographic/` | Gerador de infográficos PNG | — |
| `posting/` | Fila de publicação | `posting/CONTEXT.md` |
| `history/` | Registro imutável dos posts publicados | `history/CONTEXT.md` |

---

## Regras

- Linguagem simples e direta
- Sem hashtags, sem emojis, sem travessão (—)
- Escreva na primeira pessoa, voz do Romualdo
- Pergunte antes de fazer suposições
- Nunca edite posts em `history/` — são registro histórico
- Respeite o fluxo: `studio → posting/queue → history`; nunca pule etapas
