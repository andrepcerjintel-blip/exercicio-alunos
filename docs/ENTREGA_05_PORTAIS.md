# Entrega 05 — Portais e sequência dos vestígios

## Aluno

Login individual e equipe por código. Telas individualizadas pelas seis fases, com divisão da fase 4 em análise dos provedores e perícia/arrecadação no local. Não há controles de autoaprovação ou emissão de senha. O servidor rejeita essas tentativas com HTTP 403.

Na fase inicial de imagens, o aluno baixa um ZIP com 11 imagens, calcula e envia 12 hashes: cada imagem e o ZIP inteiro. Recebe apenas o resultado da comparação. As referências não são fornecidas pelo estado da API do aluno.

O professor recebe autor, equipe, texto, fase e horário de cada entrega, pedido, hash e ficha de análise. Contas compartilhadas de equipe não podem mais entrar; os registros anteriores sem autor individual são identificados como legados.

## Professor e avaliadores

O instrutor cadastra avaliadores e recebe os textos de cada plataforma/provedor separadamente. Há filtros por equipe e destinatário e telas por fase. Cada pedido tem parecer, situação, avaliador e horário de revisão. Uma versão corrigida precisa ser novamente avaliada.

A resposta simulada deve corresponder ao provedor do pedido aprovado da própria equipe. A última versão enviada é a que vale. Senhas ficam bloqueadas enquanto houver pedidos ou análises pendentes na fase.

Após a avaliação, o professor envia uma senha ao portal da equipe. Ela não é divulgada às outras equipes e é consumida na passagem. Novas entregas e alterações de avaliação invalidam senhas pendentes.

## Fase 4: análise dos identificadores

Cada ficha contém:

- Resposta de origem e identificador exato.
- Constatação e relevância para a investigação.
- Limites, incertezas e conclusões que não são sustentadas.
- Próxima diligência, destinatário e fundamento/autorização.

O professor aprova ou devolve cada ficha. A passagem exige análise aprovada dos retornos recebidos, sem pendências. Essa verificação não substitui o julgamento da qualidade e da completude pelo avaliador.

## Perícia e arrecadação

A21 (polícia no local) e A22 (caderno) foram retiradas da entrega antecipada. O PDF inicial também não é entregue nessa fase, pois trazia as mesmas imagens nas páginas 13 e 14. O kit original e seus arquivos não foram modificados.

Os dois vestígios ficam em `LOCAL-A21-A22.zip`, liberado apenas na tela de perícia da fase 4 após pedido pericial aprovado, recebimento de A16 e autorização expressa do professor. Essa entrega exige três hashes (as duas imagens e o ZIP) e análise dos novos vestígios.

## Resultado

- 23 materiais cadastrados; 30 arquivos originais dos manifestos conferidos.
- 13 testes de integração passaram.
- Percurso das seis fases em Chromium passou, com 12 capturas e 17 verificações registradas em `docs/demonstracao/resultado.json`.
- Compose validado; contêiner não construído.
- A prévia pública foi substituída por telas de avaliação; não oferece controles de autoaprovação.

## Disponibilidade

Os portais foram executados no ambiente de desenvolvimento. O GitHub Pages mostra a prévia visual, não o serviço autenticado. A hospedagem do serviço Python e do banco persistente permanece necessária para receber respostas reais de vários computadores.

O repositório público permite acesso aos materiais fora da aplicação. O controle do portal não torna privados os arquivos publicados no GitHub.
