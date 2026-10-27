"""Testa o programa empacotado em pasta isolada, sem abrir navegador."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import uuid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('executable', type=Path)
    args = parser.parse_args()
    executable = args.executable.resolve(strict=True)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    base = f'http://127.0.0.1:{port}'

    def request(path, body=None, token=None):
        data = None if body is None else json.dumps(body).encode()
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['X-Caixa-Token'] = token
        req = urllib.request.Request(base + path, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            raw = response.read()
            if 'application/json' in response.headers.get('Content-Type', ''):
                return json.loads(raw)
            return raw.decode('utf-8')

    with tempfile.TemporaryDirectory(prefix='rancho-exe-') as folder:
        temp = Path(folder)
        env = os.environ.copy()
        env['PESQUEIRO_DB'] = str(temp / 'dados' / 'caixa.sqlite3')
        env['PESQUEIRO_NO_BROWSER'] = '1'
        order_id = None
        for rodada in range(2):
            log_path = temp / f'execucao-{rodada}.log'
            with log_path.open('wb') as log:
                process = subprocess.Popen(
                    [str(executable), '--port', str(port), '--no-browser'],
                    cwd=temp, env=env, stdout=log, stderr=subprocess.STDOUT,
                )
                try:
                    deadline = time.monotonic() + 90
                    while True:
                        if process.poll() is not None:
                            raise RuntimeError('O executável encerrou antes de abrir o caixa.')
                        try:
                            token = request('/api/sessao')['token']
                            break
                        except (urllib.error.URLError, TimeoutError, ConnectionError):
                            if time.monotonic() >= deadline:
                                raise RuntimeError('O executável não abriu o caixa em 90 segundos.')
                            time.sleep(0.5)
                    assert 'Comandas em atendimento' in request('/cards')
                    assert 'PesqueiroUI' in request('/melhorias.js')
                    assert 'Abrir comanda' in request('/classico')
                    if rodada == 0:
                        product = request('/api/produtos', {
                            'nome': 'Produto de teste', 'preco': '8.00',
                            'controla': False, 'minimo': 0,
                        }, token)
                        order = request('/api/comandas', {'nome': 'Teste do executável'}, token)
                        order_id = order['id']
                        result = request(f'/api/comandas/{order_id}/itens', {
                            'produto': product['id'], 'quantidade': 2, 'chave': str(uuid.uuid4()),
                        }, token)
                        assert result['total'] == 1600
                    else:
                        result = request(f'/api/comandas/{order_id}')
                        assert result['total'] == 1600
                        assert len(result['itens']) == 1
                        assert result['nome'] == 'Teste do executável'
                except Exception:
                    print(log_path.read_text(encoding='utf-8', errors='replace'))
                    raise
                finally:
                    # No Windows, encerra também o processo-filho do bootloader onefile.
                    if os.name == 'nt':
                        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                                       capture_output=True, check=False)
                    else:
                        process.terminate()
                    try:
                        process.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=10)
        assert (temp / 'dados' / 'caixa.sqlite3').is_file()
    print('Executável aprovado: telas, API, consumo e persistência após reiniciar.')


if __name__ == '__main__':
    main()
