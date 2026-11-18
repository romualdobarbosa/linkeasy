Antes de mexer numa consulta SQL lenta, eu rodo EXPLAIN. Parece óbvio, mas é um passo fácil de pular.

O EXPLAIN mostra o plano que o banco escolheu para executar a consulta: a ordem das tabelas, o tipo de junção e se ele usou índice ou leu a tabela inteira. Sem o plano, otimizar vira chute.

Um exemplo. Uma consulta filtra pedidos por data e demora vários segundos. A primeira reação é criar um índice na coluna de data. Às vezes resolve. Às vezes o plano mostra que o gargalo era uma junção com uma tabela grande, sem índice na chave, e o índice novo só ocupa espaço.

O EXPLAIN ANALYZE executa a consulta de verdade e compara as linhas estimadas com as linhas reais. Quando as duas contas ficam muito distantes, as estatísticas da tabela costumam estar desatualizadas, e então o problema nem é a consulta.

O EXPLAIN não resolve tudo, e ler um plano grande leva tempo no começo. Ainda assim, é mais honesto do que reescrever a consulta três vezes torcendo para melhorar.

Na prática, na próxima consulta lenta, rode o EXPLAIN primeiro e veja onde está o maior custo.

Qual é a primeira coisa que você confere numa consulta lenta?
