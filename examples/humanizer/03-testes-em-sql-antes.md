Comecei a escrever testes para as minhas queries SQL e queria compartilhar como está sendo.

A ideia é simples: para cada query que alimenta um relatório, crio uma tabela pequena com 10 a 20 linhas de entrada e o resultado que eu espero. Um script roda a query nessa tabela e compara com o esperado.

Em duas semanas, os testes pegaram dois erros que iam para produção: um JOIN que duplicava clientes com mais de um endereço e um filtro de data que deixava de fora o último dia do mês.

O custo é real — cada teste leva uns 15 minutos para montar. Mas tem valido a pena.

Se alguém tiver uma forma melhor de montar os dados de teste, me avise se puder compartilhar.
