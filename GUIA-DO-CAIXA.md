# Rancho da tia nina — guia do caixa

## Instalar e abrir

1. Coloque a pasta em um local definitivo no computador do caixa.
2. Instale Python 3.12 ou superior caso necessário.
3. Abra `INSTALAR-CAIXA.cmd`. Esta etapa precisa de internet.
4. Abra `INICIAR-CAIXA.cmd`. O navegador abre em `http://127.0.0.1:8000`.
5. Mantenha a janela do programa aberta durante o atendimento. Para encerrar, use Ctrl+C nessa janela.

Após a instalação, funciona sem internet. Somente o computador do caixa tem acesso. Não exige login: o acesso físico fica protegido pela conta do Windows. Não exponha o servidor à internet.

## Preparar produtos e estoque

A piscina vem cadastrada por R$ 20 por pessoa. Não há cobrança de entrada. Cadastre os preços reais das bebidas, porções e peixes em **Produtos e estoque**.

- Cerveja: unidade, controlar estoque, preço e mínimo total.
- Peixe: quilo, preço por kg; pode ficar sem controle de saldo se não houver pesagem do estoque.
- Porção: unidade, sem controle de ingredientes nesta versão.

Conte o estoque inicial e registre a quantidade no depósito. Exemplo: entrada de 24 cervejas e venda de 3 deixa 21 no depósito. Saldos da versão antiga com freezer são somados automaticamente ao depósito, com backup prévio e sem apagar o histórico.

O **ajuste** define o saldo final contado; não soma ao saldo anterior. Informe sempre um motivo. Perdas e consumo interno são retiradas com motivo. O alerta considera o saldo do depósito.

## Comandas e pagamento

1. Abra a comanda pelo nome/identificação e mesa opcional. Não precisa de CPF.
2. Selecione produto e quantidade. Para peixe, informe o peso em kg, como 1,750 (ou 1.750, conforme o navegador). Para piscina, informe o número de pessoas.
3. Todos os produtos com controle de estoque saem do depósito.
4. O sistema bloqueia venda sem saldo. Após falha de conexão, confira os itens antes de repetir.
5. Para corrigir um item, cancele com motivo. Ele volta ao depósito. Se houve consumo ou perda, registre também a perda nesse local.
6. Confira o recebimento e confirme o pagamento. Dinheiro aceita valor maior e calcula troco; Pix e cartão exigem o total exato.

Uma comanda aceita uma forma de pagamento. O sistema registra, mas não confirma Pix, não opera a maquininha e não emite documento fiscal. Contas pagas ficam no histórico e liberam a mesa para outra visita. Para cancelar uma comanda, cancele seus itens primeiro.

## Fechamento diário

Em **Caixa e histórico**, escolha a data. O relatório usa a data do recebimento, mesmo se a comanda foi aberta antes. Confira os totais por forma de pagamento.

Informe apenas o dinheiro líquido das vendas contado, sem o fundo inicial. O sistema registra a diferença e o fechamento. Não há despesas, sangria ou fundo de caixa nesta versão. Para receber mais no dia fechado, reabra o dia e confira novamente ao terminar.

## Backup e restauração

O banco é `dados/caixa.sqlite3`. Cópias automáticas são feitas ao abrir o programa e após cada pagamento, em `dados/backups`. Use **Criar backup agora** ao encerrar o expediente e após mudanças no estoque.

Copie regularmente um backup para pendrive ou outro dispositivo. Cópias no mesmo disco não protegem contra perda do computador. Os backups são mantidos até remoção manual; acompanhe o espaço livre.

Para restaurar: encerre o programa, guarde uma cópia do banco atual, copie o backup desejado para `dados/caixa.sqlite3` e reinicie. Não substitua o banco com o programa aberto.

## Dados antigos e limites

Esta versão usa um banco novo. O antigo `pesqueiro.db` não é lido, apagado ou migrado automaticamente. Se já houver registros reais no antigo sistema, migre-os antes de adotar esta versão. O pacote não inclui os bancos publicados no repositório.

Reservas, delivery, ingredientes, pagamento dividido e integração de pagamentos ficam para outra versão.

## Testes

Execute `python -m pip install -r requirements-dev.txt` e `python -m pytest`. Os testes usam bancos temporários separados dos dados reais.

## Apagar todos os dados

Em Caixa e histórico, abra Administração dos dados e clique em Apagar todos os dados. Digite APAGAR TUDO e confirme. Produtos (inclusive piscina), saldos, comandas, pagamentos, movimentações e fechamentos serão apagados. O sistema só prossegue se conseguir criar e verificar um backup. Os backups anteriores são mantidos. Depois, cadastre novamente os produtos e os saldos iniciais. Para recuperar, siga a restauração descrita acima.
