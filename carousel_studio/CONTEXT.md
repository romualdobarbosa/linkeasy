# Carousel Studio

Ambiente de criação de carrosséis para o LinkedIn do Romualdo.

## Como funciona

1. Romualdo informa o tema ou prompt do carrossel
2. A skill `/carrossel` é acionada para gerar os slides
3. O carrossel é exportado como PDF e salvo em `carousel_studio/rascunhos/`
4. Após aprovação, o post de texto vai para `../posting/queue/`. O `post.py` não publica PDF, então o carrossel eu publico à mão no LinkedIn

## Estrutura de pastas

```
carousel_studio/
  rascunhos/     ← HTML e PDF de cada carrossel
  data/          ← templates e imagens de referência
```

## Inputs esperados

- Tema ou ideia do carrossel
- Número de slides (opcional, a skill sugere se não informado)
- Dados de `../data/` quando envolver experiências, cursos ou projetos

## Output esperado

Um PDF com os slides do carrossel, salvo em `carousel_studio/rascunhos/`.
