"""Central de Mensagens e Orientações do WhatsApp (MediFlow).

Este arquivo reúne todos os textos, mensagens, templates e regras de
redirecionamento exibidos aos usuários no WhatsApp.

Você pode editar livremente qualquer texto abaixo para customizar o tom de voz,
as instruções de próximo passo e as orientações para o paciente.
"""

from typing import Dict, Any, Optional

# ==============================================================================
# 1. Mensagem de Boas-Vindas e Instrução para Mensagens de Texto
# ==============================================================================
# Enviada quando o usuário manda apenas mensagem de texto (ex.: "Oi", "Como funciona?").
MENSAGEM_BOAS_VINDAS_TEXTO = (
    "🏥 *Olá! Bem-vindo ao MediFlow.*\n\n"
    "Sou o assistente inteligente de triagem de documentos de saúde.\n\n"
    "📸 *Como funciona:*\n"
    "Envie aqui uma **foto nítida** ou o arquivo **PDF** do seu documento "
    "(receita médica, pedido de exame, atestado, laudo ou guia de autorização).\n\n"
    "Eu farei a análise imediata do documento e indicarei **o que ele é e para onde você deve se dirigir** para dar andamento."
)

# ==============================================================================
# 2. Confirmação Imediata de Recebimento de Arquivo (Imagem ou PDF)
# ==============================================================================
def mensagem_confirmacao_recebimento(protocolo: str) -> str:
    """Enviada assim que o arquivo é recebido, antes do término da análise."""
    return (
        f"🏥 *MediFlow - Arquivo Recebido*\n\n"
        f"Recebi o arquivo e estou verificando se ele é um documento clínico válido.\n"
        f"🆔 *Protocolo:* `{protocolo}`\n\n"
        f"⏳ Enviarei o resultado da verificação em alguns instantes."
    )

# ==============================================================================
# 3. Orientações de Redirecionamento por Tipo de Documento / Destino
# ==============================================================================
# Mapeia cada tipo de documento identificado para o seu respectivo encaminhamento.
ORIENTACOES_POR_TIPO: Dict[str, Dict[str, str]] = {
    "RECEITA": {
        "tipo_amigavel": "Receita Médica / Prescrição de Medicamentos",
        "para_onde_seguir": "Farmácia / Posto de Dispensação",
        "instrucoes": (
            "Dirija-se à farmácia da unidade de saúde ou farmácia credenciada portando "
            "esta receita e um documento oficial de identificação com foto para a "
            "retirada ou compra dos medicamentos prescritos."
        ),
    },
    "PEDIDO_EXAME": {
        "tipo_amigavel": "Pedido / Solicitação de Exame",
        "para_onde_seguir": "Laboratório / Centro de Diagnóstico",
        "instrucoes": (
            "Encaminhe-se ao laboratório de análises clínicas ou centro de imagem credenciado "
            "para agendar o procedimento. Lembre-se de verificar previamente a necessidade "
            "de preparo especial (como jejum)."
        ),
    },
    "LAUDO": {
        "tipo_amigavel": "Laudo de Exame Diagnóstico",
        "para_onde_seguir": "Retorno ao Médico Assistente / Fila de Exames",
        "instrucoes": (
            "Seu resultado de exame foi registrado. Apresente este laudo na sua próxima "
            "consulta médica de retorno para que o profissional avalie os achados e defina a conduta."
        ),
    },
    "GUIA_TISS": {
        "tipo_amigavel": "Guia de Autorização / Solicitação de Procedimento (TISS)",
        "para_onde_seguir": "Central de Regulação / Autorizações do Convênio",
        "instrucoes": (
            "Seu documento foi direcionado ao setor de autorizações e regulação. "
            "Aguarde o prazo de liberação do procedimento pela operadora ou central de regulação."
        ),
    },
    "ATESTADO": {
        "tipo_amigavel": "Atestado Médico",
        "para_onde_seguir": "Recursos Humanos (RH) / Medicina do Trabalho",
        "instrucoes": (
            "Apresente este atestado ao departamento de Recursos Humanos da sua empresa "
            "ou instituição de ensino dentro do prazo regulamentar para justificativa de ausência."
        ),
    },
    "RELATORIO_ALTA": {
        "tipo_amigavel": "Relatório de Alta / Encaminhamento Hospitalar",
        "para_onde_seguir": "Atendimento Geral / Acompanhamento Ambulatorial",
        "instrucoes": (
            "Siga as orientações prescritas na alta hospitalar e agende o acompanhamento "
            "ambulatorial na Unidade Básica de Saúde ou especialista indicado."
        ),
    },
    "EMERGENCIA": {
        "tipo_amigavel": "Documento com Sinais de Urgência Clínica",
        "para_onde_seguir": "🚨 Pronto-Socorro / Emergência Mais Próximo",
        "instrucoes": (
            "Atenção: Os dados do documento indicam necessidade de avaliação presencial imediata. "
            "Dirija-se sem demora ao serviço de Pronto Atendimento / Emergência mais próximo."
        ),
    },
    "PADRAO": {
        "tipo_amigavel": "Documento Médico Clínico",
        "para_onde_seguir": "Atendimento / Recepção da Unidade de Saúde",
        "instrucoes": (
            "Seu documento foi validado pelo MediFlow. Apresente o protocolo na recepção "
            "da unidade de saúde para dar andamento ao seu atendimento."
        ),
    },
}

# ==============================================================================
# 4. Formatação da Devolutiva Final ao Usuário
# ==============================================================================
def formatar_mensagem_devolutiva(
    protocolo: str,
    tipo_documento_raw: str,
    especialidade: Optional[str] = None,
    prioridade: Optional[str] = None,
    destino_raw: Optional[str] = None,
    paciente_nome: Optional[str] = None,
    medico_nome: Optional[str] = None,
    is_urgente: bool = False,
) -> str:
    """Monta a devolutiva enviada ao paciente com foco direto em:

    1. O que é o documento
    2. Para onde ele deve seguir e o que fazer
    """
    # Determina chave de orientação
    chave = "PADRAO"
    if is_urgente:
        chave = "EMERGENCIA"
    else:
        tipo_upper = (tipo_documento_raw or "").upper()
        destino_upper = (destino_raw or "").upper()
        if "RECEITA" in tipo_upper or "FARMACIA" in destino_upper:
            chave = "RECEITA"
        elif "LAUDO" in tipo_upper:
            chave = "LAUDO"
        elif any(k in tipo_upper for k in ("EXAME", "PEDIDO")) or "EXAMES" in destino_upper:
            chave = "PEDIDO_EXAME"
        elif "TISS" in tipo_upper or "AUTORIZ" in destino_upper:
            chave = "GUIA_TISS"
        elif "ATESTADO" in tipo_upper:
            chave = "ATESTADO"
        elif "ALTA" in tipo_upper:
            chave = "RELATORIO_ALTA"

    config = ORIENTACOES_POR_TIPO.get(chave, ORIENTACOES_POR_TIPO["PADRAO"])
    nome_doc = config["tipo_amigavel"]
    onde_ir = config["para_onde_seguir"]
    instrucoes = config["instrucoes"]

    icone_prioridade = "🔴" if is_urgente or (prioridade and prioridade.upper() in ("URGENTE", "EMERGENCIA")) else "🟢"
    prioridade_txt = prioridade.upper() if prioridade else "NORMAL"
    especialidade_txt = especialidade if especialidade and especialidade != "Geral" else "Clínica Médica"

    linhas = [
        "🏥 *RESULTADO DA TRIAGEM - MEDIFLOW*",
        "━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📄 *O que é o documento:* {nome_doc}",
        f"🩺 *Especialidade:* {especialidade_txt}",
        f"🆔 *Protocolo:* `{protocolo}`",
        f"🚨 *Prioridade:* {icone_prioridade} {prioridade_txt}",
    ]

    if paciente_nome and paciente_nome not in ("Não identificado", "N/A", ""):
        linhas.append(f"👤 *Paciente:* {paciente_nome}")

    if medico_nome and medico_nome not in ("Não informado", "N/A", ""):
        linhas.append(f"👨‍⚕️ *Solicitante:* {medico_nome}")

    linhas.extend([
        "",
        f"📍 *PARA ONDE VOCÊ DEVE SEGUIR:*",
        f"*{onde_ir}*",
        "",
        f"💡 *Orientações:*",
        f"{instrucoes}",
        "━━━━━━━━━━━━━━━━━━━━━━━━━",
        "_Documento processado com segurança pela plataforma MediFlow._",
    ])

    return "\n".join(linhas)

# ==============================================================================
# 5. Mensagens de Documento Não Reconhecido ou Ilegível
# ==============================================================================
def mensagem_documento_invalido(motivo: Optional[str] = None) -> str:
    """Enviada quando o arquivo não é um documento médico ou está ilegível."""
    detalhe = motivo or "Não foi possível identificar informações médicas válidas no arquivo."
    return (
        "⚠️ *Atenção: Não foi possível analisar seu documento.*\n\n"
        f"📋 *Motivo:* {detalhe}\n\n"
        "📸 *Dicas para um novo envio:*\n"
        "• Certifique-se de fotografar o documento completo, reto e sem cortar as bordas.\n"
        "• Prefira ambientes bem iluminados e sem reflexos ou sombras sobre o papel.\n"
        "• Você também pode enviar o arquivo diretamente em formato **PDF**."
    )
