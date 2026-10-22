# Operação LUA

Seis fases, portais separados e avaliação nominal pelo professor. Aplicação Python 3.12+ sem dependências externas de execução.

## Executar os portais

```sh
python servidor.py
```

A inicialização valida o kit, cadastra 23 materiais e preserva os dados existentes. O aluno usa `/aluno`; o professor e os avaliadores usam `/professor`. Cada fase tem sua própria rota e mostra apenas os materiais, formulários e entregas correspondentes. A fase 4 separa `/aluno/fase/4/provedores` de `/aluno/fase/4/pericia`.

O acesso inicial do instrutor está em `.runtime/acesso-inicial.txt`, com permissão restrita. Nunca publicar esse arquivo. Cada aluno cria uma credencial pessoal e entra na equipe por código. O acesso compartilhado pelo nome da equipe foi desativado: novas entregas, pedidos, hashes e análises registram o autor nominal. O instrutor pode cadastrar contas de avaliadores no seu portal.

A porta interna padrão é 8000, em loopback. `HOST`, `PORT` e `LUA_DATA` permitem configurar o serviço. Banco, senhas de passagem e materiais privados ficam em `.runtime` ou no diretório indicado por `LUA_DATA`.

## Entregas e avaliações

O aluno envia respostas e acompanha as devolutivas. Não pode aprovar sua entrega, avaliar pedidos/análises nem emitir senhas, inclusive por chamadas diretas à API.

O professor vê nome do aluno, equipe, fase, horário e texto. Após aprovar a última entrega e as pendências da fase, envia a senha pelo próprio portal. A senha chega somente à equipe correspondente. Uma nova entrega, nova versão de pedido ou revisão de avaliação invalida senhas ainda não utilizadas. Cinco erros bloqueiam tentativas por cinco minutos.

Nas fases de provedores, cada pedido contém destinatário e texto próprio. O avaliador aprova ou pede correção individualmente. Um retorno só pode ser liberado com a última versão aprovada de um pedido da mesma equipe e da plataforma/provedor correto. A15 e A25 são atualizações sem pedido prévio; A24 exige pedido da atualização ao provedor de conexão.

Na fase 4, cada identificador relevante ganha uma ficha: resposta de origem, tipo, valor, constatação/relevância, limites, próxima providência, destinatário e fundamento/autorização. O professor avalia cada ficha. A cobertura de respostas e a ausência de análises pendentes são verificadas antes da passagem. A qualidade e a completude dos identificadores dependem da avaliação humana; não há julgamento jurídico automático.

## Imagens e hashes

- Fase 2: `IMAGENS-FASE-02.zip`, com 11 imagens; envio dos hashes das 11 imagens e do ZIP original (12 referências).
- Perícia na fase 4: `LOCAL-A21-A22.zip`, com polícia no local e caderno; envio dos hashes das duas imagens e do ZIP (3 referências).

A21 e A22 não entram no pacote inicial. O PDF inicial original também foi excluído dessa entrega por conter as duas imagens nas páginas 13 e 14. Os arquivos-fonte do kit foram preservados.

A entrega pericial depende de pedido aprovado, retorno A16 recebido e liberação expressa do professor. Os hashes de referência são calculados no servidor e não enviados ao aluno. Não há manifesto de respostas dentro dos ZIPs de imagens. O aluno calcula com sua ferramenta e cola os valores. O servidor identifica divergências sem revelar o valor esperado. Não recomprimir o ZIP antes de calcular seu hash.

## Hospedagem

O GitHub Pages exibe somente a prévia visual em `index.html`; não recebe respostas de uma turma. Para usar os portais reais é necessário executar o serviço Python, com armazenamento persistente e acesso de rede apropriado.

Há `Dockerfile`, `compose.yaml` e `servidor.py`. A configuração Compose foi validada; a imagem de contêiner não foi construída neste ambiente. O volume `lua_dados` preserva equipes, entregas e credenciais. Não executar múltiplas instâncias independentes sobre bancos diferentes para a mesma turma.

O controle de acesso vale para a aplicação. Como o repositório foi tornado público, seus materiais e gabaritos continuam acessíveis pelo GitHub fora da aplicação. A turma real exige que esses materiais sejam mantidos em fonte privada.

## Validação e prévia

```sh
python -m unittest discover -s tests -v
node --check static/app.js
python scripts/demonstrar.py
python scripts/gerar_demo_navegador.py
python scripts/testar_demo_navegador.py
```

Treze testes de integração e um percurso real no Chromium verificam permissões, autoria, senhas, hashes, avaliação por provedor, análise por identificador e liberação tardia dos vestígios locais. Os scripts de demonstração requerem Playwright e Chromium, já presentes nesta máquina, e usam banco temporário.

[Entrega 05](docs/ENTREGA_05_PORTAIS.md) · [Capturas do teste](docs/demonstracao/demonstracao.html).

## Limites

Uma turma por instância. Entregas textuais; ainda não há anexos enviados pelos alunos, recuperação de senha ou módulo de operação final. O hash não comprova por si só origem ou autoria. A publicação do serviço dos portais ainda depende de hospedagem; a prévia não deve ser usada como portal de uma turma.
