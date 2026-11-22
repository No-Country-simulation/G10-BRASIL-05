# Configuração de LLM — guia rápido

Use este guia ao configurar ou trocar o modelo de LLM do MediFlow. O objetivo é manter o contrato do fluxo; modelos diferentes ainda podem produzir resultados diferentes, então valide cada troca com exemplos representativos.

## Configuração atual

- Provedor implementado: OpenRouter, por meio de `ChatOpenAI` compatível com a API OpenAI.
- Variáveis: `OPENROUTER_API_KEY` e `OPENROUTER_MODEL`.
- Modelo padrão no código: `openrouter/free` (roteador; não fixa um modelo subjacente).
- Timeout da chamada: 35 segundos.
- Limite mínimo de confiança para encaminhamento automático: `CONFIDENCE_THRESHOLD=0.80`.
- Sem `OPENROUTER_API_KEY`, o cliente não é criado e as etapas recorrem aos fallbacks disponíveis.

Configure os valores locais em `backend/.env`, usando `backend/.env.example` como referência. Nunca coloque chaves no código, neste guia ou em arquivos versionados.

## Checklist ao escolher um modelo

1. **Identificador exato:** configure o ID de modelo aceito pelo provedor. Para comparação reproduzível, prefira um modelo específico em vez de `openrouter/free`, que pode encaminhar chamadas a modelos diferentes.
2. **Compatibilidade de API:** confirme que o modelo está acessível pela OpenRouter e funciona com a interface de chat usada pelo `ChatOpenAI`.
3. **Imagens:** se documentos de imagem fizerem parte do fluxo, confirme suporte a entrada de imagem no modelo e no endpoint. Sem suporte, a transcrição multimodal não funciona; atualmente o parser registra a falha e devolve um texto de encaminhamento para auditoria manual. O sistema não faz uma verificação prévia explícita da capacidade do modelo.
4. **Respostas JSON:** classificação e extração dependem de JSON em texto. A classificação valida os campos e enums esperados; a extração espera nomes e tipos de campo definidos no prompt. Não há configuração de saída estruturada/JSON mode no cliente atualmente.
5. **Contexto e entrada:** os prompts de classificação e extração limitam o texto do documento a 4.000 caracteres. Verifique se o modelo aceita esse volume, além das instruções e do conteúdo da chamada.
6. **Latência e limites:** confirme que o modelo normalmente responde dentro do timeout atual de 35 segundos e que sua cota/limites são adequados.
7. **Qualidade e efeito operacional:** compare os mesmos documentos antes e depois da troca. Diferenças de classificação, prioridade, score e campos extraídos podem alterar a confiança final, acionar auditoria humana ou fazer o fluxo usar heurísticas.

## O que acontece se a resposta não servir

- **Classificação:** falha de chamada, JSON inválido ou campos fora do schema acionam o classificador heurístico. Se ele também não reconhecer o documento, o tipo fica sem identificação.
- **Extração:** falha de chamada ou JSON inválido aciona a extração heurística.
- **Imagem:** falha de chamada multimodal leva ao texto de encaminhamento para auditoria manual; isso não equivale a uma transcrição OCR bem-sucedida.
- **Validação posterior:** campos extraídos sem correspondência literal no texto são bloqueados e podem exigir revisão.

## Arquivos relacionados

- `backend/.env` — valores e credenciais locais; arquivo privado e não versionado.
- `backend/.env.example` — nomes e exemplos das variáveis.
- `backend/app/config/settings.py` — valores padrão e carregamento das configurações.
- `backend/app/agent/llm.py` — construção do cliente, provedor e timeout.
- `backend/app/agent/nodes/classificador.py` e `backend/app/agent/nodes/extrator.py` — contratos de resposta e fallbacks.
- `backend/app/services/document_parser.py` — transcrição de imagens.
- `backend/app/agent/prompts/` — instruções e formato esperado pelo modelo.
- `backend/app/agent/nodes/validador.py` — validação das extrações e evidências textuais.

## Nota de consistência

O comentário em `backend/app/services/document_parser.py` menciona “GPT-5.4 mini”, mas o cliente efetivamente usa `OPENROUTER_MODEL`. Ao configurar ou revisar o modelo, considere o valor da configuração como fonte do modelo usado e mantenha esse comentário sincronizado numa alteração futura.
