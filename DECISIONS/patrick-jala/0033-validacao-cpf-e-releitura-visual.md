# [0033] - Validação de CPF e releitura visual

- **Data:** 2026-11-21
- **Autor(es):** @patrick-jala (via Assistente IA)
- **Status:** Proposto

---

## 1. Por quê? (Contexto e Motivação)
A extração atual normaliza o CPF pelo tamanho, mas não verifica os dígitos verificadores. Um erro de leitura pode seguir no fluxo como se fosse válido, e não há uma segunda leitura visual para esclarecer o candidato.

## 2. Para quê? (Objetivo e Resultados Esperados)
Exigir CPF matematicamente válido e repetir a releitura visual até dez vezes. Se nenhum resultado for válido, encaminhar o documento para revisão humana com o motivo explícito.

## 3. Como? (Implementação Técnica e Alternativas)
### Alternativas Consideradas:
- **Alternativa A (Descartada):** Persistir a imagem original no estado do grafo/checkpoint. Isso duplica conteúdo sensível e aumenta o estado persistido.
- **Alternativa B (Escolhida):** Reutilizar o caminho já fornecido como `referencia_fonte`, processar a imagem em memória no nó de extração e enviar até dez releituras visuais ao cliente LLM existente. Como não há coordenadas confiáveis na saída atual do OCR, as releituras usam a imagem inteira, sem inventar recortes.

### Detalhamento da Solução:
Adicionar validação pura de CPF no núcleo do agente. Para CPF ausente ou inválido, preparar a imagem via Pillow (ampliando quando útil) e solicitar apenas os dígitos legíveis, sem correção ou inferência. Falha de imagem encerra o retry; falhas de chamada e candidatos inválidos podem ser tentados novamente até o limite. Ao esgotá-lo, encaminhar para revisão humana indicando a falha na leitura do CPF.

## 4. Onde? (Impacto no Código e Arquitetura)
- **Módulos / Diretórios Afetados:** `backend/app/agent`, `backend/tests`.
- **Arquivos Criados / Modificados:** normalização CPF, nó de extração, validador e testes do pipeline.
- **Banco de Dados / Infra:** Sem alterações ou dependências novas.

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** A regra matemática permanece determinística e independente do LLM; o número de releituras é limitado, CPF ausente não segue no processamento automático, e bytes da imagem não são gravados no checkpoint.
- **Riscos / Trade-offs:** Sem coordenadas confiáveis, a releitura visual usa a página inteira e pode não resolver imagens ilegíveis. A validade matemática não confirma que os dígitos foram lidos corretamente.
- **Validação / Testes:** Cobrir dígitos válidos/inválidos, ausência e repetição de CPF, retry válido/inválido, falhas de imagem e LLM e preservar os demais dados extraídos.
