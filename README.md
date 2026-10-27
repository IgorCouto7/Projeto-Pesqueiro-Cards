# Rancho da tia nina — versão com cards

Esta versão mantém o caixa completo do [Projeto-Pesqueiro de IgorCouto7](https://github.com/IgorCouto7/Projeto-Pesqueiro), com uma alteração visual: as comandas em atendimento aparecem em cards na área central da primeira aba.

## As três telas

1. **Comandas:** cards com nome e total no centro. Clique em um card para abrir a janela de consumo, cancelamentos, recebimento e troco. Escolha um produto cadastrado e informe a quantidade; o preço é automático.
2. **Produtos e estoque:** preservada, incluindo cadastro, preço, unidade, saldo, entrada, perda, ajuste e movimentações.
3. **Caixa e histórico:** preservada, incluindo recebimentos, fechamento, reabertura, contas pagas e backups.

Os cards usam o nome da pessoa ou do grupo. Clique em **Nova comanda** para abrir um atendimento só pelo nome, sem numerar mesas. Os preços são definidos na aba **Produtos e estoque**, não durante o lançamento.

![Prévia com dados fictícios](previa-cards.png)

## Instalar e abrir no Windows

Requer Python 3.12 ou superior.

1. Execute **INSTALAR-CAIXA.cmd** uma vez.
2. Execute **INICIAR-CAIXA.cmd**.
3. Abra http://127.0.0.1:8000 ou http://127.0.0.1:8000/cards.
4. Para comparar com a lista lateral original, abra http://127.0.0.1:8000/classico.

As duas apresentações usam o mesmo banco do caixa, `dados/caixa.sqlite3`. Nenhum banco de clientes é publicado neste repositório. O banco do protótipo antigo (`pesqueiro.db`) não é convertido automaticamente.

Consulte o [guia completo do caixa](GUIA-DO-CAIXA.md).

## Desenvolvimento e testes

```sh
python -m pip install -r requirements-dev.txt
python -m pytest
node --test tests/cards.test.cjs
python iniciar.py
```

A suíte ativa está em `tests/`. Os arquivos de `App/models`, `App/schemas` e `App/tests` são referências do protótipo antigo, como na base original. A entrada `App.api.main:app` também aponta para o caixa completo.

Os testes verificam as operações originais de estoque, preços históricos, pagamentos, cancelamentos e fechamento. Os novos testes também verificam a seleção dos cards e que o HTML das abas de estoque e caixa e a lógica das operações continuam iguais à apresentação clássica.

## Origem e versões

- Base completa: [IgorCouto7/Projeto-Pesqueiro](https://github.com/IgorCouto7/Projeto-Pesqueiro), revisão `36eed34a73a01c0078cb8b580832950c611dbd81`.
- Origem acadêmica da estrutura: [C214-L1-202501/Projeto-Pesqueiro](https://github.com/C214-L1-202501/Projeto-Pesqueiro). Créditos aos autores e colaboradores das bases reutilizadas.
- A adaptação anterior, feita sobre o protótipo simplificado, fica preservada na branch `backup/prototipo-cards`.
- A apresentação clássica completa está em `caixa-classico.html`; a apresentação com cards está em `caixa.html`.

Este é um repositório independente, não um fork do GitHub. Não foi atribuída uma nova licença ao código reutilizado.

