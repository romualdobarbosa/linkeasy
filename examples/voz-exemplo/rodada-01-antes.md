Antes de mexer numa consulta SQL lenta, eu rodo EXPLAIN. Parece óbvio, mas é um passo fácil de pular.

O EXPLAIN mostra o plano que o banco escolheu pra executar a consulta, ou seja, a ordem das tabelas, o tipo de junção e se ele usou índice ou leu a tabela inteira. Sem isso, otimizar vira chute.

Tipo uma consulta que filtra pedidos por data e demora vários segundos. A primeira reação é criar um índice na coluna de data. Às vezes resolve. Às vezes o plano mostra que o gargalo era outro, uma junção com uma tabela grande sem índice na chave, e o índice novo só ocupa espaço.

O EXPLAIN ANALYZE vai além e executa a consulta de verdade, comparando as linhas estimadas com as linhas reais. Quando essas duas contas ficam muito distantes, as estatísticas da tabela costumam estar desatualizadas (e aí o problema nem é a consulta).

Não resolve tudo, e ler um plano grande leva tempo no começo. Mas é mais honesto do que reescrever a consulta três vezes torcendo pra melhorar.

Na próxima consulta lenta, roda o EXPLAIN primeiro e olha onde está o maior custo.
