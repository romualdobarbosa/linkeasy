# Posting

Gerencia a fila de publicação dos posts do LinkedIn do Romualdo.

## Fluxo

```
studio/for_review/ → posting/queue/ → post.py → history/
```

1. Post aprovado no studio é movido para `queue/`, com `scheduled_at` preenchido.
2. `uv run post.py` publica os posts cujo `scheduled_at` já passou e move cada um para `../history/` sozinho. Ninguém move post publicado à mão.

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
scheduled_at: 2026-05-15 08:00   # quando publicar, formato AAAA-MM-DD HH:MM
status: queue                    # vira published quando o post.py publica
published_at: 2026-05-15 08:32   # gravado pelo post.py
post_id: urn:li:share:...        # gravado pelo post.py (header x-restli-id da API)
---
```

Na fila eu preencho só `scheduled_at` e `status: queue`. Os campos `status: published`, `published_at` e `post_id` quem grava é o `post.py`, logo depois que a API confirma a publicação. Não edite esses três à mão.

O horário é local de America/Sao_Paulo. Para usar outro fuso, defina `LINKEASY_TZ` no `.env` (por exemplo `LINKEASY_TZ=Europe/Lisbon`).

## O que o post.py faz com cada post

- Sem `scheduled_at` ou com data em outro formato, para com erro dizendo qual arquivo e qual campo.
- Com `scheduled_at` no futuro, deixa na fila.
- Com `post_id` já gravado, não publica de novo. Só completa `status` e `published_at` se faltarem e move para `history/`. Isso cobre o caso de a execução cair entre publicar e mover.
- Se o destino já existir em `history/`, para sem sobrescrever nada.

## Imagens

- Pasta de imagens com o mesmo nome do arquivo sem extensão (ex: `meu-post/`).
- Só entram arquivos png, jpg e jpeg, em ordem de nome. Os outros geram aviso e ficam de fora.
- Uma imagem vai como imagem única. De 2 a 20 vão como multiImage. Mais de 20 dá erro.
- Carrossel em PDF não passa pelo `post.py`. Esse eu publico à mão no LinkedIn.

## Regras

- Nome do arquivo: `slug-do-post.md` (sem data, sem espaços)
- Não editar posts em `history/`, são registro histórico
