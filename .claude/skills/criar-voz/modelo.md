---
name: voz-{{slug}}
description: Escreve ou reescreve texto público em nome de {{Nome}} ({{tipos de texto da entrevista}}) na voz de {{Nome}}, sem marcas de IA. Use para qualquer texto assinado por {{Nome}}, inclusive revisar rascunhos do redator antes de publicar.
---

<!--
MOLDE DA SKILL DE VOZ. Como preencher:
- {{...}} é valor a trocar. Comentário HTML que começa com PREENCHER é instrução de preenchimento.
- Tudo fora de {{...}} e dos comentários é fixo: copie como está.
- Antes de gravar, apague todos os comentários HTML, inclusive este.
- Um traço só entra com evidência: citação curta (até ~20 palavras) de uma amostra ou de
  uma resposta da entrevista, com a origem entre parênteses. Sem evidência, o traço fica de fora.
-->

# Voz de {{Nome}}

Texto público em nome de {{Nome}}. Duas etapas, nesta ordem:

1. Escreva (ou reescreva) seguindo o perfil de voz abaixo.
2. Passe o resultado pela skill `humanizer` em modo embutido. Onde o humanizer e este perfil discordarem, vale este perfil: ele é a amostra de escrita que o humanizer pede.

Não invente fato, número, nome ou citação. Os números vêm do rascunho, do projeto ou de {{Nome}}. Se uma frase precisa de um dado que não está no material, pergunte ou escreva uma frase mais simples.

Não atribua a {{Nome}} opinião ou sentimento que não foi declarado ("o que mais me chamou atenção", "fiquei impressionado"). Use só os que estão no rascunho ou no pedido.

Confira toda aproximação contra o número exato: 1,48 milhão é "quase 1,5", não "mais de 1,5". E "só" ou "apenas" só cabem quando o número é de fato o menor da comparação.

## Perfil de voz

Fontes: {{lista das amostras, uma por item: tipo de texto e data, ex. "post de LinkedIn de 2024-09"}} e a entrevista de {{AAAA-MM-DD}}.

<!-- PREENCHER: de 5 a 10 traços, um parágrafo cada, no formato abaixo. Comece pelos traços
que mais aparecem nas amostras. A explicação diz o que fazer ao escrever, em afirmação positiva.
Evidência vinda de correção em rodada de teste usa a origem "rodada NN". -->

**{{Traço em uma frase.}}** {{Explicação: como o traço aparece no texto e quando usar.}} Evidência: "{{citação curta}}" ({{amostra NN | entrevista | rodada NN}}).

## Ajuste por tipo de texto

<!-- PREENCHER: um item por tipo de texto que a pessoa disse que vai escrever (entrevista).
Diga o que muda em relação ao perfil: tamanho, abertura, fecho, quanto do coloquial entra. -->

- **{{Tipo de texto}}:** {{o que muda nesse tipo}}

## Regras gerais

Português com acentuação e ortografia corretas, mesmo que as amostras tenham erro de digitação.

<!-- PREENCHER: regras de pontuação, formalidade e vocabulário que vieram da entrevista ou das
amostras, cada uma com a origem entre parênteses. Inclua as palavras que a pessoa usa (e quando)
e as que evita, com a troca que ela prefere. -->

{{Regra.}} ({{origem}})

Proibido em qualquer texto público:

<!-- PREENCHER: um item por resposta à pergunta "o que nunca entra", com a alternativa quando
houver (ex.: "travessão (—); use vírgula ou ponto"). -->

- {{item proibido; alternativa}}
