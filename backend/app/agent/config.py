from app.config.settings import settings

# Limiares e configurações do agente clínico
DEFAULT_CONFIDENCE_THRESHOLD = settings.CONFIDENCE_THRESHOLD

# Termos críticos indicativos de urgência médica para detecção rápida determinística
TERMOS_URGENCIA_CRITICA = [
    "tromboembolismo pulmonar",
    "tep agudo",
    "embolia pulmonar",
    "parada cardiorrespiratoria",
    "infarto agudo do miocardio",
    "iam",
    "dispneia subita",
    "choque septico",
    "avc agudo",
    "hemorragia digestiva alta",
]

# Destinos possíveis de roteamento
DESTINO_EMERGENCIA = "Fila_Emergencia_Medica"
DESTINO_AUDITORIA_HUMANA = "Auditoria_Humana"
DESTINO_FLUXO_PADRAO = "Fluxo_Padrao"
DESTINO_FARMACIA = "Farmacia_Hospitalar"
DESTINO_AUTORIZACOES = "Auditoria_Autorizacoes"
