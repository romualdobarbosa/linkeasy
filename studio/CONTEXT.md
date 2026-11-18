# Studio

Este é o ambiente de criação de posts para o LinkedIn da pessoa que usa o linkeasy.

## Como funciona

1. A pessoa informa o tema ou prompt do post
2. O redator é acionado para redigir o conteúdo
3. O post é salvo em `for_review/` aguardando aprovação
4. Após aprovação, o post passa pela voz ativa (com a medição descrita abaixo) e segue para `../carousel_studio/` (se carrossel) ou `../infographic/` (se infográfico), depois vai para `../posting/queue/`

## Arquivos e pastas desta pasta

- `redator.md` — instruções e regras para redigir os posts
- `for_review/` — posts redigidos aguardando aprovação
- `for_review/antes/` — cópia do rascunho do redator antes da voz ativa, só para a medição

## Inputs esperados

- Prompt com o tema ou ideia do post
- Dados de `../data/` quando o post envolver experiências, cursos ou projetos

## Output esperado

Um post salvo em `for_review/` com frontmatter `status: for_review`, pronto para revisão.

## Humanizar o texto e medir

Antes de aprovar um post, ele passa pela voz ativa: a skill cujo nome está em `../data/voz/ativa`. Ela reescreve o rascunho na voz da pessoa e chama o `/humanizer` em modo embutido; onde os dois discordarem, vale o perfil de voz. Se `../data/voz/ativa` não existir, rode `/criar-voz` antes ou use `/humanizer` direto. Cada passada é medida:

1. Antes de chamar a voz, copie o rascunho do redator para `for_review/antes/<slug>.md`. Esse é o "antes".
2. Rode a voz ativa no post em `for_review/<slug>.md`. A saída dela é o "depois".
3. Grave a medição no frontmatter do post:

   ```bash
   uv run padroes.py studio/for_review/antes/<slug>.md studio/for_review/<slug>.md --gravar
   ```

   O comando mostra a tabela de padrões antes e depois e grava `padroes_antes` e `padroes_depois` no frontmatter. Os dois campos vão junto com o post para a fila e para `history/`.

A cópia em `for_review/antes/` nunca vai para `posting/queue/`. O agregado dos posts publicados sai com `uv run padroes.py --resumo history`.
