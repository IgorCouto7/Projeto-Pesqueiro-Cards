'use strict';

// Quantidades em milésimos e valores em centavos, como no banco do caixa.
const PesqueiroUI = {
    normalizar(texto) {
        return String(texto ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('pt-BR').trim();
    },
    corresponde(nome, busca) {
        return this.normalizar(nome).includes(this.normalizar(busca));
    },
    agrupar(itens) {
        const grupos = new Map();
        for (const item of itens) {
            if (item.cancelado) continue;
            const chave = JSON.stringify([item.produto, item.nome, item.preco]);
            if (!grupos.has(chave)) grupos.set(chave, {...item, quantidade: 0, total: 0, lancamentos: []});
            const grupo = grupos.get(chave);
            grupo.quantidade += item.quantidade;
            // Soma os valores gravados, preservando arredondamentos por lançamento.
            grupo.total += item.total;
            grupo.lancamentos.push(item.id);
        }
        return [...grupos.values()];
    },
    favoritosSalvos(valor, catalogo) {
        if (valor === null) return catalogo.slice(0, 6).map(p => p.id);
        try {
            const ids = JSON.parse(valor);
            if (!Array.isArray(ids)) throw Error('Formato inválido');
            return [...new Set(ids.filter(Number.isInteger))];
        } catch { return catalogo.slice(0, 6).map(p => p.id); }
    },
};

if (typeof module !== 'undefined' && module.exports) module.exports = PesqueiroUI;
if (typeof document !== 'undefined') (() => {
    const estilo = document.createElement('style');
    estilo.textContent = `
        .search-cards{display:flex;gap:14px;align-items:center;flex-wrap:wrap;margin:16px 0}
        .search-cards input{max-width:360px}.search-cards label{margin:0;flex:1;min-width:200px}
        .search-cards label span{display:block;margin-bottom:7px}.quick-products{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}
        .quick-products button{text-align:left;background:#e9f1e4;color:#234b3b;font-size:13px;margin-top:0}
        .quick-products small{display:block;margin-top:5px;font-weight:400}.favorite-settings{margin:12px 0;color:#416039}
        .favorite-settings label{display:flex;gap:10px;align-items:center}.favorite-settings input{width:auto}
        .individual-launches{margin:14px 0}.individual-launches summary{cursor:pointer;color:#21664e;font-weight:600}
        .receipt-actions{display:flex;gap:10px;margin:15px 0;flex-wrap:wrap}.receipt-heading{text-align:center;border-bottom:1px dashed #a8b4a4;padding-bottom:18px}
        .receipt-heading h2{margin:0 0 8px}.receipt-meta{line-height:1.7;overflow-wrap:anywhere}
        #receiptDialog{background:white}.receipt-total{display:flex;justify-content:space-between;gap:16px;font-size:24px;font-weight:700;border-top:2px solid #17372d;margin-top:18px;padding-top:15px}
        #receiptDialog th,#receiptDialog td{font-size:13px}#receiptDialog td:first-child{overflow-wrap:anywhere}
        #receiptDialog td:last-child,#receiptDialog th:last-child{text-align:right}.receipt-footer{text-align:center;font-size:12px;color:#6e7c70;margin-top:25px}
        @media print {
            body:has(#receiptDialog[open]) > :not(#receiptDialog){display:none!important}
            body:has(#receiptDialog[open]) dialog:not(#receiptDialog){display:none!important}
            #receiptDialog[open]{display:block!important;position:static!important;width:100%!important;max-width:none!important;max-height:none!important;overflow:visible!important;border:0!important;padding:0!important;margin:0!important;box-shadow:none!important;color:#000;background:#fff}
            #receiptDialog::backdrop{display:none!important}#receiptDialog .no-print{display:none!important}
            #receiptDialog tr{break-inside:avoid}#receiptDialog thead{display:table-header-group}
        }
    `;
    document.head.append(estilo);

    const busca = document.createElement('div');
    busca.className = 'search-cards';
    busca.innerHTML = '<label><span>Buscar comanda pelo nome</span><input id="buscaCards" type="search" placeholder="Ex.: João ou família" autocomplete="off"></label><span id="buscaResultado" class="muted" role="status"></span>';
    $('orders').before(busca);
    const semResultado = document.createElement('p');
    semResultado.id = 'semResultadoCards';
    semResultado.className = 'muted hidden';
    semResultado.textContent = 'Nenhuma comanda com esse nome. Tente outra parte do nome.';
    $('orders').after(semResultado);

    function filtrarCards() {
        const termo = $('buscaCards').value;
        let encontrados = 0;
        const nomes = new Map(activeOrders.map(o => [o.id, o.nome]));
        $('orders').querySelectorAll('[data-order]').forEach(botao => {
            const visivel = PesqueiroUI.corresponde(nomes.get(Number(botao.dataset.order)), termo);
            botao.classList.toggle('hidden', !visivel);
            if (visivel) encontrados++;
        });
        $('buscaResultado').textContent = `${encontrados} de ${activeOrders.length} comanda${activeOrders.length === 1 ? '' : 's'}`;
        $('semResultadoCards').classList.toggle('hidden', !activeOrders.length || encontrados > 0);
    }
    $('buscaCards').addEventListener('input', filtrarCards);
    const atualizarComandas = refreshOrders;
    refreshOrders = async function() { await atualizarComandas(); filtrarCards(); };

    const atalhos = document.createElement('div');
    atalhos.innerHTML = '<strong>Produtos favoritos</strong><div id="atalhosProdutos" class="quick-products"></div><details class="favorite-settings"><summary>Escolher favoritos</summary><p class="muted">Marque os produtos que quer ter à mão neste navegador.</p><div id="escolhaFavoritos"></div></details>';
    $('addItem').querySelector('h2').after(atalhos);
    const chaveFavoritos = 'pesqueiro.cards.favoritos.v1';
    let favoritos = null;
    function lerFavoritos() {
        let salvo = null;
        try { salvo = localStorage.getItem(chaveFavoritos); } catch { /* Atalhos funcionam nesta sessão. */ }
        return PesqueiroUI.favoritosSalvos(salvo, products);
    }
    function renderizarAtalhos() {
        if (favoritos === null) favoritos = lerFavoritos();
        $('atalhosProdutos').innerHTML = products.filter(p => favoritos.includes(p.id)).map(p =>
            `<button type="button" data-shortcut="${p.id}">${esc(p.nome)}<small>${money(p.preco)} / ${p.unidade === 'KG' ? 'kg' : 'un.'}</small></button>`
        ).join('') || '<span class="muted">Use “Escolher favoritos” para adicionar atalhos.</span>';
        $('atalhosProdutos').querySelectorAll('[data-shortcut]').forEach(b => b.onclick = () => {
            const produto = products.find(p => p.id === Number(b.dataset.shortcut));
            if (!produto) return;
            $('saleProduct').value = String(produto.id);
            const quantidade = $('addItem').elements.quantidade;
            quantidade.value = produto.unidade === 'KG' ? '' : '1';
            quantidade.focus();
        });
    }
    function renderizarFavoritos() {
        // Não fixa uma seleção vazia antes de o catálogo terminar de carregar.
        if (!products.length && favoritos === null) return;
        renderizarAtalhos();
        $('escolhaFavoritos').innerHTML = products.map(p =>
            `<label><input type="checkbox" data-favorite="${p.id}" ${favoritos.includes(p.id) ? 'checked' : ''}>${esc(p.nome)}</label>`
        ).join('');
        $('escolhaFavoritos').querySelectorAll('[data-favorite]').forEach(c => c.onchange = () => {
            const id = Number(c.dataset.favorite);
            favoritos = c.checked ? [...new Set([...favoritos, id])] : favoritos.filter(x => x !== id);
            try { localStorage.setItem(chaveFavoritos, JSON.stringify(favoritos)); }
            catch { notify('Favoritos disponíveis nesta sessão. O navegador não permitiu salvar a preferência.'); }
            renderizarAtalhos();
        });
    }
    const atualizarProdutos = refreshProducts;
    refreshProducts = async function() { await atualizarProdutos(); renderizarFavoritos(); };

    const individuais = document.createElement('details');
    individuais.className = 'individual-launches';
    individuais.id = 'lancamentosIndividuais';
    individuais.innerHTML = '<summary>Lançamentos individuais e cancelamentos</summary><p class="muted">Cada lançamento continua separado aqui. Cancele apenas o lançamento desejado.</p><div class="scroll"><table><thead><tr><th>Produto</th><th>Quantidade</th><th>Preço</th><th>Total</th><th></th></tr></thead><tbody id="itensIndividuais"></tbody></table></div>';
    $('items').closest('.scroll').after(individuais);
    const mostrarConta = document.createElement('button');
    mostrarConta.type = 'button';
    mostrarConta.id = 'conferirConta';
    mostrarConta.className = 'secondary';
    mostrarConta.textContent = 'Conferir / imprimir conta';
    $('orderTotal').parentElement.append(mostrarConta);

    function renderizarGrupos() {
        if (!current) return;
        // Move os nós originais, preservando os botões e eventos de cancelamento.
        $('itensIndividuais').replaceChildren(...$('items').childNodes);
        const grupos = PesqueiroUI.agrupar(current.itens);
        $('items').innerHTML = grupos.map(g => `<tr><td>${esc(g.nome)}</td><td>${qty(g.quantidade)}</td><td>${money(g.preco)}</td><td>${money(g.total)}</td><td>${current.status === 'ABERTA' ? '<button type="button" class="secondary" data-launches>Ver lançamentos</button>' : ''}</td></tr>`).join('') || '<tr><td colspan="5">Nenhum consumo lançado.</td></tr>';
        $('items').querySelectorAll('[data-launches]').forEach(b => b.onclick = () => {
            individuais.open = true;
            individuais.scrollIntoView({behavior: 'smooth', block: 'nearest'});
        });
        individuais.classList.toggle('hidden', !current.itens.some(i => !i.cancelado));
    }
    const desenharComanda = renderOrder;
    renderOrder = function() { desenharComanda(); renderizarGrupos(); renderizarFavoritos(); };

    const recibo = document.createElement('dialog');
    recibo.id = 'receiptDialog';
    recibo.className = 'order-dialog';
    recibo.setAttribute('aria-labelledby', 'tituloConta');
    recibo.innerHTML = '<div class="dialog-heading no-print"><h2 id="tituloConta">Conferência da conta</h2><button type="button" id="fecharConta" class="secondary" aria-label="Voltar ao consumo">Voltar</button></div><div id="conteudoConta"></div><div class="receipt-actions no-print"><button type="button" id="imprimirConta">Imprimir / salvar PDF</button><button type="button" id="voltarConta" class="secondary">Voltar ao consumo</button></div>';
    document.body.append(recibo);
    $('fecharConta').onclick = $('voltarConta').onclick = () => recibo.close();
    $('imprimirConta').onclick = () => window.print();
    mostrarConta.onclick = () => {
        if (!current) return;
        const grupos = PesqueiroUI.agrupar(current.itens);
        const unidade = id => products.find(p => p.id === id)?.unidade === 'KG' ? ' kg' : '';
        $('conteudoConta').innerHTML = `<div class="receipt-heading"><h2>Rancho da tia nina</h2><span>Conferência de consumo</span></div><div class="receipt-meta"><p><strong>${esc(current.nome)}</strong><br>Comanda #${current.id}${current.mesa ? ' · Mesa ' + esc(current.mesa) : ''}<br>Aberta em ${esc(new Date(current.aberta).toLocaleString('pt-BR'))}<br>Situação: ${current.status === 'PAGA' ? 'Paga' : 'Em aberto'}</p></div><table><thead><tr><th>Produto</th><th>Qtd.</th><th>Preço un.</th><th>Subtotal</th></tr></thead><tbody>${grupos.map(g => `<tr><td>${esc(g.nome)}</td><td>${qty(g.quantidade)}${unidade(g.produto)}</td><td>${money(g.preco)}</td><td>${money(g.total)}</td></tr>`).join('') || '<tr><td colspan="4">Nenhum consumo lançado.</td></tr>'}</tbody></table><div class="receipt-total"><span>Total</span><span>${money(current.total)}</span></div>${current.status === 'PAGA' ? `<p>Pagamento: ${esc(current.forma)}<br>Recebido: ${money(current.recebido)} · Troco: ${money(current.troco)}</p>` : '<p class="receipt-footer">Conta em aberto. A conferência não registra pagamento.</p>'}<p class="receipt-footer">Obrigado pela visita!</p>`;
        recibo.showModal();
    };
    filtrarCards();
    renderizarFavoritos();
})();
