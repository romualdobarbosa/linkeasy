# History

Registro histórico de todos os posts publicados no LinkedIn do Romualdo.

## Estrutura de pastas

```
history/
  post-titulo.md        ← conteúdo do post publicado
  post-titulo/          ← imagens do post (opcional, mesmo nome sem extensão)
    capa.png
```

## Frontmatter

```yaml
---
scheduled_at: 2026-05-13 08:00   # horário planejado
status: published
published_at: 2026-05-13 08:32   # horário real da publicação
post_id: urn:li:share:...        # ID que a API do LinkedIn devolveu
---
```

`status`, `published_at` e `post_id` são gravados pelo `post.py` antes de mover o arquivo. Os horários são locais de America/Sao_Paulo, ou do fuso em `LINKEASY_TZ` se estiver definido.

## Regras

- Posts chegam aqui pelo `post.py`, que move o `.md` e a pasta de imagens de `../posting/queue/` depois de publicar. Não mova nada para cá à mão.
- O `post.py` nunca sobrescreve um arquivo que já está aqui. Se o nome bater, ele para e avisa.
- Não editar o conteúdo dos posts, são registro fiel do que foi publicado.
- Não remover posts. Mesmo conteúdo ruim serve de referência.
