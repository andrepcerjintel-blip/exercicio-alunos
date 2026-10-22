import hashlib
import io
import zipfile
from support import PortalCase,integrar_kit,app

class MaterialTests(PortalCase):
 def test_catalog_zip_and_hidden_references(self):
  self.assertEqual(self.report['verified_files'],30);self.assertEqual(self.report['materials'],23)
  count=len(self.state(self.teacher)['materials']);integrar_kit.integrate();self.assertEqual(len(self.state(self.teacher)['materials']),count)
  references=self.state(self.teacher)['hash_references'];self.assertEqual(len(references),15)
  m=self.material('IMAGENS-FASE-02');status,raw=self.get(self.teacher,'/material/'+str(m['id']));self.assertEqual(status,200)
  zipref=next(r for r in references if r['name']=='IMAGENS-FASE-02.zip');self.assertEqual(hashlib.sha256(raw).hexdigest(),zipref['sha256'])
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   self.assertEqual(len(z.namelist()),11)
   self.assertTrue(all(n.endswith('.png') for n in z.namelist()))
   for n in z.namelist():self.assertEqual(z.read(n),(app.ROOT/'02_PROVAS_INICIAIS_ALUNOS'/n).read_bytes())
  self.advance(self.a)
  student=self.state(self.a);self.assertEqual(student['hash_references'],[]);self.assertEqual(len(student['inventory']),12)
  self.assertNotIn(zipref['sha256'],str(student))
  self.assertEqual(self.get(self.a,'/asset/'+str(m['id'])+'/anexos/A02.png')[0],403)
 def test_guessed_files_future_and_teacher_are_denied(self):
  for code in ['IMAGENS-FASE-02','A08','PROFESSOR']:
   m=self.material(code);self.assertEqual(self.get(self.a,'/material/'+str(m['id']))[0],403)
  self.advance(self.a)
  images=self.material('IMAGENS-FASE-02');self.assertEqual(self.get(self.a,'/material/'+str(images['id']))[0],200)
  self.assertEqual(self.get(self.b,'/material/'+str(images['id']))[0],403)
 def test_wrong_image_or_zip_hash_blocks_phase(self):
  self.advance(self.a)
  self.assertFalse(self.post(self.a,'hash',{'name':'anexos/A02.png','sha256':'0'*64})['matched'])
  self.post(self.a,'submit',{'body':'Tentativa sem todos os hashes'},400)
  self.hashes(self.a)
  zipref=next(r for r in self.state(self.teacher)['hash_references'] if r['name']=='IMAGENS-FASE-02.zip')
  self.post(self.a2,'hash',{'name':zipref['name'],'sha256':'f'*64})
  self.post(self.a,'submit',{'body':'Tentativa com ZIP divergente'},400)
  self.post(self.a,'hash',{'name':zipref['name'],'sha256':zipref['sha256'].upper()})
  self.assertEqual(self.state(self.a)['hash_pending'],[])
  self.post(self.a,'submit',{'body':'Todos os hashes conferidos e recebimento registrado.'})
  records=self.state(self.teacher)['hashes'];self.assertTrue(any(r['student_name']=='Bruno' and r['team_name']=='Alfa' for r in records))
  self.assertEqual(self.state(self.b)['hashes'],[])
 def test_response_requires_approved_latest_matching_request(self):
  for _ in range(3):self.advance(self.a)
  discord=self.state(self.a)['requests'][-1]
  google=self.request(self.a,'Google','Texto específico do pedido ao Google para avaliação.')
  data={'id':self.material('A10-A10B')['id'],'team_id':self.team(self.a)['id'],'request_id':google['id']}
  self.post(self.teacher,'release',data,400)
  self.approve_request(google)
  self.post(self.teacher,'release',{**data,'request_id':discord['id']},400)
  self.post(self.teacher,'release',data)
  self.assertEqual(self.get(self.a,'/material/'+str(data['id']))[0],200)
  self.assertEqual(self.get(self.b,'/material/'+str(data['id']))[0],403)
  revised=self.request(self.a,'Google','Nova versão nominal do pedido.')
  self.post(self.teacher,'release',data,400)
  self.approve_request(revised);self.post(self.teacher,'release',{**data,'request_id':revised['id']})

 def test_crime_scene_images_and_embedded_pdf_are_not_delivered_early(self):
  self.advance(self.a)
  inventory=self.state(self.a)['inventory']
  self.assertNotIn('anexos/A21.png',inventory);self.assertNotIn('anexos/A22.png',inventory)
  late_ref=next(r for r in self.state(self.teacher)['hash_references'] if r['name']=='anexos/A21.png')
  self.post(self.a,'hash',{'name':late_ref['name'],'sha256':late_ref['sha256']},400)
  for code in ['FASE-02','IMAGENS-FASE-02']:
   status,raw=self.get(self.a,'/material/'+str(self.material(code)['id']));self.assertEqual(status,200)
   with zipfile.ZipFile(io.BytesIO(raw)) as z:
    self.assertFalse(any('A21' in n or 'A22' in n or 'Caderno_Desta_Entrega.pdf' in n for n in z.namelist()))
  self.assertEqual(self.get(self.a,'/material/'+str(self.material('LOCAL-A21-A22')['id']))[0],403)

 def test_crime_scene_package_requires_pericial_request_and_report(self):
  for _ in range(3):self.advance(self.a)
  request=self.request(self.a,'Perícia');self.approve_request(request)
  late=self.material('LOCAL-A21-A22');data={'id':late['id'],'team_id':self.team(self.a)['id'],'request_id':request['id']}
  self.post(self.teacher,'release',data,400)
  self.release(self.a,'A16',request);self.post(self.teacher,'release',data)
  student=self.state(self.a);self.assertIn('anexos/A21.png',student['inventory']);self.assertIn('anexos/A22.png',student['inventory'])
  status,raw=self.get(self.a,'/material/'+str(late['id']));self.assertEqual(status,200)
  with zipfile.ZipFile(io.BytesIO(raw)) as z:self.assertEqual(set(z.namelist()),{'anexos/A21.png','anexos/A22.png'})
  self.assertEqual(self.get(self.b,'/material/'+str(late['id']))[0],403)
