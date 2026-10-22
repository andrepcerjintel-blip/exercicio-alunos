# Operação LUA

Simulação investigativa em seis fases para uma turma por instância. Cadastro individual, equipes, entregas versionadas e passagem por senha após avaliação do instrutor.

Veja a [Entrega 04](docs/ENTREGA_04_INTEGRACAO.md) e a [demonstração com capturas reais](docs/demonstracao/demonstracao.html).

## Preparar e executar

Python 3.12 ou superior. A aplicação não exige pacotes externos.

```sh
python integrar_kit.py
python app.py
```

O importador valida os 30 arquivos dos manifestos e cadastra 21 itens: seis pacotes de fase, doze conjuntos de retornos e três itens reservados ao instrutor. Pode ser executado novamente sem duplicar os registros. Os arquivos internos mantêm seus bytes; os ZIPs reconstruídos recebem hashes próprios.

O servidor atende internamente em loopback na porta 8000. `PORT` permite alterar a porta e `LUA_DATA` permite definir um diretório privado de dados. A credencial inicial está em `.runtime/acesso-inicial.txt`, com permissão restrita. Não versionar nem divulgar esse arquivo. Banco, credenciais, pacotes e histórico ficam em `.runtime`; preservar em backups seguros.

## Como usar

1. Cada aluno cadastra usuário, senha pessoal, nome e código da equipe. O primeiro integrante define o código; os demais precisam dele para entrar. Nome do aluno e nome da equipe devem ser diferentes. Senhas e códigos têm pelo menos dez caracteres.
2. A equipe visualiza a missão e os materiais da fase, trabalha e envia sua entrega.
3. Na fase 2, os 18 hashes do manifesto precisam estar registrados e corresponder aos arquivos antes da entrega. O navegador pode calcular a pasta extraída sem enviar os arquivos ao servidor.
4. Nas fases 3 a 5, a equipe registra pedidos com destinatário e fundamentação. O instrutor avalia e libera os retornos para aquela equipe, vinculando o pedido correspondente. A15 e A25 são atualizações sem pedido prévio.
5. O instrutor aprova a última entrega e emite uma senha exclusiva da equipe e fase. A equipe digita a senha para avançar. A sexta senha encerra o exercício.

A emissão de nova senha invalida a anterior. Cinco erros impõem cinco minutos de espera. Alunos não podem acessar gabaritos, materiais futuros ou respostas liberadas apenas para outra equipe pela aplicação. Quem tiver acesso ao GitHub terá acesso aos materiais reservados ali armazenados.

O campo de pedido deve registrar objeto, identificadores, intervalo temporal e fuso, finalidade, fundamento e autorização necessária. O instrutor avalia o conteúdo; o sistema não substitui análise jurídica.

## Material adicional

```sh
python importar_material.py /caminho/arquivo.zip --fase 2 --titulo 'Material adicional'
```

Esse importador cadastra como reservado. Para o kit padronizado, use `integrar_kit.py`, que distingue materiais de fase, retornos individuais e arquivos exclusivos do professor.

## Testes

```sh
python -m unittest discover -s tests -v
node --check static/app.js
```

Para reproduzir o percurso visual em um banco temporário, são necessários Playwright para Python e `/usr/bin/chromium` (já disponíveis no ambiente atual):

```sh
python scripts/demonstrar.py
```

O script abre a aplicação real, cadastra equipes, percorre as fases, verifica bloqueios e gera capturas e relatório em `docs/demonstracao`. As entregas demonstrativas não são gabaritos pedagógicos.

## Limites

Uma turma por instância. Acessos individuais e acesso legado de equipe. Entregas textuais; ainda não há anexos de entrega, rubricas por item, recuperação/troca de senha ou módulo da operação final. A correção jurídica dos pedidos e dependências específicas dos retornos exige avaliação do instrutor. A conferência do hash não comprova autoria nem origem. Uso atual restrito à validação interna; publicação externa exige preparação específica de hospedagem e autenticação.
