"""Garante que a adaptação visual mantém as demais telas e ações do caixa."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_estoque_e_caixa_mantem_html_original():
    novo = (ROOT / 'caixa.html').read_text(encoding='utf-8')
    original = (ROOT / 'caixa-classico.html').read_text(encoding='utf-8')
    for secao in ('estoque', 'caixa'):
        pattern = rf'<section id="{secao}"[\s\S]*?</section>'
        assert re.search(pattern, novo).group() == re.search(pattern, original).group()


def test_logica_das_operacoes_permanece_original():
    novo = (ROOT / 'caixa.html').read_text(encoding='utf-8')
    original = (ROOT / 'caixa-classico.html').read_text(encoding='utf-8')

    def operacoes(html):
        script = html.split('<script>')[1].split('</script>')[0]
        script = re.sub(r'/\* CARDS_DIALOG \*/[\s\S]*?/\* /CARDS_DIALOG \*/\n?', '', script)
        # A única função alterada é a que desenha a lista de comandas.
        return re.sub(r'async function refreshOrders\(\)[\s\S]*?(?=async function selectOrder)', '', script)

    assert operacoes(novo) == operacoes(original)


def test_cards_centrais_abrem_consumo_com_preco_do_catalogo():
    html = (ROOT / 'caixa.html').read_text(encoding='utf-8')
    atendimento = re.search(r'<section id="comandas"[\s\S]*?</section>', html).group()
    assert '<aside>' not in atendimento
    assert 'id="orders"' in atendimento
    assert 'id="openNewOrder"' in atendimento
    modal = re.search(r'<dialog id="orderDialog"[\s\S]*?</dialog>', html).group()
    assert 'id="addItem"' in modal
    assert 'id="payment"' in modal
    assert 'id="saleProduct"' in modal
    assert 'name="preco"' not in modal
    assert 'id="backToCards"' in modal
