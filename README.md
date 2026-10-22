# Operação LUA

Primeira versão funcional para uma turma por instância, com seis fases com progressão por equipe e cadastro individual dos alunos. Python 3.12 ou superior; sem dependências externas.

## Executar

Na raiz do projeto:

```sh
python app.py
```

O processo atende internamente na porta 8000, interface de loopback. O acesso inicial é criado em `.runtime/acesso-inicial.txt`, com permissão restrita. Não versionar nem divulgar esse arquivo. Cada aluno cadastra seu nome de acesso, senha pessoal e nome da equipe. O primeiro integrante define o código da equipe; os demais precisam informar o mesmo código para entrar. Senhas e códigos têm no mínimo dez caracteres. O nome de acesso do aluno deve ser diferente do nome da equipe. O instrutor também pode criar equipes.

Cada grupo envia respostas textuais versionadas. O instrutor aprova ou devolve para correção. Após aprovar a última entrega da fase atual, o instrutor emite a senha exclusiva para equipe e fase. A equipe informa essa senha para avançar. A senha não dispensa a aprovação. Entregas antigas não podem liberar fases. Na fase final, a senha confirma a conclusão, sem criar uma sétima fase. Revisão jurídica e pedagógica é responsabilidade do instrutor.

## Materiais

```sh
python importar_material.py /caminho/arquivo.zip --fase 2 --titulo 'Provas iniciais'
```

Os arquivos são copiados sem alteração para `.runtime/materiais`, fora da área estática. O instrutor habilita os materiais; cada equipe só pode vê-los e baixá-los após alcançar a fase correspondente. Alunos não podem acessar materiais reservados nem entregas de outros grupos. Não cadastrar gabaritos como materiais de alunos. O pacote inicial já foi importado nesta máquina, reservado para a fase 2.

O cálculo SHA-256 no navegador é apoio e não valida automaticamente cadeia de custódia nem substitui a entrega dos registros. A aprovação técnica é manual nesta versão.

## Validação

```sh
python -m unittest discover -s tests -v
node --check static/app.js
```

## Roteiro do jogo

Consulte [Entrega 03](docs/ENTREGA_03_JOGO.md). Senhas são emitidas no painel do instrutor e nunca incluídas na documentação.

## Limites desta versão

Uma turma por instância e acessos individuais vinculados à equipe, com acesso legado de equipe mantido. Entregas são textuais; ainda não há anexos de entregas, rubricas por item, recuperação/troca de senha, exportação ou fluxo específico da operação final. Os outros materiais do caso ainda precisam ser cadastrados. Não há revisão automática de legislação. Uso atual restrito à validação interna: publicação externa requer HTTPS, gestão de acessos, limitação de tentativas e revisão de segurança. SQLite, materiais, credenciais e histórico ficam em `.runtime`; preservar esse diretório em backups seguros.
