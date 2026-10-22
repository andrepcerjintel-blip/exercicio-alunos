"""Importa o kit sem executar scripts recebidos e sem alterar bytes dos anexos."""
import hashlib
import json
import zipfile
from pathlib import Path
import app

RESPONSES = [
 ('Discord/01_Resposta_Inicial_ROOK','A08','Discord · resposta inicial ROOK',3),
 ('Discord/02_Resposta_Complementar','A23','Discord · resposta complementar',3),
 ('Discord/03_Proativo_Posterior','A15','Discord · atualização proativa',4),
 ('Google/01_Cadastros_E_Dispositivo','A10-A10B','Google · cadastros e dispositivo',3),
 ('Meta_Instagram/01_Retorno_Contas','A11','Instagram · retorno de contas',3),
 ('NetSul_Fibra/01_Conexoes_Iniciais','A09','NetSul · conexões iniciais',3),
 ('NetSul_Fibra/02_Conexao_Posterior','A24','NetSul · novo acesso',4),
 ('Rede_De_Videos/01_Retorno_Perfis','A26','Rede de vídeos · retorno de perfis',3),
 ('Telegram/01_Protocolo_Limitado','A13','Telegram · protocolo limitado',3),
]
DILIGENCES=[('01_Qualificacoes_Locais','A12','Diligência · qualificações locais',3),('02_Comunicacao_Pericial','A16','Diligência · comunicação pericial',3),('03_Metadados_Atualizados','A25','Diligência · metadados atualizados',4)]

def checksum(path):
 with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def archive(folder,destination,private=False):
 files=sorted(p for p in folder.rglob('*') if p.is_file() and (private or p.name!='LEIA_PROFESSOR_NAO_ENTREGAR.txt'))
 if not files:raise ValueError(f'Pasta sem documentos: {folder}')
 with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as z:
  for p in files:
   info=zipfile.ZipInfo(p.relative_to(folder).as_posix(),date_time=(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
   z.writestr(info,p.read_bytes())
 return files

def integrate():
 app.init();output=app.DATA/'kit';output.mkdir(exist_ok=True)
 verified=0
 for manifest in sorted(app.ROOT.glob('0[1-6]*/SHA256.txt')):
  for line in manifest.read_text().splitlines():
   parts=line.split(maxsplit=1)
   if len(parts)!=2:continue
   expected,name=parts;file=manifest.parent/name.lstrip('*')
   if not file.is_file() or checksum(file)!=expected:raise ValueError(f'Integridade divergente: {file}')
   verified+=1
 catalog=[]
 def add(folder,code,title,phase,kind,condition='',private=False):
  dest=output/(code+'.zip');files=archive(folder,dest,private)
  value=checksum(dest)
  with app.db() as c:
   existing=c.execute('SELECT id FROM materials WHERE code=?',(code,)).fetchone()
   values=(title,phase,str(dest),value,int(kind=='phase'),kind,code,condition,dest.name)
   if existing:c.execute('UPDATE materials SET title=?,phase=?,path=?,sha256=?,released=?,kind=?,code=?,condition=?,filename=? WHERE id=?',(*values,existing['id']))
   else:c.execute('INSERT INTO materials(title,phase,path,sha256,released,kind,code,condition,filename) VALUES(?,?,?,?,?,?,?,?,?)',values)
  catalog.append(dict(code=code,title=title,phase=phase+1,kind=kind,files=len(files),sha256=value))
 plan=json.loads((app.ROOT/'00_PROFESSOR_RESERVADO/Plano_De_Liberacao.json').read_text())
 for i,entry in enumerate(plan):add(app.ROOT/entry['folder'],f'FASE-{i+1:02}',entry['title'],i,'phase',entry['release'])
 reserved=app.ROOT/'00_PROFESSOR_RESERVADO'
 for relative,code,title,phase in RESPONSES:
  folder=reserved/'02_RESPOSTAS_PROVEDORES'/relative
  add(folder,code,title,phase,'response',(folder/'LEIA_PROFESSOR_NAO_ENTREGAR.txt').read_text())
 for relative,code,title,phase in DILIGENCES:
  folder=reserved/'03_RETORNOS_DILIGENCIAS'/relative
  add(folder,code,title,phase,'response',(folder/'LEIA_PROFESSOR_NAO_ENTREGAR.txt').read_text())
 add(reserved/'01_GABARITO_E_VALIDACAO','PROFESSOR','Gabaritos, base canônica e validação',0,'teacher',private=True)
 for name,title in [('Guia_Instrutor_LUA.pdf','Guia do instrutor'),('Plano_De_Liberacao.json','Plano de liberação')]:
  p=reserved/name;code='RESERVADO-'+p.stem
  with app.db() as c:
   if not c.execute('SELECT 1 FROM materials WHERE code=?',(code,)).fetchone():
    c.execute('INSERT INTO materials(title,phase,path,sha256,kind,code,filename) VALUES(?,?,?,?,?,?,?)',(title,0,str(p),checksum(p),'teacher',code,name))
  catalog.append(dict(code=code,title=title,kind='teacher',files=1))
 report=dict(verified_files=verified,materials=len(catalog),catalog=catalog)
 (app.DATA/'integracao.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 return report
if __name__=='__main__':
 report=integrate();print(json.dumps({k:v for k,v in report.items() if k!='catalog'},ensure_ascii=False))
