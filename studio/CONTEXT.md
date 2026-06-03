# Studio

Este é o ambiente de criação de posts para o LinkedIn do Romualdo.

## Como funciona

1. Romualdo informa o tema ou prompt do post
2. O redator é acionado para redigir o conteúdo
3. O post é salvo em `for_review/` aguardando aprovação
4. Após aprovação, o post passa por `/humanizer` e segue para `../carousel_studio/` (se carrossel) ou `../infographic/` (se infográfico), depois vai para `../posting/queue/`

## Arquivos e pastas desta pasta

- `redator.md` — instruções e regras para redigir os posts
- `for_review/` — posts redigidos aguardando aprovação

## Inputs esperados

- Prompt com o tema ou ideia do post
- Dados de `../data/` quando o post envolver experiências, cursos ou projetos

## Output esperado

Um post salvo em `for_review/` com frontmatter `status: for_review`, pronto para revisão.

## Humanizar o texto (opcional)

Antes de aprovar um post, use `/humanizer` para remover padrões típicos de texto gerado por IA.

Para calibrar com a voz do Romualdo, forneça uma amostra junto ao comando:
> `/humanizer` — aqui está o post. Amostra da minha voz: [trecho de texto escrito por mim]
