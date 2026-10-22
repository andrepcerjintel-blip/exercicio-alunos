"""Inicialização do serviço dos portais, com dados persistentes fora da área estática."""
import os
from http.server import ThreadingHTTPServer
import app
import integrar_kit

if __name__=='__main__':
 report=integrar_kit.integrate()
 print(f"Kit preparado: {report['materials']} itens. Portais do aluno e do professor disponíveis.",flush=True)
 server=ThreadingHTTPServer((os.environ.get('HOST','127.0.0.1'),int(os.environ.get('PORT','8000'))),app.App)
 try:server.serve_forever()
 except KeyboardInterrupt:pass
 finally:server.server_close()
