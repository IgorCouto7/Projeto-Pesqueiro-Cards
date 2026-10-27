"""Entrada do programa e do executável Windows."""
import argparse
import os
import threading
import time
import webbrowser

import uvicorn


def main():
    parser = argparse.ArgumentParser(description='Rancho da tia nina — caixa local')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    from caixa import app

    config = uvicorn.Config(
        app, host='127.0.0.1', port=args.port, loop='asyncio', http='h11',
        ws='none', lifespan='on',
    )
    server = uvicorn.Server(config)

    def abrir_navegador():
        for _ in range(600):
            if server.started:
                webbrowser.open(f'http://127.0.0.1:{args.port}/cards')
                return
            time.sleep(0.1)

    if not args.no_browser and os.environ.get('PESQUEIRO_NO_BROWSER') != '1':
        threading.Thread(target=abrir_navegador, daemon=True).start()
    print('Rancho da tia nina: mantenha esta janela aberta durante o atendimento.')
    server.run()


if __name__ == '__main__':
    main()
