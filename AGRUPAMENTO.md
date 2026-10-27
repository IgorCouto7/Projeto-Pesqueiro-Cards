# Agrupamento na visualização da comanda

1. A aplicação usa FastAPI e SQLAlchemy no backend e `index.html` no frontend.
   Atualmente a comanda é identificada por ID e cliente; não existe campo de mesa.
   O resumo é sempre calculado para a comanda selecionada, sem combinar comandas.
2. As respostas de comanda incluem `itens_agrupados`, além de `itens`, que continua
   contendo cada lançamento original com seu ID, quantidade e preço.
3. O agrupamento usa nome exato do produto e preço unitário do lançamento.
   Duas cervejas a R$ 8 e mais uma a R$ 8 aparecem como quantidade 3 e R$ 24.
   Uma cerveja posterior a R$ 10 aparece em outra linha, preservando o preço
   histórico. Nomes diferentes, inclusive marcas, maiúsculas e espaços, não são
   unificados automaticamente, pois não existe um catálogo com ID de produto.
4. A página usa o resumo para mostrar quantidade, preço unitário e subtotal.
   A criação de itens, o total registrado e o fechamento não foram alterados.
   Não é necessária migração: o resumo também funciona com lançamentos antigos.
5. Atualize o backend e o HTML juntos e recarregue a página. Abra uma comanda,
   lance 2 cervejas a R$ 8 e depois mais 1 a R$ 8: o painel mostrará uma linha
   com 3 cervejas e R$ 24. Lance outra a R$ 10 para conferir os preços separados.

## Testes

```sh
poetry run pytest
python -B -m unittest App.tests.test_agrupamento -v
node --test App/tests/comanda_frontend.test.cjs
```

Os novos testes de API usam SQLite em memória e restauram as dependências
substituídas ao terminar. Cobrem preservação dos lançamentos, isolamento entre
comandas, preços históricos, soma decimal, consulta repetida, comanda vazia,
ID inexistente e fechamento. O teste da página verifica o uso do resumo,
subtotais, preços diferentes e limpeza da lista ao trocar para comanda vazia.
