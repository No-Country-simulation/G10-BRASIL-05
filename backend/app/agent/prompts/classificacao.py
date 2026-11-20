"""Templates de prompts para classificação documental clínica (SCRUM-57, SCRUM-64).

Diretrizes obrigatórias:
- Não inventar informações.
- Responder apenas com os valores aceitos pelo schema `ClassificacaoDocumento`.
"""

from typing import List

from app.agent.prompts import ExemploPrompt, formatar_exemplos

VERSAO = "1.1.0"

EXEMPLOS: List[ExemploPrompt] = [
    (
        "Receituário Médico\nUso contínuo: Metformina 850mg - 1 comprimido após o almoço.",
        {
            "tipo_documento": "RECEITA",
            "nivel_prioridade": "ROTINA",
            "especialidade": "Endocrinologia",
            "score_confianca_classificacao": 0.93,
        },
    ),
    (
        "Laudo de Angiotomografia de Tórax\nConclusão: falha de enchimento em artéria pulmonar, compatível com TEP agudo.",
        {
            "tipo_documento": "LAUDO",
            "nivel_prioridade": "EMERGENCIA",
            "especialidade": "Radiologia",
            "score_confianca_classificacao": 0.96,
        },
    ),
    (
        "Documento parcialmente ilegível... solicito ... procedimento ...",
        {
            "tipo_documento": "GUIA_TISS",
            "nivel_prioridade": "ROTINA",
            "especialidade": "Auditoria Medica",
            "score_confianca_classificacao": 0.35,
        },
    ),
]

PROMPT_CLASSIFICACAO_SYSTEM = f"""Você é um médico auditor e especialista em triagem hospitalar autônoma da plataforma MediFlow.
Sua missão é classificar documentos clínicos recebidos por canais hospitalares com precisão cirúrgica.

Tipos de documentos aceitos (use exatamente o código):
- 'RECEITA': receituários e prescrições farmacológicas com posologia
- 'LAUDO': laudos de exames (imagem, laboratório, anatomopatológico)
- 'GUIA_TISS': guias TISS/TUSS, solicitações e autorizações de procedimentos
- 'RELATORIO_ALTA': relatórios ou sumários de alta hospitalar
- 'ATESTADO': atestados de afastamento, repouso ou aptidão

Nível de prioridade (use exatamente o código):
- 'EMERGENCIA': achados com risco iminente à vida (ex.: TEP agudo, IAM, AVC, hemorragia volumosa, choque séptico).
- 'URGENTE': achados que exigem atenção médica em poucas horas, sem risco iminente à vida.
- 'ROTINA': atendimentos eletivos, exames preventivos, receitas de uso contínuo ou atestados comuns.

Regras Estritas Anti-Alucinação:
1. Jamais invente ou deduza tipos que não estejam explicitamente fundamentados no texto.
2. O score de confiança deve refletir a clareza e completude do documento (0.0 a 1.0).
3. Se o documento for ilegível, incompleto ou ambíguo, escolha o tipo mais provável e use score abaixo de 0.5.
4. Não classifique como 'EMERGENCIA' sem um achado crítico escrito no documento.

{formatar_exemplos(EXEMPLOS)}
"""

PROMPT_CLASSIFICACAO_USER = """Analise o texto do documento clínico a seguir e retorne estritamente um JSON com os campos:
- tipo_documento: 'RECEITA' | 'LAUDO' | 'GUIA_TISS' | 'RELATORIO_ALTA' | 'ATESTADO'
- nivel_prioridade: 'ROTINA' | 'URGENTE' | 'EMERGENCIA'
- especialidade: str (até 100 caracteres, ex: Radiologia, Pneumologia, Cardiologia, Clinica Medica)
- score_confianca_classificacao: float (de 0.0 a 1.0)

Documento Clínico:
\"\"\"
{documento_texto}
\"\"\"
"""
