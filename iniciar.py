"""Executa exclusivamente no computador do caixa e abre o navegador."""
import threading
import webbrowser
import uvicorn

if __name__ == '__main__':
    threading.Timer(2, lambda: webbrowser.open('http://127.0.0.1:8000')).start()
    uvicorn.run('caixa:app', host='127.0.0.1', port=8000)
