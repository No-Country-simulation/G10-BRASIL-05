# Plano de evolução para agentes especializados com LangGraph

## Objetivo

Propor uma evolução do fluxo atual do backend, hoje organizado como um `StateGraph` linear com cinco etapas — ingestão, classificação, extração, avaliação e roteamento — para um fluxo com responsabilidades mais explícitas, tratamento de exceções e revisão humana antes de decisões que precisem de validação. A proposta acrescenta uma verificação inicial de elegibilidade para separar documentos do domínio médico/clínico de conteúdo fora desse escopo. Este documento registra uma proposta para aprovação; não representa implementação.

## Princípios da proposta

- Os “agentes” são nós especializados coordenados por um único grafo LangGraph e compartilham um estado tipado. Não são processos autônomos separados nem serviços independentes.
- O grafo mantém controle explícito do fluxo, das condições de transição e dos resultados de cada etapa.
- A revisão humana é um `interrupt`/pausa da execução para apresentar contexto e aguardar uma decisão. Não é um agente, nó inteligente ou processo autônomo.
- A automação prepara recomendações e evidências; casos encaminhados para revisão ficam pendentes até uma decisão humana registrada.
- O estado necessário à retomada deve ser persistido com checkpoint e associado a um identificador estável da execução/documento.
- A elegibilidade avalia apenas se o conteúdo parece pertencer ao domínio médico/clínico. Não verifica autenticidade do documento nem sua validade legal.
- Saída estruturalmente válida não significa dado correto: confiança do modelo e conformidade com schema não provam que o valor foi lido corretamente da imagem.
- Cada campo extraído precisa de evidência verificável ligada à fonte original. Texto gerado pelo próprio modelo, sem trecho/localização verificável na página ou imagem, não é prova.

## Arquitetura proposta

```text
Entrada
  → Ingestor
  → Filtro de elegibilidade / escopo
       ├─ médico → Verificador de qualidade/legibilidade
       │                ├─ insuficiente → pausa (interrupt) → revisão humana (corrigir/aprovar ou pedir reenvio)
       │                └─ adequado → Classificador de tipos clínicos → Extrator com evidências por campo
       │                             → Validador de schema + suporte na fonte original
       │                                  ├─ evidência ausente/não sustenta valor → bloquear campo → revisão humana
       │                                  └─ evidência sustenta valor → Avaliador de risco e confiança
       │                                       ├─ revisão necessária (inclui campo crítico duvidoso) → pausa (interrupt) → decisão humana → retomada
       │                                       └─ critérios automáticos atendidos
       │                                            → Preparador de roteamento
       │                                            → Persistência / notificação conforme política aprovada
       ├─ não médico → Avisar usuário: documento não médico / processamento recusado → END
       └─ incerto → pausa (interrupt) → decisão humana → retomada/encerramento
```

No caminho **não médico**, a recusa e o aviso ao usuário são seguidos de encerramento imediato (`END`). O documento, seus dados e metadados derivados não devem ser salvos nem persistidos nesse caminho. A análise temporária necessária para determinar elegibilidade não deve gerar registro persistente; o conteúdo transitório é descartado ao encerrar.

O estado compartilhado das execuções que prosseguem deve guardar, no mínimo, identificador e origem do documento, referências recuperáveis à página/imagem original, resultados estruturados com evidência por campo, scores de confiança, alertas de validação, motivo de escalonamento, status da execução, decisão humana e resultado final. A revisão deve mostrar a imagem original ou sua região correspondente junto ao valor, evidência, campos ausentes/ilegíveis/incertos, divergências e justificativas; uma transcrição produzida pela IA não substitui a fonte. Na saída não médica, conteúdo e metadados derivados permanecem apenas transitórios e são descartados ao terminar.

### Nós especializados e responsabilidades

| Nó | Responsabilidade proposta | Saída principal |
| --- | --- | --- |
| **Ingestor** | Receber o documento e preparar uma representação transitória para avaliação de escopo, registrando apenas metadados técnicos mínimos necessários. Não realizar a avaliação decisiva de qualidade/legibilidade nem extrair dados clínicos nesta etapa. | Conteúdo/representação transitória para o filtro, metadados técnicos mínimos e falhas de recebimento. |
| **Filtro de elegibilidade/escopo** | Avaliar se o conteúdo parece pertencer ao domínio médico/clínico (por exemplo, separar uma receita médica de uma receita culinária de pudim ou miojo). Produzir uma das três saídas: **médico**, seguindo primeiro para o verificador de qualidade/legibilidade; **não médico**, avisando o usuário de que o documento não é médico e que o processamento foi recusado, sem salvar nem persistir o documento ou seus dados, e encerrando imediatamente; **incerto**, encaminhando para revisão humana. Esse filtro não atesta autenticidade, autoria ou validade legal. | Resultado de elegibilidade (médico/não médico/incerto), confiança e justificativa; evidências apenas transitórias quando o resultado for não médico. |
| **Verificador de qualidade e legibilidade** | Para documentos elegíveis, antes de qualquer classificação clínica ou extração de dados, verificar integridade técnica e qualidade visual/textual: resolução, blur/definição, legibilidade e cobertura/qualidade do OCR. Se insuficiente, não inferir nem preencher dados; indicar motivo e campos/regiões candidatos ausentes, ilegíveis ou incertos, e pausar para revisão, incluindo pedido de nova imagem quando necessário. Se adequado, liberar a classificação clínica e, depois, a extração. | Avaliação de qualidade, decisão adequado/insuficiente e motivo; regiões/campos problemáticos para revisão. |
| **Classificador de tipos clínicos** | Após qualidade adequada, identificar o tipo documental (por exemplo, receita médica, laudo ou atestado), especialidade e prioridade provável, mantendo score e método/evidências da classificação. | Classificação clínica estruturada e confiança. |
| **Extrator** | Quando a qualidade for adequada, extrair somente informações apoiadas pelo documento. Cada campo deve vir acompanhado de evidência vinculada à fonte original: trecho/crop ou coordenada/localização na imagem ou página, referência à página/imagem, confiança e status. Evidência é o conteúdo visível na fonte, não apenas texto produzido pelo modelo. Usar `null` e marcar como ausente/ilegível/incerto quando não houver leitura confiável; nunca inferir valores não lidos. | Dados estruturados com referência verificável à fonte e evidência, localização, confiança e status por campo; `null` para ausente/ilegível. |
| **Validador** | Validar schema e, separadamente, conferir que a evidência apontada existe na fonte original e sustenta o valor daquele campo. Conferir consistência e dados essenciais com regras determinísticas. Schema válido ou confiança alta do modelo não prova correção. Se a evidência não corresponder, não estiver disponível ou não sustentar o valor, bloquear o campo e encaminhar à revisão humana; nunca liberar apenas por passar no schema. Para campos críticos — por exemplo, medicamento, dose/posologia e identificação do paciente — baixa legibilidade ou discrepância exige revisão humana antes de qualquer uso/roteamento. Uma segunda leitura/OCR independente pode sinalizar divergência, mas não serve como prova nem garante correção. | Resultados separados de schema e verificação da fonte; campos confirmados, bloqueados e escalados, com motivo. |
| **Avaliador de risco e confiança** | Combinar prioridade/urgência, confiança, validação e regras de negócio para decidir se o fluxo pode prosseguir ou deve ser escalonado. | Decisão de seguir ou solicitar revisão, com motivos explícitos. |
| **Ponto de revisão humana** | Pausar via `interrupt`, expor o caso e aguardar decisão humana. A pessoa revisora precisa ver a imagem original/região associada ao campo, não somente o texto extraído, e pode corrigir valores, aprovar o que conseguir verificar ou pedir reenvio de imagem/documento. Para campos críticos sem leitura verificável, a aprovação humana precede qualquer uso/roteamento. O objetivo é revisar fonte e transcrição, não assumir ou formular diagnóstico. Após resposta válida, permitir a retomada do checkpoint. | Decisão humana, correções, evidência revisada ou pedido de reenvio auditáveis. Este ponto não é um agente. |
| **Preparador de roteamento** | Propor destino e notificações com base nos dados aprovados e nas regras vigentes. Aplicar a política para casos aprovados, corrigidos ou rejeitados. | Decisão de roteamento e justificativa. |
| **Finalizador/auditoria** | Persistir resultados, trilha de execução, decisão humana e status final; emitir notificações apenas segundo a política aprovada. | Estado final rastreável. |

Os nós existentes podem ser reutilizados e renomeados/refinados em etapas posteriores. O filtro de elegibilidade decide se o material parece médico, não qual documento médico é nem se é autêntico ou legalmente válido. Para documentos elegíveis, o verificador de qualidade é executado imediatamente depois do filtro e antes de qualquer classificação clínica ou extração. A validação do schema e a verificação do valor contra a fonte original são controles separados: a primeira checa formato; a segunda checa se o conteúdo visível sustenta o dado. Confiança do modelo, texto por ele produzido e uma segunda leitura/OCR não substituem essa verificação. Instruções de prompt são apenas uma camada de proteção; evidência obrigatória, consistência determinística, bloqueio de campo sem suporte e revisão humana com acesso à imagem original formam as demais barreiras.

## Pausa e retomada para revisão humana

1. O filtro de elegibilidade ou um nó posterior detecta uma situação incerta/de escalonamento e registra os motivos e dados necessários à decisão. Dúvida sobre o domínio pausa antes do classificador clínico. Qualidade insuficiente pausa antes da extração e informa campos ausentes/ilegíveis/incertos, motivo e se é necessária nova imagem. Outros critérios podem pausar após classificação, extração e validação. Se o resultado for não médico, aplica-se o encerramento imediato descrito acima, sem persistência.
2. O grafo chega ao ponto de revisão e emite um `interrupt`, suspendendo a execução antes do roteamento final ou de efeitos externos que dependam de aprovação.
3. Um checkpoint durável preserva o estado e o ponto de continuação. A execução permanece com status pendente, vinculada ao identificador do documento e da execução.
4. A interface ou operador autorizado apresenta o resumo e permite aprovar, corrigir campos, solicitar complementação ou rejeitar/devolver o caso. Para problemas de leitura, pode aprovar/corrigir o que estiver legível ou pedir reenvio de imagem/documento; essa revisão não deve assumir diagnóstico. A identidade, horário, decisão e alterações devem ser auditados.
5. A resposta humana é validada e enviada para a retomada da mesma execução/checkpoint. O grafo continua a partir da pausa, incorporando as correções aprovadas sem repetir etapas anteriores desnecessariamente. Se houver pedido de reenvio, a nova imagem/documento volta ao verificador de qualidade antes de qualquer extração.
6. O fluxo segue para o roteamento e a finalização conforme a decisão e a política aprovadas. Se a resposta for inválida ou o checkpoint não puder ser retomado, o caso permanece pendente e recebe tratamento de erro explícito, sem roteamento silencioso.

Detalhes de persistência, prazo de pendência, autorização dos revisores e comportamento em indisponibilidade precisam ser definidos antes de implementar o ciclo completo.

## Critérios iniciais de escalonamento

Os critérios abaixo são ponto de partida para discussão; valores e consequências finais precisam ser aprovados e calibrados com dados representativos.

1. **Urgência detectada:** classificação como urgente/emergência, ou sinais clínicos/regra de segurança que indiquem potencial dano se o fluxo seguir sem confirmação. Definir se esses casos geram alerta imediato em paralelo à revisão e qual destino provisório é permitido.
2. **Elegibilidade incerta:** o filtro não consegue determinar com confiança suficiente se o conteúdo pertence ao domínio médico/clínico. Encaminhar para revisão antes de qualquer classificação clínica.
3. **Baixa confiança:** score de elegibilidade, classificação clínica ou extração abaixo de um limiar configurável por etapa/tipo documental. Como hipótese inicial para avaliação, considerar revisão quando qualquer score relevante for inferior a `0,75`; esse número não é regra clínica nem valor aprovado.
4. **Qualidade insuficiente/sem suporte:** baixa resolução, blur, baixa legibilidade ou cobertura/qualidade OCR insuficiente; campo sem evidência textual/localização; ou score/status indicando leitura incerta. Pausar antes de usar os dados, retornar valores como ausentes/ilegíveis/incertos (ou `null` no schema) e permitir correção humana ou pedido de nova imagem.
5. **Inconsistências:** conflito entre campos extraídos, classificação e conteúdo; falha de validação de schema; divergência entre prioridade sugerida e sinais observados; ou informação contraditória entre páginas/campos.
6. **Dados essenciais ausentes:** falta de campos obrigatórios para a decisão seguinte, definidos por tipo documental. Dado não encontrado deve permanecer ausente e motivar revisão ou pedido de complementação, sem inferência automática.
7. **Falha operacional com impacto na decisão:** documento ilegível, extração incompleta ou indisponibilidade de dependência que impeça resultado confiável. A política deve distinguir retentativa técnica de encaminhamento humano.

Os motivos devem ser cumulativos e legíveis: mais de um critério pode encaminhar o mesmo caso. A avaliação deve registrar qual regra disparou, seus dados de entrada e a versão da política aplicada.

## Etapas de implementação propostas

1. **Aprovar escopo e política:** decidir quais conteúdos são elegíveis como médicos e os critérios para casos incertos, limiares, campos essenciais, ações para urgências e quem pode revisar cada tipo de caso. A ação para não médicos já está definida: avisar o usuário, recusar o processamento, não persistir documento/dados e encerrar imediatamente.
2. **Desenhar o estado e os contratos:** definir schema compartilhado, status (por exemplo, em processamento, pendente de revisão, aprovado/corrigido/rejeitado, concluído e falha), identificadores e formato de auditoria.
3. **Refinar os nós especializados:** manter cada responsabilidade pequena e com entradas/saídas validadas; explicitar o filtro de elegibilidade, o verificador técnico e visual/textual de qualidade antes de qualquer classificação clínica ou extração, a extração com evidência/localização/confiança/status por campo, e a validação separada de schema, suporte da evidência na imagem original e consistência determinística. Definir os campos críticos que exigem revisão quando houver discrepância ou baixa legibilidade. Combinar instruções de prompt com garantias executáveis: evidência obrigatória, bloqueio e escalação de campos sem suporte.
4. **Definir ramificações do grafo:** médico segue para verificação de qualidade; qualidade insuficiente pausa para revisão e possível reenvio; qualidade adequada segue para classificação e extração; não médico avisa, recusa e termina imediatamente sem persistência; incerto no filtro de escopo pausa para revisão. Incluir falhas, retentativas limitadas e demais critérios de revisão.
5. **Implementar checkpoint e interrupt:** escolher e configurar armazenamento durável, associar checkpoint à execução e garantir que a retomada continue do ponto correto.
6. **Integrar a experiência humana:** definir como a fila de pendências é consultada, como o revisor registra decisão/correção e como permissões e auditoria funcionam. Pode ser interface existente ou endpoint dedicado, conforme decisão de produto.
7. **Conectar roteamento e efeitos externos:** só executar roteamento, persistência definitiva e notificações na ordem autorizada pela política; assegurar idempotência para evitar duplicação após retomadas.
8. **Validar e liberar gradualmente:** cobrir caminhos automáticos, imagens legíveis e ilegíveis, baixa resolução/blur, OCR insuficiente, campos com e sem evidência, pausas, correções e reenvio humano, falhas e duplicidade; comparar resultados com o fluxo atual em modo controlado antes de ativar a política para todos os casos.

## Decisões que precisam da aprovação do usuário

- Quais tipos documentais e etapas entram no primeiro escopo, e quais podem continuar no fluxo atual?
- Qual critério define conteúdo médico/clínico elegível e quem resolve os casos incertos? Para conteúdo não médico, o comportamento proposto é fixo: avisar o usuário, recusar, não persistir e encerrar imediatamente.
- Qual score e qual método de confiança devem controlar o limiar inicial? O valor ilustrativo `0,75` deve ser ajustado por tipo documental?
- Toda urgência exige confirmação humana antes do roteamento, ou existe uma ação de alerta imediato permitida em paralelo à pausa?
- Quais campos são essenciais para cada tipo de documento e quais inconsistências sempre bloqueiam o avanço?
- Qual mecanismo de revisão verificável ligará cada evidência à página/região original? Quais campos são críticos e exigem aprovação humana diante de discrepância ou baixa legibilidade, antes de qualquer uso/roteamento?
- Quais limites de resolução, blur, legibilidade e qualidade/cobertura OCR definem qualidade insuficiente? Que evidência e confiança são exigidas por campo antes de permitir o uso dos dados?
- Como deve funcionar o pedido de reenvio de imagem e qual revisão/correção humana é permitida sem entrar em diagnóstico?
- Quais decisões o revisor pode tomar (aprovar, corrigir, solicitar complementação, rejeitar/devolver) e quais perfis podem tomá-las?
- Qual interface/canal será usado para revisão e qual prazo/SLA se aplica a casos pendentes?
- Onde checkpoints e a trilha de auditoria serão persistidos, por quanto tempo e como tratar expiração, falha ou retomada duplicada?
- Quais efeitos (roteamento, gravação definitiva e notificações) só podem ocorrer após aprovação humana?
- Como será feita a implantação gradual e qual indicador/critério autoriza expandir o fluxo?

## Escopo e status

A arquitetura foi aprovada pelo usuário e a implementação está em andamento. O código ainda precisa de validação ponta a ponta com PostgreSQL, que não está disponível neste ambiente.

---

## Estrutura de módulos aprovada para `backend/app/agent/nodes/`

Esta seção registra a estrutura aprovada de arquivos e fronteiras. A implementação está em andamento. Também são necessários ajustes em `state.py`, `graph.py` e no serviço de triagem, porque os nós sozinhos não conseguem persistir checkpoints, retomar uma execução nem impedir gravações feitas antes da elegibilidade.

### Estrutura proposta

```text
backend/app/agent/
├── graph.py                         # Registra nós, condições, interrupt, checkpoint e retomada
├── state.py                         # Contrato tipado compartilhado do grafo
├── nodes/
│   ├── ingestao.py                  # Normalização e metadados transitórios de entrada
│   ├── filtro_elegibilidade.py      # Médico / não médico / incerto
│   ├── qualidade_documento.py      # Integridade, legibilidade e resultado do OCR
│   ├── classificador.py             # Tipo documental médico, especialidade e prioridade
│   ├── extrator.py                  # Campos extraídos e evidência por campo
│   ├── validador.py                 # Schema, evidência na fonte e consistência
│   ├── avaliador.py                 # Risco, confiança e decisão de escalonamento
│   ├── revisao_humana.py            # Pausa e retomada via interrupt; sem acesso a banco
│   ├── roteador.py                  # Destino calculado somente após aprovação das barreiras
│   ├── finalizador.py               # Estado final e mensagem/status, sem persistência
│   └── validadores_clinicos.py      # Regras determinísticas reutilizadas por validador.py
└── prompts/
    ├── elegibilidade.py             # Instruções do filtro, se a opção LLM for aprovada
    ├── classificacao.py             # Instruções de classificação médica
    └── extracao.py                  # Instruções de extração sem inferir campos
```

`validadores_clinicos.py` já existe e contém funções de validação; a proposta é mantê-lo como biblioteca de regras chamada por `validador.py`, em vez de registrá-lo diretamente como nó. Os nós de ingestão, classificação, extração, avaliação e roteamento atuais seriam reaproveitados/refinados onde couberem.

### Caminhos do grafo propostos

```text
START → ingestão → elegibilidade
  ├─ não médico → finalizador (recusado, avisar usuário, sem persistência) → END
  ├─ incerto → interrupt de revisão humana
  │                 ├─ confirmado médico → qualidade → classificação → extração → validação → avaliação
  │                 ├─ confirmado não médico → finalizador (recusado, sem persistência) → END
  │                 └─ reenvio/rejeição → finalizador com status correspondente → END
  └─ médico → qualidade
                 ├─ insuficiente/incerta → interrupt → reenvio ou retomada após correção
                 └─ adequada → classificação → extração → validação
                                      ├─ evidência/schema/consistência falhou → interrupt
                                      └─ passou → avaliação de risco
                                                     ├─ requer humano → interrupt
                                                     └─ pode prosseguir → roteamento → finalizador → END
```

Nenhum nó de roteamento, persistência definitiva ou notificação externa deve ser executado antes da revisão quando ela for obrigatória. A persistência e o disparo de efeitos externos continuam na camada de serviço; os nós retornam atualizações do estado e não acessam banco, Redis, Mongo ou OCI.

### Contrato de estado a acrescentar

- **Entrada/fonte:** identificador, canal, tipo do arquivo, texto transitório e referência recuperável à fonte original (sem copiar o binário para o estado do checkpoint).
- **Elegibilidade:** resultado `medico`, `nao_medico` ou `incerto`, justificativa e confiança.
- **Qualidade:** legibilidade, sinais técnicos/OCR, regiões ou campos problemáticos e motivo de pausa.
- **Extração:** valores e evidência por campo, com trecho/localização na fonte, confiança e status (`confirmado`, `ausente`, `ilegivel` ou `incerto`).
- **Validação/risco:** erros de schema, campos bloqueados, divergências, urgência, score e motivos de escalonamento.
- **Revisão/execução:** decisão humana, correções, status do fluxo e resultado final.

### Integrações fora de `nodes` necessárias para o fluxo funcionar

1. `graph.py`: criar arestas condicionais, ponto `interrupt`, identificador estável por documento e compilação com checkpoint.
2. Checkpoint: proposta de usar PostgreSQL, já presente na aplicação, com o pacote oficial de checkpoint Postgres do LangGraph. Isso adiciona uma dependência e exige inicialização/gestão do ciclo de vida do saver.
3. `services/triagem.py`: não persistir não médicos; salvar casos elegíveis pendentes; retomar o mesmo checkpoint após decisão humana; persistir resultado/notificações só após a liberação do grafo.
4. Controllers e schemas: transportar referência da fonte original até o fluxo e adaptar a decisão existente de auditoria para retomar a execução, mantendo o contrato HTTP acordado.
5. Upload/WhatsApp e parser: hoje o grafo recebe texto, não a imagem original nem coordenadas/OCR confiável. Para o revisor conferir imagem/região e o validador confirmar evidência contra a fonte, será necessário disponibilizar uma referência segura à imagem original e metadados do OCR. Sem isso, o sistema deve bloquear o campo e pedir revisão/reenvio; não pode tratar a transcrição como prova da imagem.

### Defaults propostos para esta primeira implementação

- Reutilizar o `CONFIDENCE_THRESHOLD` atual (padrão `0,75`), sem introduzir limiares numéricos novos.
- Elegibilidade sem sinal médico claro resulta em `incerto`, não em aprovação automática; sinais explícitos de conteúdo culinário sem sinais clínicos resultam em `nao_medico`.
- Documento médico com qualidade textual insuficiente, campo sem evidência verificável ou divergência em campo crítico pausa para revisão. Em imagens, até existir referência verificável da fonte original, OCR sozinho não libera campos críticos.
- Urgência pausa antes do roteamento final; a notificação externa só é disparada após decisão humana, evitando efeitos irreversíveis antes da revisão.
- A revisão pode aprovar, corrigir, rejeitar ou solicitar reenvio. Solicitar reenvio encerra a execução atual como pendente de novo documento; o novo arquivo inicia pela etapa de qualidade.
- Inicialmente, a experiência humana usa a fila/endpoint de auditoria já existente, com o ajuste necessário para retomar o checkpoint. A identidade do revisor continua sendo registrada pelo fluxo de auditoria.

### Execução aprovada

A estrutura, o fluxo condicional e os defaults acima foram aprovados. A implementação será feita em etapas: (1) estado e nós; (2) grafo, interrupt e checkpoint Postgres; (3) integração de upload, serviço e auditoria; (4) cobertura de testes para recusa sem persistência, qualidade/evidência, pausa, retomada, correção, reenvio e roteamento.
