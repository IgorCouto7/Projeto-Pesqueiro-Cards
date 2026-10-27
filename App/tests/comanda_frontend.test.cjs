const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

test('painel exibe resumo agrupado, preços históricos e comanda vazia', () => {
    const html = fs.readFileSync(path.join(__dirname, '../../index.html'), 'utf8');
    const elements = {};
    const context = vm.createContext({
        fetch: async () => ({ ok: true, json: async () => [] }),
        document: { getElementById(id) {
            return elements[id] ??= { style: {}, innerHTML: '', innerText: '' };
        } },
    });
    vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1], context);
    context.carregarPainel({
        id: 5, valor_total: 34, status: 'ABERTA',
        itens: [{ nome_produto: 'NAO MOSTRAR LANCAMENTO BRUTO' }],
        itens_agrupados: [
            { nome_produto: 'Cerveja', quantidade: 3, preco_unitario: 8, valor_total: 24 },
            { nome_produto: 'Cerveja', quantidade: 1, preco_unitario: 10, valor_total: 10 },
        ],
    });
    const rendered = elements.listaPedidosDetalhe.innerHTML;
    assert.equal((rendered.match(/<tr>/g) || []).length, 2);
    assert.match(rendered, /<td>3<\/td>/);
    assert.match(rendered, /R\$ 24\.00/);
    assert.match(rendered, /R\$ 10\.00/);
    assert.doesNotMatch(rendered, /NAO MOSTRAR/);
    context.carregarPainel({ id: 6, valor_total: 0, status: 'ABERTA', itens_agrupados: [] });
    assert.match(elements.listaPedidosDetalhe.innerHTML, /Nenhum pedido/);
    assert.doesNotMatch(elements.listaPedidosDetalhe.innerHTML, /Cerveja/);
});
