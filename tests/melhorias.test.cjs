const {test} = require('node:test');
const assert = require('node:assert/strict');
const ui = require('../melhorias.js');

test('busca por parte do nome ignora acentos, caixa e espaços externos',()=>{
    assert.equal(ui.corresponde('João e família',' JOAO '),true);
    assert.equal(ui.corresponde('João e família','familia'),true);
    assert.equal(ui.corresponde('Ana','João'),false);
    assert.equal(ui.corresponde('Ana',''),true);
});

const item=(id,extra={})=>({id,produto:1,nome:'Cerveja',preco:800,local:'DEPOSITO',quantidade:1000,total:800,cancelado:0,...extra});
test('agrupa quantidades e centavos sem modificar lançamentos originais',()=>{
    const itens=[item(1,{quantidade:2000,total:1600}),item(2)];
    const antes=JSON.stringify(itens);
    const grupos=ui.agrupar(itens);
    assert.equal(grupos.length,1);
    assert.equal(grupos[0].quantidade,3000);
    assert.equal(grupos[0].total,2400);
    assert.deepEqual(grupos[0].lancamentos,[1,2]);
    assert.equal(JSON.stringify(itens),antes);
});
test('preços históricos e identidades diferentes não são misturados',()=>{
    const grupos=ui.agrupar([item(1),item(2,{preco:1000,total:1000}),item(3,{produto:2})]);
    assert.equal(grupos.length,3);
    assert.deepEqual(grupos.map(g=>g.total),[800,1000,800]);
});
test('cancelamento retira somente o lançamento cancelado do resumo',()=>{
    const grupos=ui.agrupar([item(1,{cancelado:1}),item(2)]);
    assert.equal(grupos[0].quantidade,1000);
    assert.equal(grupos[0].total,800);
    assert.deepEqual(grupos[0].lancamentos,[2]);
    assert.deepEqual(ui.agrupar([item(1,{cancelado:1})]),[]);
});
test('peso conserva a soma dos subtotais arredondados na venda',()=>{
    const grupos=ui.agrupar([item(1,{quantidade:333,preco:100,total:33}),item(2,{quantidade:333,preco:100,total:33})]);
    assert.equal(grupos[0].quantidade,666);
    assert.equal(grupos[0].total,66);
});
test('local de estoque não divide o mesmo produto na conta do cliente',()=>{
    const grupos=ui.agrupar([item(1),item(2,{local:'FREEZER'})]);
    assert.equal(grupos.length,1);
    assert.equal(grupos[0].total,1600);
});
test('favoritos restauram IDs sem fixar preços e permitem seleção vazia',()=>{
    const catalogo=[{id:1,preco:800},{id:2,preco:1000}];
    assert.deepEqual(ui.favoritosSalvos(null,catalogo),[1,2]);
    assert.deepEqual(ui.favoritosSalvos('[2,2,"1",null]',catalogo),[2]);
    assert.deepEqual(ui.favoritosSalvos('[]',catalogo),[]);
    assert.deepEqual(ui.favoritosSalvos('invalido',catalogo),[1,2]);
});
