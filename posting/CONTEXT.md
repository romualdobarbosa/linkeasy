# Posting

Gerencia a fila de publicação dos posts do LinkedIn do Romualdo.

## Fluxo

```
studio/for_review/ → posting/queue/ → history/
```

1. Post aprovado no studio é movido para `queue/`
2. Post publicado no LinkedIn é movido para `../history/`

## Estrutura de pastas

```
posting/
  queue/              ← posts prontos para publicar
    post-titulo.md
    post-titulo/      ← imagens do post (opcional, mesmo nome sem extensão)
      capa.png

history/              ← registro histórico de todos os posts publicados
  post-titulo.md
  post-titulo/        ← imagens do post
    capa.png
```

## Frontmatter dos posts

```yaml
---
scheduled_at: 2026-05-15 08:00   # data e hora planejada para publicar
status: queue | published
published_at: 2026-05-15 08:32   # preenchido após publicar
---
```

## Regras

- Nome do arquivo: `slug-do-post.md` (sem data, sem espaços)
- Pasta de imagens: mesmo nome do arquivo sem extensão (ex: `meu-post/`)
- Ao publicar: atualizar `status` para `published`, preencher `published_at`, e mover para `../history/`
- Não editar posts em `history/` — são registro histórico
