# Studio

Este é o ambiente de criação de posts para o LinkedIn do Romualdo.

## Como funciona

1. Romualdo informa o tema ou prompt do post
2. O redator é acionado para redigir o conteúdo
3. O post é salvo em `for_review/` aguardando aprovação
4. Após aprovação, o post passa por `/humanizer` (com a medição descrita abaixo) e segue para `../carousel_studio/` (se carrossel) ou `../infographic/` (se infográfico), depois vai para `../posting/queue/`

## Arquivos e pastas desta pasta

- `redator.md` — instruções e regras para redigir os posts
- `for_review/` — posts redigidos aguardando aprovação
- `for_review/antes/` — cópia do rascunho antes do `/humanizer`, só para a medição

## Inputs esperados

- Prompt com o tema ou ideia do post
- Dados de `../data/` quando o post envolver experiências, cursos ou projetos

## Output esperado

Um post salvo em `for_review/` com frontmatter `status: for_review`, pronto para revisão.

## Humanizar o texto e medir

Antes de aprovar um post, use `/humanizer` para remover padrões típicos de texto gerado por IA. Cada passada é medida:

1. Antes de chamar o `/humanizer`, copie o rascunho para `for_review/antes/<slug>.md`.
2. Rode o `/humanizer` no post em `for_review/<slug>.md`.
3. Grave a medição no frontmatter do post:

   ```bash
   uv run padroes.py studio/for_review/antes/<slug>.md studio/for_review/<slug>.md --gravar
   ```

   O comando mostra a tabela de padrões antes e depois e grava `padroes_antes` e `padroes_depois` no frontmatter. Os dois campos vão junto com o post para a fila e para `history/`.

A cópia em `for_review/antes/` nunca vai para `posting/queue/`. O agregado dos posts publicados sai com `uv run padroes.py --resumo history`.

Para calibrar com a voz do autor, forneça uma amostra junto ao comando:
> `/humanizer` aqui está o post. Amostra da minha voz: [trecho de texto escrito por mim]
