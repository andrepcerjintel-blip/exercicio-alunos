# Entrega 03 — Jogo Operação LUA

## Funcionamento implementado

Cada aluno tem acesso individual e integra uma equipe. A equipe envia a entrega, o instrutor avalia e aprova, emite uma senha exclusiva para aquela equipe e etapa, e um integrante informa a senha para avançar. Todos os integrantes passam a ver a nova fase. A senha sozinha não substitui a aprovação.

A emissão de nova senha invalida a anterior. Cinco erros bloqueiam as tentativas por cinco minutos. Senhas são verificadas no servidor e não aparecem no roteiro nem no estado enviado aos alunos. A senha da fase 6 confirma o encerramento.

## As seis fases

### 1. O plantão recebeu uma denúncia

A equipe assume o plantão e recebe uma mensagem por WhatsApp. Neste momento, somente a denúncia está disponível; a narrativa ainda precisa de confirmação.

**O que o grupo faz:**

- Redigir a resposta ao denunciante, esclarecendo risco atual, momento dos fatos, origem das informações e pessoas envolvidas.
- Solicitar links, identificadores e arquivos já existentes, preferindo originais quando disponíveis e registrando a proveniência.
- Descrever as providências imediatas e os acionamentos justificados, sem exigir nova exposição da fonte.

**Entrega:** Abordagem escrita, avaliação de risco e registro das providências iniciais.

**Passagem:** Após avaliação e aprovação, o instrutor fornece a senha para abrir o recebimento das provas.

### 2. A fonte entregou os arquivos

A equipe recebe o pacote inicial completo: capturas, seis imagens selecionadas, caderno e vídeo. Não há respostas de provedores nesta etapa.

**O que o grupo faz:**

- Inventariar os arquivos recebidos e registrar origem, responsável, data, horário e fuso.
- Calcular SHA-256 dos arquivos, registrar ferramenta e resultados e conferir o manifesto recebido.
- Documentar armazenamento, preservação dos originais e movimentações dos vestígios.
- Realizar a primeira leitura do acervo separando observações, alegações e hipóteses.

**Entrega:** Inventário, registros de recebimento e cadeia de custódia, hashes e análise inicial.

**Passagem:** A aprovação dos registros permite ao instrutor emitir a senha da triagem e dos pedidos.

### 3. Transformar pistas em diligências

A equipe organiza os identificadores disponíveis e recebe os materiais de pedidos e diligências quando habilitados pelo instrutor.

**O que o grupo faz:**

- Relacionar cada identificador à sua fonte, sem preencher dados ainda desconhecidos.
- Justificar competência territorial, prioridades e finalidade das diligências.
- Preparar pedidos por destinatário com objeto, identificadores, intervalo temporal e fuso, fundamento e autorização necessária.
- Distinguir preservação de dados, obtenção de registros, dados cadastrais e conteúdo conforme a medida escolhida.

**Entrega:** Quadro de identificadores, plano de diligências e pedidos fundamentados.

**Passagem:** Após análise técnica e jurídica dos pedidos, a senha abre a rodada de respostas.

### 4. As respostas começam a chegar

Os retornos são entregues pelo instrutor conforme os pedidos avaliados. Novas respostas exigem novos pedidos quando houver dependência.

**O que o grupo faz:**

- Analisar os retornos recebidos e registrar o que cada fonte demonstra e o que permanece desconhecido.
- Preparar pedidos complementares a partir de identificadores efetivamente obtidos.
- Correlacionar registros de aplicação e conexão com IP, porta, protocolo, data, horário e fuso quando pertinentes.
- Solicitar diligências locais e sobre local e objetos quando justificadas.
- Distinguir conta, titular da conexão, pessoa indicada e autoria da conduta.

**Entrega:** Pedidos complementares, análise dos retornos, linha do tempo e cadeias com limites de atribuição.

**Passagem:** O instrutor confere a cobertura das cadeias iniciais e emite a senha da atualização posterior.

### 5. Uma nova informação muda o cenário

O instrutor apresenta a atualização posterior e seus metadados. A equipe deve analisar o novo acesso e decidir quais providências são necessárias.

**O que o grupo faz:**

- Registrar recebimento e integridade dos novos materiais.
- Comparar o novo elemento com as cadeias anteriores, considerando a origem e a independência das fontes.
- Preparar o pedido referente ao novo acesso e analisar o retorno somente após sua liberação.
- Reavaliar risco, hipóteses, confiança e lacunas sem confundir quantidade de contas com quantidade de autores.

**Entrega:** Análise da atualização, novo pedido, análise do retorno e quadro de hipóteses revisado.

**Passagem:** Após aprovação desta rodada, a senha abre a consolidação final.

### 6. Concluir e prestar contas da investigação

A equipe consolida todo o trabalho. O encerramento depende da qualidade e dos limites da fundamentação, sem exigir uma conclusão predeterminada de autoria.

**O que o grupo faz:**

- Entregar relatório, inventário, linha do tempo, organograma, pedidos, respostas e cadeias.
- Separar fatos observados, alegações, inferências, lacunas e graus de confiança.
- Individualizar condutas apenas quando houver suporte e distinguir as medidas cabíveis conforme idade e situação.
- Justificar diligências ou medidas propostas e apresentar os registros de preservação e proteção das pessoas sob risco.

**Entrega:** Dossiê final completo e apresentação para avaliação e debriefing.

**Passagem:** Após a avaliação final, a senha de encerramento conclui o exercício. Não abre uma sétima fase.

## Regras reservadas de condução

- Fase 1: somente denúncia; não antecipar arquivos do pacote inicial.
- Fase 2: pacote inicial completo, sem respostas de provedores.
- Fase 4: A08 após pedido sobre ROOK; A23 após pedido complementar; A10/A10B após e-mails e pedido ao Google; A11, A13 e A26 conforme pedidos próprios.
- A09 depende da cobertura dos dez registros de conexão; A12 e A16 dependem das respectivas solicitações de diligências.
- Fase 5: A15 e A25 na atualização; A24 somente após pedido do novo acesso.
- O dossiê final não exige conclusão predeterminada de autoria. O material disponível encerra no relatório, sem um módulo de operação tática.

## Resultado da validação

Teste de integração executado: cadastro, isolamento entre equipes, entregas compartilhadas, aprovação sem avanço imediato, emissão e substituição de senha, rejeição de senha de outra equipe, bloqueio de reutilização e encerramento após seis etapas.

## Limites desta entrega

O novo ZIP mestre não pôde ser transferido: excede 32 MiB. Roteiro baseado no guia, checkpoint, base canônica, matriz e pacote inicial já examinados. Não houve validação do conteúdo do novo ZIP.

A avaliação dos requisitos é manual. As dependências específicas de respostas da fase 4 ainda são controladas pelo instrutor; o sistema controla material habilitado e fase, sem validação automática de cada pedido. Apenas o pacote inicial está importado.
