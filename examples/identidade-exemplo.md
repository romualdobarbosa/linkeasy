---
nome: "Lia Fontes"
tagline: "Dados para quem decide"
foto: ""
linha_de_seguir: "Me segue para mais conteúdo sobre dados no dia a dia."
cor_fundo_impacto: "#183A37"
nome_fundo_impacto: "Verde Pinho"
cor_fundo_principal: "#F5F3EE"
nome_fundo_principal: "Papel"
cor_acento_principal: "#F4845F"
nome_acento_principal: "Coral"
cor_acento_secundario: "#3E6C8F"
nome_acento_secundario: "Azul Aço"
cor_acento_terciario: "#7A4E7E"
nome_acento_terciario: "Ameixa"
---

# Identidade visual: Lia Fontes (pessoa fictícia, identidade-exemplo)

Identidade inventada para a mesma persona da `voz-exemplo`. É o que as skills `/carrossel` e `/infografista` usam quando a instalação não tem `data/identidade.md`. Quem configura o linkeasy grava a própria identidade em `data/identidade.md` (gitignored) pelo `/criar-voz`, no mesmo formato deste arquivo.

## Formato

Frontmatter YAML simples: uma `chave: valor` por linha, sem listas nem blocos aninhados. Valor entre aspas quando tiver `#`, `:` ou acento. Campo vazio fica `""`.

| Campo | O que é |
|---|---|
| `nome` | Nome como aparece na assinatura e nas capas |
| `tagline` | Uma linha abaixo do nome na assinatura (área, foco) |
| `foto` | Caminho da foto de perfil, relativo à raiz do repo (ex. `data/Photos/perfil.jpg`). Opcional: vazio gera a assinatura sem foto |
| `linha_de_seguir` | Frase do último slide do carrossel convidando a seguir |
| `cor_*` | Hex de cada papel da paleta (abaixo) |
| `nome_*` | Nome da cor de cada papel, opcional, só para conversar sobre ela (`nome_fundo_impacto`, `nome_fundo_principal`, `nome_acento_principal`, `nome_acento_secundario`, `nome_acento_terciario`) |

## Papéis da paleta

As skills citam as cores pelo papel, nunca pelo hex. Nos HTML e SVG, cada papel vira uma variável CSS: `cor_fundo_impacto` vira `--cor-fundo-impacto`, e assim por diante.

- **Fundo de impacto** (`cor_fundo_impacto`): fundo escuro da capa, dos slides de título grande e do CTA. Também é a cor do texto sobre o fundo principal.
- **Fundo principal** (`cor_fundo_principal`): fundo claro dos slides de conteúdo, da sub-capa e do resumo. Também é a cor do texto sobre o fundo de impacto.
- **Acento principal** (`cor_acento_principal`): destaque. Hook da capa, chamada de ação, barras e marcadores, a moldura da foto. Precisa ser legível sobre o fundo de impacto.
- **Acento secundário** (`cor_acento_secundario`): segundo elemento dos gráficos e numeração dos slides claros.
- **Acento terciário** (`cor_acento_terciario`): terceiro elemento dos gráficos e variação pontual.

## Contraste

Texto claro sobre fundo de impacto e texto escuro sobre fundo principal precisam passar WCAG AA (4,5:1). Os números desta paleta:

| Par | Contraste |
|---|---|
| Fundo principal sobre fundo de impacto (e o inverso) | 11,14:1 |
| Acento principal sobre fundo de impacto | 4,89:1 |
| Acento secundário sobre fundo principal | 5,05:1 |
| Acento terciário sobre fundo principal | 5,88:1 |

O acento principal sobre o fundo principal fica em 2,28:1: nos slides claros ele serve para barra, marcador e forma, não para texto.
