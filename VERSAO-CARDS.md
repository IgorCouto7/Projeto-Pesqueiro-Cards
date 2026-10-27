# Testar as duas versões

A tela anterior continua em `index.html`, sem alterações. A versão nova está
em `cards.html`. Ambas usam o mesmo banco e mantêm o agrupamento dos produtos.
O commit `7756ab6` também guarda a versão anterior completa no GitHub.

1. Inicie a API com `poetry run uvicorn App.api.main:app --reload`.
2. Abra http://127.0.0.1:8000/cards para experimentar os cards.
3. Clique em **Nova comanda**, informe o nome da pessoa ou grupo e confirme.
   Não é necessário número de mesa nem CPF.
4. Clique no card para lançar produtos ou finalizar o pagamento. Use a busca
   para localizar um nome e a aba **Pagas** para consultar contas finalizadas.
5. Para voltar ao visual anterior, use **Acessar versão anterior** no topo ou
   abra http://127.0.0.1:8000/classico. Não precisa desfazer código nem apagar dados.

As comandas existentes aparecem automaticamente. Cada chegada abre um
atendimento separado, mesmo quando duas pessoas têm o mesmo nome. O número
pequeno da comanda e a data ajudam a distinguir homônimos; não são números de mesa.
Os cards são carregados do banco, inclusive depois de atualizar a página.
Use **Atualizar** para buscar lançamentos feitos em outro dispositivo.

O novo fluxo salva CPF ausente como NULL, sem inventar documentos. O cadastro
completo da versão anterior continua disponível. As respostas de clientes
aceitam CPF ausente para também listar os atendimentos criados só pelo nome.
Não é necessária migração do banco SQLite atual.
