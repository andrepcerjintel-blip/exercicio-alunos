from support import PortalCase

class WorkflowTests(PortalCase):
 def test_student_cannot_approve_issue_codes_or_create_evaluator(self):
  for path,data in [('review',{'id':1,'status':'approved'}),('gate',{'team_id':self.team(self.a)['id']}),('request-review',{'id':1,'status':'approved'}),('analysis-review',{'id':1,'status':'approved'}),('evaluator',{'name':'intruso','password':'senha-segura-123'}),('release',{'id':1})]:
   self.post(self.a,path,data,403)
  other=self.client();self.post(other,'login',{'name':'Alfa','password':'codigo-equipe-123'},401)
  self.assertEqual(self.get(self.a,'/aluno')[0],200);self.assertEqual(self.get(self.teacher,'/professor')[0],200)
 def test_nominal_delivery_and_password_inbox_are_team_scoped(self):
  self.post(self.a,'submit',{'body':'Abordagem proposta pela Ana.'})
  self.post(self.a2,'submit',{'body':'Abordagem revista por Bruno.'})
  teacher=self.state(self.teacher);ds=teacher['deliveries']
  self.assertEqual([d['student_name'] for d in ds],['Ana','Bruno']);self.assertEqual([d['name'] for d in ds],['Alfa','Alfa'])
  self.post(self.teacher,'review',{'id':ds[0]['id'],'status':'approved'},400)
  self.post(self.teacher,'review',{'id':ds[1]['id'],'status':'approved'})
  code=self.post(self.teacher,'gate',{'team_id':self.team(self.a)['id']})['code']
  self.assertEqual(self.state(self.a)['messages'][0]['code'],code);self.assertEqual(self.state(self.a2)['messages'][0]['code'],code)
  self.assertEqual(self.state(self.b)['messages'],[])
  self.post(self.a,'unlock',{'code':'incorreta'},400);self.post(self.a,'unlock',{'code':code})
  self.assertEqual(self.state(self.a2)['phase'],1);self.assertEqual(self.state(self.b)['phase'],0);self.assertEqual(self.state(self.a)['messages'],[])
 def test_new_delivery_invalidates_previously_sent_password(self):
  self.post(self.a,'submit',{'body':'Primeira versão'})
  d=self.state(self.a)['deliveries'][-1];self.post(self.teacher,'review',{'id':d['id'],'status':'approved'})
  code=self.post(self.teacher,'gate',{'team_id':self.team(self.a)['id']})['code']
  self.post(self.a2,'submit',{'body':'Nova versão'})
  self.assertEqual(self.state(self.a)['messages'],[]);self.post(self.a,'unlock',{'code':code},400)
 def test_platform_texts_are_reviewed_individually_by_named_evaluator(self):
  self.advance(self.a);self.advance(self.a)
  discord=self.request(self.a,'Discord','Texto de Ana ao Discord.')
  google=self.request(self.a2,'Google','Texto de Bruno ao Google.')
  self.assertEqual(self.state(self.teacher)['requests'][-1]['student_name'],'Bruno')
  self.post(self.teacher,'evaluator',{'name':'Avaliador Um','password':'avaliador-senha-123'})
  evaluator=self.client();self.post(evaluator,'login',{'name':'Avaliador Um','password':'avaliador-senha-123'})
  self.post(evaluator,'evaluator',{'name':'Outro','password':'senha-outro-123'},403)
  self.post(evaluator,'request-review',{'id':discord['id'],'status':'approved','feedback':'Discord aprovado.'})
  self.post(evaluator,'request-review',{'id':google['id'],'status':'correction','feedback':'Delimite o período e justifique o escopo.'})
  self.post(self.a,'submit',{'body':'Plano com dois pedidos.'})
  d=self.state(self.a)['deliveries'][-1];self.post(self.teacher,'review',{'id':d['id'],'status':'approved'},400)
  requests=self.state(self.a)['requests'];self.assertEqual(requests[-1]['reviewer_name'],'Avaliador Um');self.assertEqual(requests[-1]['feedback'],'Delimite o período e justifique o escopo.')
  self.assertEqual(self.state(self.b)['requests'],[])
 def test_identifier_analysis_requires_source_limits_action_and_approval(self):
  for _ in range(3):self.advance(self.a)
  request=self.state(self.a)['requests'][-1];self.release(self.a,'A08',request)
  item=self.analysis(self.a)
  self.assertEqual(item['student_name'],'Ana');self.assertEqual(item['team_name'],'Alfa');self.assertEqual(item['response_code'],'A08')
  self.post(self.a,'submit',{'body':'Consolidação dos retornos.'})
  d=self.state(self.a)['deliveries'][-1];self.post(self.teacher,'review',{'id':d['id'],'status':'approved'},400)
  self.post(self.teacher,'analysis-review',{'id':item['id'],'status':'correction','feedback':'Explique melhor a diligência proposta.'})
  self.assertEqual(self.state(self.a)['analyses'][0]['status'],'correction')
  revised=self.analysis(self.a)
  self.post(self.teacher,'analysis-review',{'id':item['id'],'status':'approved'},400)
  self.post(self.teacher,'analysis-review',{'id':revised['id'],'status':'approved'})
  self.pericia(self.a)
  self.post(self.teacher,'review',{'id':d['id'],'status':'approved'})
  code=self.post(self.teacher,'gate',{'team_id':self.team(self.a)['id']})['code'];self.post(self.a,'unlock',{'code':code})
  self.assertEqual(self.state(self.a)['phase'],4)
 def test_six_phases_complete_without_advancing_other_teams(self):
  for phase in range(6):
   self.assertEqual(self.state(self.a)['phase'],phase);self.advance(self.a)
  self.assertTrue(self.state(self.a)['completed']);self.assertEqual(self.state(self.a)['phase'],5)
  self.assertEqual(self.state(self.b)['phase'],0);self.assertEqual(self.state(self.b)['deliveries'],[])
  self.post(self.a,'submit',{'body':'Tentativa após encerramento'},400)

 def test_correction_can_change_identifier_without_leaving_stale_pending_item(self):
  for _ in range(3):self.advance(self.a)
  request=self.state(self.a)['requests'][-1];self.release(self.a,'A08',request)
  original=self.analysis(self.a,value='identificador-digitado-incorretamente')
  self.post(self.teacher,'analysis-review',{'id':original['id'],'status':'correction','feedback':'Corrija o identificador e preserve a origem.'})
  data={k:original[k] for k in ['response_id','identifier_type','identifier_value','findings','limits','next_step','next_recipient','legal_basis']}
  data.update(revision_of=original['id'],identifier_value='identificador-corrigido')
  self.post(self.a2,'analysis',data)
  revised=self.state(self.a)['analyses'][-1]
  self.assertEqual(revised['student_name'],'Bruno')
  self.assertEqual(self.state(self.a)['analyses'][0]['superseded_by'],revised['id'])
  self.post(self.teacher,'analysis-review',{'id':original['id'],'status':'approved'},400)
  self.post(self.teacher,'analysis-review',{'id':revised['id'],'status':'approved'})
  self.pericia(self.a)
  self.post(self.a,'submit',{'body':'Fichas corrigidas e diligências avaliadas.'})
  d=self.state(self.a)['deliveries'][-1];self.post(self.teacher,'review',{'id':d['id'],'status':'approved'})
