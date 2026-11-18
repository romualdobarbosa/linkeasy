# ADR 0001. Carrossel em PDF publicado à mão

- Data: 18/11/2026
- Status: aceita

## Contexto

O `/carrossel` gera um PDF de 8 a 12 slides. O `post.py` publica texto com imagens png e jpg, mas não publica PDF, então o carrossel eu subo direto no LinkedIn.

Por muito tempo achei que isso era limitação da API. Não é. A [Documents API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/documents-api) do LinkedIn aceita PDF de até 100 MB e 300 páginas, com o mesmo caminho das imagens (`initializeUpload`, upload do arquivo e o post com o `urn:li:document` em `content.media`). A permissão é a mesma `w_member_social` que eu já uso. Os exemplos da documentação usam página de empresa como dona do documento, então o upload pra perfil pessoal ainda teria que ser conferido com uma chamada real.

## Decisão

Não implementei o upload de PDF no `post.py`. Carrossel continua sendo publicado à mão.

O motivo é de uso, não técnico. Eu quase não vejo carrossel no meu feed do LinkedIn, e na prática publico bem mais post com imagem do que carrossel. Pra algo que acontece de vez em quando, subir o PDF à mão custa menos que manter mais um fluxo de upload (com o status de processamento do documento, que é assíncrono) e os testes dele.

## Consequências

- O post de carrossel não passa pela fila, então não tem `scheduled_at`, `post_id` nem registro automático em `history/`.
- Se carrossel virar formato frequente, a decisão muda. O caminho é o mesmo do `upload_image`, trocando o endpoint por `/rest/documents` e esperando o documento ficar `AVAILABLE` antes de criar o post.
