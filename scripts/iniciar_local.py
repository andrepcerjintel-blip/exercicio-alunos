"""Inicia a aplicação local e abre o navegador do usuário."""
import os
import sys
import threading
import webbrowser
from http.server import ThreadingHTTPServer
from pathlib import Path

def main():
 if sys.version_info<(3,12):
  raise SystemExit('Instale Python 3.12 ou superior para executar a Operação LUA.')
 root=Path(__file__).resolve().parents[1]
 sys.path.insert(0,str(root))
 import app
 import integrar_kit
 print('Operação LUA — inicializando o ambiente local…',flush=True)
 report=integrar_kit.integrate()
 print(f"Kit conferido: {report['verified_files']} arquivos e {report['materials']} materiais integrados.",flush=True)
 port=int(os.environ.get('PORT','8000'))
 try:server=ThreadingHTTPServer(('127.0.0.1',port),app.App)
 except OSError:
  print('A porta está ocupada. Tentando outra porta local disponível.',flush=True)
  server=ThreadingHTTPServer(('127.0.0.1',0),app.App)
 url=f'http://127.0.0.1:{server.server_port}/'
 print('O navegador será aberto. Mantenha esta janela aberta enquanto estiver usando o jogo.',flush=True)
 print('O acesso do instrutor está no arquivo:',app.DATA/'acesso-inicial.txt',flush=True)
 print('Para encerrar, pressione Ctrl+C nesta janela.',flush=True)
 if os.environ.get('LUA_NO_BROWSER')!='1':
  threading.Timer(0.5,lambda:webbrowser.open(url)).start()
 else:print('LUA_READY_PORT='+str(server.server_port),flush=True)
 try:server.serve_forever()
 except KeyboardInterrupt:print('\nJogo encerrado.')
 finally:server.server_close()

if __name__=='__main__':main()
