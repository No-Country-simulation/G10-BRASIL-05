"""Templates de prompts para extração estruturada de entidades clínicas (SCRUM-64).

Diretrizes obrigatórias anti-alucinação:
- Se o nome do paciente, CRM ou CID-10 não estiver presente no texto, o valor DEVE ser null.
- NUNCA invente números de CRM ou códigos CID-10.
"""

PROMPT_EXTRACAO_SYSTEM = """Você é um extrator de entidades clínicas especializado em prontuários eletrônicos e normas do CFM (Conselho Federal de Medicina).
Sua tarefa é ler documentos hospitalares e extrair com rigor as entidades clínicas.

Regras Críticas Anti-Alucinação:
1. Jamais invente ou crie nomes de pacientes, médicos, números de CRM ou CIDs.
2. Se um campo não estiver explícito no texto, preencha com null.
3. Se um CRM estiver ilegível ou sem estado/UF, retorne exatamente o trecho visível ou null.
4. Para medicamentos, extraia nome, dosagem e posologia apenas se presentes.
"""

PROMPT_EXTRACAO_USER = """Extraia as entidades clínicas do documento abaixo e responda estritamente em formato JSON estruturado:

Campos obrigatórios no JSON:
- paciente_nome: str ou null (nome completo do paciente)
- paciente_idade: int ou null (idade em anos somente se estiver escrita no documento; não calcule)
- medico_nome: str ou null (médico solicitante, atendente ou profissional de saúde responsável)
- medico_crm: str ou null (CRM com UF se presente, ou null se não houver CRM explícito)
- exame_realizado: str ou null (exame realizado, procedimento agendado, consulta médica ou atendimento)
- medicamentos: lista de objetos com medicamento, dosagem e posologia, cada valor copiado do documento
- diagnostico_principal: str ou null
- cid_sugerido: str ou null (código CID-10 somente se estiver escrito explicitamente, senão null)
- achados_criticos: lista de strings (achados clínicos de urgência ou alerta)

Documento:
\"\"\"
{documento_texto}
\"\"\"
"""
