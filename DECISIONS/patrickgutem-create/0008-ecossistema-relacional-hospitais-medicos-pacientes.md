# [0008] - Ecossistema Relacional Normalizado: Hospitais, Médicos e Pacientes

- **Data:** 2026-10-26
- **Autor(es):** @patrickgutem-create (via Assistente IA)
- **Status:** Aprovado

---

## 1. Por quê? (Contexto e Motivação)
Até este momento, os dados de entidades (pacientes, médicos e hospitais) estavam persistidos exclusivamente de forma desnormalizada dentro do documento clínico (`dados_extraidos` em formato JSON e colunas soltas na tabela `documentos_triagem`).
Embora flexível para a ingestão inicial, essa abordagem impede que o MediFlow opere como uma plataforma hospitalar integrada:
- Não há visão longitudinal do paciente (um paciente com múltiplos laudos ou receitas não possui prontuário unificado);
- O corpo clínico não é auditável (não há como consultar todos os laudos emitidos por um determinado CRM);
- Não há segregação de documentos por unidade hospitalar ou polo de atendimento.

---

## 2. Para quê? (Objetivo e Resultados Esperados)
- Normalizar o ecossistema relacional criando as tabelas:
  - `hospitais`: unidades de atendimento, CNPJ, localização e status;
  - `medicos`: corpo clínico com CRM único, especialidade e UF;
  - `pacientes`: prontuário centralizado com CPF, nome, idade e flag de cadastro provisório.
- Estabelecer chaves estrangeiras (`ForeignKeys`) em `documentos_triagem`:
  - `paciente_id` -> `pacientes.id`
  - `medico_id` -> `medicos.id`
  - `hospital_id` -> `hospitais.id`
- Implementar estratégia de **Upsert Automático na Triagem**:
  - Quando um documento é processado, o repositório busca se o paciente e médico já existem no banco; caso não existam, cria o registro automaticamente sem interromper o fluxo de emergência.
- Disponibilizar endpoints REST de consulta:
  - `GET /pacientes` e `GET /pacientes/{id}/historico` (histórico clínico do paciente);
  - `GET /medicos` (consulta de corpo clínico e CRMs);
  - `GET /hospitais` (unidades hospitalares cadastradas).
- Incluir seed automático no `init_db()` com hospitais e médicos de referência para a demonstração do Hackathon.

---

## 3. Como? (Implementação Técnica e Alternativas)

### Alternativas Consideradas:
- **Alternativa A (Descartada):** Cadastro estrito prévio.
  - *Motivo do descarte:* Em pronto-socorro e triagem de urgência, laudos chegam sem cadastro prévio no sistema; bloquear a triagem com erro 400 atrasaria condutas clínicas com risco de morte.
- **Alternativa B (Escolhida):** Modelo relacional normalizado com Upsert inteligente na ingestão.
  - *Motivo da escolha:* Combina a integridade relacional do PostgreSQL com a agilidade do fluxo autônomo, criando o prontuário do paciente dinamicamente à medida que os exames chegam.

### Detalhamento da Solução:
1. **Modelos SQLAlchemy (`backend/app/models/triagem.py`):**
   - Criação de `HospitalModel`, `MedicoModel`, `PacienteModel`.
   - Inclusão das Foreign Keys e relacionamentos `relationship()` em `DocumentoTriagemModel`.
2. **Métodos no `DatabaseRepository` (`backend/app/repositories/database.py`):**
   - `obter_ou_criar_paciente(nome, idade, cpf=None)`
   - `obter_ou_criar_medico(nome, crm, especialidade=None)`
   - `obter_ou_criar_hospital(nome, canal_origem=None)`
   - `seed_dados_iniciais(db)` executado no startup se as tabelas estiverem vazias.
3. **Novas Rotas de Consulta em `backend/app/controllers/triagem.py`:**
   - Rotas para consulta de pacientes, histórico por paciente, médicos e hospitais.

---

## 4. Onde? (Impacto no Código e Arquitetura)
- `backend/app/models/triagem.py`: Novas tabelas relacionais.
- `backend/app/repositories/database.py`: Funções de upsert, relacionamentos e seed.
- `backend/app/controllers/triagem.py`: Novos endpoints de ecossistema.
- `backend/tests/test_ecossistema_relacional.py`: Suíte de testes automatizados.

---

## 5. Consequências e Débitos Técnicos
- **Pontos Positivos:** O sistema agora possui um modelo de dados hospitalar de nível empresarial, permitindo prontuário eletrônico unificado e auditoria de corpo clínico.
- **Riscos / Trade-offs:** Pacientes homônimos sem CPF recebem cadastro provisório e podem precisar de unificação manual via Human-in-the-Loop no futuro.
- **Validação / Testes:** Testes automatizados garantindo o upsert durante a triagem e o correto relacionamento entre as 4 tabelas.
