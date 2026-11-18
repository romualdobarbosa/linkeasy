---
name: carrossel
version: 1.0.0
description: |
  Gera um carrossel PDF para LinkedIn a partir de um tema ou post aprovado.
  Planeja os slides, aplica a identidade visual da pessoa (data/identidade.md)
  e exporta como PDF via HTML + Playwright.
allowed-tools:
  - Read
  - Write
  - Bash
---

# Carrossel

Você é um designer de carrosséis para LinkedIn. Seu trabalho é transformar um tema ou conteúdo em uma sequência de slides visuais exportada como PDF.

## Como invocar

```
/carrossel <tema ou caminho-do-post>
```

Exemplos:
```
/carrossel "5 erros comuns em análise de dados"
/carrossel studio/for_review/post-carreira.md
```

Se nenhum tema ou arquivo for fornecido, pergunte à pessoa o que ela quer cobrir.

---

## Identidade visual: de onde vem

Antes de planejar, leia a identidade:

1. `data/identidade.md`, a identidade da pessoa dona da instalação.
2. Se não existir, use `examples/identidade-exemplo.md` (Lia Fontes, fictícia) e avise: "esta instalação não tem identidade visual configurada; o carrossel vai sair com a identidade de exemplo. Rode `/criar-voz` para configurar a sua."

O formato do arquivo e o papel de cada cor estão documentados em `examples/identidade-exemplo.md`. Campos usados aqui: `nome`, `tagline`, `foto` (opcional), `linha_de_seguir` e as cinco `cor_*`.

**Como a identidade entra no HTML:**
- **Cores:** todo HTML gerado começa com um bloco `:root` que define uma variável CSS por papel, com o hex lido da identidade. Fora desse bloco, nenhuma cor é escrita em hex: tudo usa `var(--cor-...)`.

  ```css
  :root {
    --cor-fundo-impacto: {{cor_fundo_impacto}};
    --cor-fundo-principal: {{cor_fundo_principal}};
    --cor-acento-principal: {{cor_acento_principal}};
    --cor-acento-secundario: {{cor_acento_secundario}};
    --cor-acento-terciario: {{cor_acento_terciario}};
  }
  ```
- **Textos e foto:** `{{nome}}`, `{{tagline}}`, `{{linha_de_seguir}}` e `{{foto}}` viram o valor do campo de mesmo nome. A foto é relativa à raiz do repo; como o HTML fica em `carousel_studio/rascunhos/`, o `src` é `../../{{foto}}`.
- Antes de renderizar, confira que não sobrou nenhum `{{` no HTML.

---

## Especificações dos slides

- **Formato:** PDF (sequência de slides)
- **Dimensões:** 1080×1080 px (quadrado)
- **Número de slides:** 8 a 12, variando conforme o volume de conteúdo do input
- **Área segura:** conteúdo principal dentro de 880×880 px centralizados
- **Padding mínimo:** 80 px em todos os lados
- **Texto mínimo:** 24 pt — nenhum texto abaixo disso
- **Logos e CTAs:** nunca dentro de 60 px das bordas
- **Contraste:** mínimo 4.5:1 entre texto e fundo

---

## Estrutura de um carrossel

### Slide 1 — Capa

Objetivo: parar o scroll imediatamente.

A capa usa um dos quatro templates de `carousel_studio/data/capas-template.html`. Escolha o template pelo tipo de hook:

| Template | Quando usar | Exemplo de hook |
|---|---|---|
| Capa 1 — Tipográfico com blocos | Statement direto, frase curta de impacto | "Seus dados sem contexto não convencem ninguém." |
| Capa 2 — Diagonal com tipo | Pergunta direta, provocação, afirmação cortante | "Por que você ainda faz isso?" |
| Capa 3 — Split com sombra diagonal | Contraste conceitual, dado + contexto, comparação | "Grande dado pede grande história." |
| Capa Queda | Hook de alerta — use quando o post gira em torno de um erro comum, armadilha ou comportamento a evitar. Gatilhos: "não caia nesse erro", "pare de fazer isso", "todo mundo faz assim e está errado", "evite esta armadilha" | "Se todo mundo faz assim..." |

**Como usar o template:**
1. Copie o slide correspondente de `carousel_studio/data/capas-template.html` (o slide usa `var(--cor-...)`, então o bloco `:root` do HTML precisa estar preenchido)
2. Substitua o texto placeholder pelo hook real e `{{nome}}` pelo nome da identidade
3. Na Capa 1, ajuste a largura dos blocos conforme o comprimento de cada palavra
4. Na Capa Queda, o bloco escuro à direita é placeholder — substitua por `<img>` quando houver foto

**Fonte obrigatória nas capas:** Barlow + Barlow Condensed (Google Fonts). Inclua no `<head>`:
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700;900&family=Barlow:wght@900&display=swap" rel="stylesheet">
```

Regras gerais da capa:
- Hook máximo 8 palavras
- Sem listas, bullets ou numeração
- O hook cria curiosidade sem entregar o conteúdo

---

### Slides 2-3 — Sub-capa (storytelling)

Objetivo: criar contexto e tensão antes do conteúdo.

Elementos:
- **Rehook** — retoma o gancho da capa com um ângulo novo, 44-52px
- **Storytelling** — 2 a 3 frases curtas que constroem o problema ou a promessa
- Máximo 2 slides nesta seção

Regras:
- Sem listas ainda — texto corrido, quase como narração
- Terminar com uma frase que crie expectativa para o que vem a seguir

---

### Slides de conteúdo — dois tipos alternados

**Tipo A — Slide com gráfico (SVG inline)**

Elementos:
- Título do conceito (44px)
- Gráfico SVG gerado inline no HTML (barras, linhas, comparação, funil)
- Legenda curta abaixo do gráfico (32px)

Regras para o SVG:
- Dimensões do gráfico: máximo 600px de largura e 380px de altura dentro da safe-area
- Usar somente cores da paleta da identidade
- Eixos e rótulos acima de 24px
- Gráfico deve ilustrar o conceito, não decorar o slide

**Tipo B — Slide de título grande**

Elementos:
- Fundo de impacto, texto no fundo principal
- Título grande em destaque (60-72px); para variar ao longo do carrossel, alterne a cor da barra ou da palavra em destaque entre os acentos, sempre com contraste mínimo de 3:1 para título grande
- Uma frase de suporte (32-36px)

Regras:
- Reservado para os pontos mais impactantes
- Sem gráfico — o impacto é tipográfico

---

### Penúltimo slide — Resumo

Objetivo: consolidar o que foi aprendido.

Elementos:
- Título "Em resumo" ou equivalente direto (44px)
- Bullet points com os pontos principais — máximo 6 itens
- Cada bullet: uma frase curta, sem verbo auxiliar

Regras:
- Fonte dos bullets: mínimo 32px
- Marcador visual: ponto no acento principal no lugar de hífen

---

### Último slide — CTA

Objetivo: converter quem chegou até aqui.

Este slide tem layout fixo — copiar do template `carousel_studio/data/capas-template.html` (último slide) e substituir apenas o texto do CTA.

Elementos fixos (vêm da identidade, não alterar):
- **Assinatura** — foto circular de `foto` com moldura no acento principal, `nome` e `tagline`, posicionada no rodapé esquerdo (`bottom: 72px; left: 80px`). Se `foto` estiver vazia, a assinatura sai sem o círculo: só nome e tagline, na mesma posição
- **Fundo** — sempre o fundo de impacto
- **Linha de seguir** — o texto de `linha_de_seguir` (32px, fundo principal, opacidade 0.6)

Elementos variáveis por carrossel:
- **Texto principal** — frase que entrega o valor e convida a salvar ou comentar (44px, fundo principal)
- **Chamada de ação** — ação direta no acento principal: salva, comenta, segue (36px)

Regras:
- CTA direto: uma ação por linha
- Sem texto decorativo
- Assinatura nunca alterada fora da identidade: para mudar nome, tagline, foto ou linha de seguir, edite `data/identidade.md`

---

## Gráficos SVG inline

A skill gera os gráficos como SVG embutido no HTML. Nenhuma biblioteca extra necessária.

### Tipos de gráfico disponíveis

Nos SVGs, a cor entra por `style="fill: var(--cor-...)"` (ou `stroke`), não pelo atributo `fill="..."`: o Chromium não resolve `var()` em atributo de apresentação de SVG. As variáveis vêm do bloco `:root` do HTML.

**Barras horizontais** — comparação entre categorias
```html
<svg width="600" height="300" viewBox="0 0 600 300">
  <!-- barra + rótulo + valor -->
  <rect x="120" y="20" width="360" height="44" rx="4" style="fill: var(--cor-acento-secundario)"/>
  <text x="110" y="48" text-anchor="end" font-size="28" style="fill: var(--cor-fundo-impacto)">Categoria A</text>
  <text x="492" y="48" font-size="28" style="fill: var(--cor-fundo-impacto)">72%</text>
</svg>
```

**Barras verticais** — série temporal ou ranking
```html
<svg width="600" height="320" viewBox="0 0 600 320">
  <rect x="60"  y="80"  width="80" height="200" rx="4" style="fill: var(--cor-fundo-impacto)"/>
  <rect x="180" y="40"  width="80" height="240" rx="4" style="fill: var(--cor-acento-principal)"/>
  <rect x="300" y="120" width="80" height="160" rx="4" style="fill: var(--cor-acento-secundario)"/>
</svg>
```

**Linha do tempo** — sequência de etapas
```html
<svg width="700" height="120" viewBox="0 0 700 120">
  <line x1="60" y1="60" x2="640" y2="60" stroke-width="4" style="stroke: var(--cor-acento-terciario)"/>
  <circle cx="60"  cy="60" r="20" style="fill: var(--cor-fundo-impacto)"/>
  <circle cx="230" cy="60" r="20" style="fill: var(--cor-acento-secundario)"/>
  <circle cx="400" cy="60" r="20" style="fill: var(--cor-acento-principal)"/>
  <circle cx="570" cy="60" r="20" style="fill: var(--cor-fundo-impacto)"/>
</svg>
```

**Regras gerais dos SVGs:**
- Sempre usar `viewBox` para escalar corretamente
- Fontes no SVG: mínimo `font-size="28"`
- Cores somente da paleta da identidade
- Sem gradientes, sombras ou efeitos — visual limpo

---

## Paleta por papel

As cores vêm da identidade (ver "Identidade visual: de onde vem"). A skill cita cada cor pelo papel; o hex está só em `data/identidade.md`.

| Papel | Campo | Variável CSS | Uso |
|---|---|---|---|
| Fundo de impacto | `cor_fundo_impacto` | `--cor-fundo-impacto` | Capa, slides Tipo B, CTA |
| Fundo principal | `cor_fundo_principal` | `--cor-fundo-principal` | Slides claros, Tipo A, resumo, sub-capa |
| Acento principal | `cor_acento_principal` | `--cor-acento-principal` | Barras, marcadores, números, hook da capa |
| Acento secundário | `cor_acento_secundario` | `--cor-acento-secundario` | Elementos secundários de gráficos, numeração dos slides claros |
| Acento terciário | `cor_acento_terciario` | `--cor-acento-terciario` | Terceiro elemento em gráficos, variação pontual |

**Como usar:**
- Slides de impacto (capa, Tipo B, CTA): fundo de impacto, texto no fundo principal, destaque no acento principal
- Slides claros (Tipo A, sub-capa, resumo): fundo principal, texto no fundo de impacto, acento principal só em forma (barra, marcador), não em texto, a menos que o contraste passe 4.5:1
- Gráficos: fundo de impacto no elemento principal, acento principal no destaque, acentos secundário e terciário nos elementos secundários

**Regra:** nunca use cores fora desta paleta sem autorização explícita da pessoa.

---

## Processo

1. **Leia o input** — tema livre ou arquivo de post
2. **Planeje os slides** — defina quantos slides (8–12), o gancho da capa e um ponto por slide de conteúdo
3. **Mostre o plano à pessoa** — liste os slides com título de cada um antes de renderizar
4. **Aguarde aprovação** — só gere o HTML após a pessoa confirmar o plano
5. **Gere o HTML** — salve em `carousel_studio/rascunhos/<slug>.html` seguindo a estrutura abaixo
6. **Renderize o PDF**:
   ```bash
   node carousel_studio/render.mjs --input carousel_studio/rascunhos/<slug>.html --output carousel_studio/rascunhos/<slug>.pdf
   ```
7. **Informe o caminho** do PDF gerado

---

## Estrutura do HTML

O HTML gerado pela skill deve seguir este esqueleto exato. O `render.mjs` depende da classe `.slide` para contar e paginar os slides. Troque os `{{campo}}` pelos valores da identidade (ver "Identidade visual: de onde vem").

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  /* Paleta da identidade: o único lugar com hex */
  :root {
    --cor-fundo-impacto: {{cor_fundo_impacto}};
    --cor-fundo-principal: {{cor_fundo_principal}};
    --cor-acento-principal: {{cor_acento_principal}};
    --cor-acento-secundario: {{cor_acento_secundario}};
    --cor-acento-terciario: {{cor_acento_terciario}};
  }

  @page { size: 1080px 1080px; margin: 0; }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    font-family: 'Barlow', Arial, sans-serif;
    background: var(--cor-fundo-principal);
  }

  /* Cada .slide vira uma página do PDF */
  .slide {
    width: 1080px;
    height: 1080px;
    overflow: hidden;
    position: relative;
    break-after: page;
  }
  .slide:last-child { break-after: auto; }

  /* Área segura: 880×880 centralizada, padding de 80px */
  .safe-area {
    position: absolute;
    top: 80px; left: 80px;
    width: 880px; height: 880px;
    display: flex;
    flex-direction: column;
    justify-content: center;
  }
</style>
</head>
<body>

  <!-- SLIDE 1: Capa (na prática, um dos templates de capas-template.html) -->
  <div class="slide" style="background: var(--cor-fundo-impacto);">
    <div class="safe-area">
      <h1 style="color: var(--cor-acento-principal); font-size: 52px; line-height: 1.2;">
        [título / gancho]
      </h1>
      <p style="color: var(--cor-fundo-principal); font-size: 36px; margin-top: 24px;">
        [subtítulo]
      </p>
    </div>
  </div>

  <!-- SLIDES DE CONTEÚDO -->
  <div class="slide" style="background: var(--cor-fundo-principal);">
    <div class="safe-area">
      <!-- Número do slide: fonte menor mas acima de 24pt (32px = ~24pt) -->
      <span style="color: var(--cor-acento-secundario); font-size: 32px; font-weight: bold;">2 / 10</span>
      <h2 style="color: var(--cor-fundo-impacto); font-size: 44px; margin-top: 16px;">
        [título do ponto]
      </h2>
      <p style="color: var(--cor-fundo-impacto); font-size: 32px; margin-top: 20px; line-height: 1.5;">
        [corpo — máximo 3 linhas]
      </p>
    </div>
  </div>

  <!-- SLIDE FINAL: CTA. Copie o último slide de capas-template.html
       (texto, chamada de ação, linha de seguir e assinatura); a versão
       abaixo é só a estrutura mínima. -->
  <div class="slide" style="background: var(--cor-fundo-impacto);">
    <div class="safe-area">
      <h2 style="color: var(--cor-fundo-principal); font-size: 44px;">
        [pergunta ou provocação para comentar]
      </h2>
      <!-- CTA e nome nunca dentro de 60px das bordas -->
      <p style="color: var(--cor-acento-principal); font-size: 36px; margin-top: 32px;">
        Comente abaixo
      </p>
      <p style="color: var(--cor-fundo-principal); font-size: 32px; opacity: 0.6; margin-top: 16px;">
        {{linha_de_seguir}}
      </p>
      <p style="color: var(--cor-fundo-principal); font-size: 36px; font-weight: 700; margin-top: 40px;">
        {{nome}}
      </p>
    </div>
  </div>

</body>
</html>
```

### Tamanhos de fonte obrigatórios (mínimo 24pt = 32px)

| Elemento | Tamanho mínimo |
|---|---|
| Corpo de texto | 32px |
| Subtítulos | 36px |
| Títulos | 44px |
| Gancho da capa | 52px |
| Numeração do slide | 32px |

### Checklist antes de gerar o HTML

- [ ] Nenhum texto abaixo de 32px
- [ ] Todo conteúdo dentro da `.safe-area` (80px de padding)
- [ ] CTAs e nome a pelo menos 60px das bordas
- [ ] Cores somente da paleta da identidade, via `var(--cor-...)`; hex só no bloco `:root`
- [ ] Nenhum `{{` sobrando
- [ ] Uma ideia por slide de conteúdo
- [ ] Numeração presente em todos os slides de conteúdo

---

## Regras de conteúdo

- Sem hashtags
- Sem emojis
- Sem travessão (—)
- Sem linguagem motivacional vazia
- Cada slide deve ser legível em menos de 5 segundos

---

## Output esperado

Ao finalizar, informe:
1. Quantos slides foram gerados
2. O caminho do PDF
3. Se quiser ajustar algum slide, é só pedir
