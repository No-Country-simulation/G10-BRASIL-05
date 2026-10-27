from app.config.settings import settings

# Limiares e configurações do agente clínico
DEFAULT_CONFIDENCE_THRESHOLD = settings.CONFIDENCE_THRESHOLD

# Termos críticos indicativos de urgência médica para detecção rápida determinística
TERMOS_URGENCIA_CRITICA = [
    "tromboembolismo pulmonar",
    "tep agudo",
    "tep",
    "embolia pulmonar",
    "parada cardiorrespiratoria",
    "parada cardiorrespiratória",
    "parada cardiaca",
    "parada cardíaca",
    "fibrilacao ventricular",
    "fibrilação ventricular",
    "pcr",
    "infarto agudo do miocardio",
    "infarto agudo do miocárdio",
    "iam",
    "supradesnivelamento de segmento st",
    "supra de st",
    "dispneia subita",
    "dispneia súbita",
    "choque septico",
    "choque séptico",
    "avc agudo",
    "avc isquemico",
    "avc isquêmico",
    "avc hemorragico",
    "avc hemorrágico",
    "hemorragia digestiva alta",
    "hemorragia",
    "apendicite aguda",
    "choque anafilatico",
    "choque anafilático",
    "anafilaxia",
    "aneurisma de aorta",
    "tamponamento cardiaco",
    "tamponamento cardíaco",
]

# Destinos possíveis de roteamento
DESTINO_EMERGENCIA = "Fila_Emergencia_Medica"
DESTINO_AUDITORIA_HUMANA = "Auditoria_Humana"
DESTINO_FLUXO_PADRAO = "Fluxo_Padrao"
DESTINO_FARMACIA = "Farmacia_Hospitalar"
DESTINO_AUTORIZACOES = "Auditoria_Autorizacoes"
