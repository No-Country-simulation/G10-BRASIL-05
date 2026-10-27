# [0011] - Modelagem dos Contratos Pydantic de Roteamento e Armazenamento (SCRUM-52)

- **Data:** 2026-10-26
- **Autor(es):** @patrickgutem-create (via Assistente IA) / Pedro Augusto
- **Status:** Aprovado

---

## 1. Por quê? (Contexto e Motivação)
O card `SCRUM-52` exige a formalização estrita dos contratos DTO para a saída da tomada de decisão clínica do agente autônomo:
- `DecisaoRoteamento`: define para onde o documento será encaminhado no hospital (emergência, auditoria humana, farmácia), justificativa clínica e notificação de alerta;
- `ArmazenamentoOCI`: define o espelhamento de auditoria e persistência segregada no bucket Always Free da Oracle Cloud Infrastructure.

---

## 2. Para quê? (Objetivo e Resultados Esperados)
- Criar os módulos `backend/app/schemas/roteamento.py` e `backend/app/schemas/armazenamento.py`.
- Garantir alinhamento 100% com o briefing oficial `mediflow.pdf`.
- Prover validação com Pydantic v2 utilizando `json_schema_extra` para compatibilidade com OpenAPI/Swagger sem warnings de depreciação.
- Fornecer suíte de testes unitários em `backend/tests/test_roteamento_armazenamento.py`.

---

## 3. Como? (Implementação Técnica e Alternativas)
- Pydantic BaseModel com campos obrigatórios e tipagem estrita.
- Testes unitários cobrindo fluxos com e sem notificação de urgência, bem como rejeição de payloads incompletos.

---

## 4. Onde? (Impacto no Código e Arquitetura)
- `backend/app/schemas/roteamento.py`: Modelos `NotificacaoAlerta` e `DecisaoRoteamento`.
- `backend/app/schemas/armazenamento.py`: Modelo `ArmazenamentoOCI`.
- `backend/app/schemas/__init__.py`: Re-exportação centralizada.
- `backend/tests/test_roteamento_armazenamento.py`: Testes unitários.
