"""Gera distribuição portátil sem dados, senhas ou histórico do ambiente de desenvolvimento."""
import hashlib
import json
import shutil
import tempfile
import zipapp
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT.parent/'entregas'
OUTPUT.mkdir(exist_ok=True)

BOOTSTRAP=r'''
import hashlib
import json
import os
import runpy
import sys
import zipfile
from pathlib import Path
if sys.version_info<(3,12):
 raise SystemExit('Python 3.12 ou superior é necessário. Instale-o e abra novamente o arquivo.')
archive=Path(sys.argv[0]).resolve()
with zipfile.ZipFile(archive) as z:
 manifest=json.loads(z.read('manifest.json'))
 base=Path(os.environ.get('LUA_APP_ROOT',Path.home()/'OperacaoLUA'))/manifest['version']
 base.mkdir(parents=True,exist_ok=True)
 for name,expected in manifest['files'].items():
  relative=Path(name)
  if relative.is_absolute() or '..' in relative.parts:raise SystemExit('Caminho inválido no pacote.')
  dest=base/relative
  payload=z.read('bundle/'+name)
  if hashlib.sha256(payload).hexdigest()!=expected:raise SystemExit('Falha de integridade no pacote: '+name)
  if dest.exists():
   if hashlib.sha256(dest.read_bytes()).hexdigest()!=expected:
    raise SystemExit('Arquivo local foi modificado. Preserve seu trabalho e use outra pasta LUA_APP_ROOT: '+str(dest))
  else:
   dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(payload)
 os.environ.setdefault('LUA_DATA',str(base/'.runtime'))
 sys.path.insert(0,str(base))
 runpy.run_path(str(base/'scripts/iniciar_local.py'),run_name='__main__')
'''

GUIDE='''OPERAÇÃO LUA — PACOTE EXECUTÁVEL LOCAL

Requisito: Python 3.12 ou superior instalado (Windows, macOS ou Linux).
Este arquivo é uma aplicação Python portátil, não um .exe nativo do Windows.

FORMA MAIS SIMPLES
Execute o arquivo Operacao_LUA.pyz com Python. Ele verifica o conteúdo,
prepara uma pasta local, integra o kit e abre o jogo no navegador.
No Windows, use: py -3 Operacao_LUA.pyz
No macOS/Linux, use: python3 Operacao_LUA.pyz

Os arquivos ficam em sua pasta pessoal, dentro de OperacaoLUA/versão-do-pacote.
O acesso inicial do instrutor é criado em .runtime/acesso-inicial.txt nessa pasta.
O terminal informa a localização exata. Não compartilhe essa credencial.
Mantenha o terminal aberto para usar o jogo; Ctrl+C encerra o servidor.

ALTERNATIVA COM PASTA EXTRAÍDA
Extraia o ZIP inteiro. No Windows, abra INICIAR_WINDOWS.cmd.
No macOS/Linux, execute bash INICIAR_MAC_LINUX.sh.

O pacote destina-se ao instrutor: contém os materiais completos e o gabarito.
Não distribuir o pacote completo aos alunos. Pela aplicação, alunos só veem
os materiais autorizados para sua equipe e fase.

COMO TESTAR
1. Entre como instrutor com a credencial local criada na primeira execução.
2. Em outro perfil/janela privada do navegador, cadastre um aluno e equipe.
3. A equipe recebe a denúncia, escreve a abordagem e envia a entrega.
4. O instrutor aprova e emite a senha. A equipe informa a senha e avança.
5. Na fase 2, baixe o pacote, extraia-o e registre a pasta de provas para
   calcular e conferir os 18 hashes antes de enviar a entrega.
6. Continue até o relatório. Cada passagem exige avaliação e senha.

A validação jurídica é realizada pelo instrutor. O pacote funciona localmente
para avaliação; não publica o jogo na internet. Os dados da equipe permanecem
na pasta .runtime; preserve-a se quiser manter o progresso.
'''


def build():
 with tempfile.TemporaryDirectory() as tmp:
  stage=Path(tmp);bundle=stage/'bundle';bundle.mkdir()
  names=['app.py','integrar_kit.py','importar_material.py','roteiro.json','README.md']
  names += [p.relative_to(ROOT).as_posix() for folder in ['static','00_PROFESSOR_RESERVADO','01_DENUNCIA_WHATSAPP','02_PROVAS_INICIAIS_ALUNOS','03_PEDIDOS_E_DILIGENCIAS','04_ANALISE_DOS_RETORNOS','05_ATUALIZACAO_POSTERIOR','06_RELATORIO_FINAL'] for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
  names+=['scripts/iniciar_local.py']
  for name in names:
   dest=bundle/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
  files={name:hashlib.sha256((bundle/name).read_bytes()).hexdigest() for name in sorted(names)}
  version=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()[:12]
  (stage/'manifest.json').write_text(json.dumps({'version':version,'files':files},sort_keys=True))
  (stage/'__main__.py').write_text(BOOTSTRAP)
  pyz=OUTPUT/'Operacao_LUA.pyz'
  zipapp.create_archive(stage,target=pyz,interpreter='/usr/bin/env python3',compressed=True)
  (OUTPUT/'LEIA_PRIMEIRO.txt').write_text(GUIDE)
  windows='@echo off\r\ncd /d "%~dp0"\r\nwhere py >nul 2>nul\r\nif %errorlevel% equ 0 (py -3 scripts\\iniciar_local.py) else (python scripts\\iniciar_local.py)\r\npause\r\n'
  unix='#!/usr/bin/env bash\nset -eu\ncd "$(dirname "$0")"\npython3 scripts/iniciar_local.py\n'
  portable=OUTPUT/'Operacao_LUA_Portatil.zip'
  with zipfile.ZipFile(portable,'w',zipfile.ZIP_DEFLATED) as z:
   for name in names:z.write(bundle/name,'Operacao_LUA/'+name)
   z.writestr('Operacao_LUA/INICIAR_WINDOWS.cmd',windows)
   z.writestr('Operacao_LUA/INICIAR_MAC_LINUX.sh',unix)
   z.writestr('Operacao_LUA/LEIA_PRIMEIRO.txt',GUIDE)
  for file in [pyz,portable]:
   with file.open('rb') as stream:value=hashlib.file_digest(stream,'sha256').hexdigest()
   (OUTPUT/(file.name+'.sha256')).write_text(value+'  '+file.name+'\n')
  print(json.dumps({'version':version,'files':len(files),'artifacts':[{'name':p.name,'bytes':p.stat().st_size} for p in [pyz,portable]]},ensure_ascii=False))
if __name__=='__main__':build()
