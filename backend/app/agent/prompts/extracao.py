"""Templates de prompts para extração estruturada de entidades clínicas (SCRUM-58, SCRUM-64).

Diretrizes obrigatórias anti-alucinação:
- Se o nome do paciente, CRM ou CID-10 não estiver presente no texto, o valor DEVE ser null.
- NUNCA invente números de CRM ou códigos CID-10.
"""

PROMPT_EXTRACAO_SYSTEM = """Você é um extrator de entidades clínicas especializado em prontuários eletrônicos e normas do CFM (Conselho Federal de Medicina).
Sua tarefa é ler documentos hospitalares e extrair com rigor as entidades clínicas.

Regras Críticas Anti-Alucinação:
1. Jamais invente ou crie nomes de pacientes, médicos, números de CRM, códigos CID ou medicamentos.
2. Se um campo não estiver explícito no texto, preencha com null (ou lista vazia para medicamentos).
3. Copie nomes, CRM e CID exatamente como aparecem no texto.
4. Só preencha cid_sugerido se o código CID-10 estiver escrito no documento; não deduza o código a partir do diagnóstico.
5. Se o CRM estiver ilegível ou sem UF, preencha crm_uf com null.
"""

PROMPT_EXTRACAO_USER = """Extraia as entidades clínicas do documento abaixo e responda estritamente com um JSON neste formato:

{{
  "paciente": {{"nome": str | null, "idade": int | null}},
  "medico_solicitante": {{"nome": str | null, "crm_uf": str | null}},
  "exame_realizado": str | null,
  "diagnostico_principal": str | null,
  "cid_sugerido": str | null,
  "medicamentos": [{{"medicamento": str | null, "dosagem": str | null}}]
}}

- crm_uf no formato 'NUMERO-UF' (ex: '123456-SP').
- cid_sugerido no formato CID-10 (ex: 'I26.9'), apenas se estiver escrito no documento.

Documento:
\"\"\"
{documento_texto}
\"\"\"
"""
