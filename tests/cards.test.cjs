const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const html = fs.readFileSync(path.join(__dirname,'../caixa.html'),'utf8');
const source = html.match(/async function refreshOrders\(\)[\s\S]*?(?=async function selectOrder)/)[0];

test('cards por nome preservam identidade, total e seleção da comanda',async()=>{
    const elements = {count:{},orders:{innerHTML:'',querySelectorAll(){return buttons;}}};
    const buttons = [{dataset:{order:'1'}},{dataset:{order:'2'}}];
    let selected;
    const context = vm.createContext({
        activeOrders:[],current:{id:2},
        api:async()=>[
            {id:1,nome:'João <script>',mesa:'',total:2400},
            {id:2,nome:'João <script>',mesa:'',total:800},
        ],
        $:id=>elements[id],
        esc:s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;'),
        money:c=>(c/100).toLocaleString('pt-BR',{style:'currency',currency:'BRL'}),
        selectOrder:async id=>{selected=id;},notify:()=>{},
    });
    vm.runInContext(source,context);
    await context.refreshOrders();
    assert.equal(elements.count.textContent,2);
    assert.match(elements.orders.innerHTML,/data-order="1"/);
    assert.match(elements.orders.innerHTML,/data-order="2"/);
    assert.match(elements.orders.innerHTML,/chosen/);
    assert.match(elements.orders.innerHTML,/aria-pressed="true"/);
    assert.match(elements.orders.innerHTML,/João &lt;script&gt;/);
    assert.doesNotMatch(elements.orders.innerHTML,/<script>/);
    assert.match(elements.orders.innerHTML,/24,00/);
    assert.doesNotMatch(elements.orders.innerHTML,/Sem mesa/);
    await buttons[1].onclick();
    assert.equal(selected,2);
    context.api=async()=>[];
    await context.refreshOrders();
    assert.equal(elements.count.textContent,0);
    assert.match(elements.orders.innerHTML,/Nenhuma comanda aberta/);
});
