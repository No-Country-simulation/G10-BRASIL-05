import base64
import binascii
import re

from utils.formatadores import NIVEL_AVISO, NIVEL_ERRO, NIVEL_SUCESSO

TAMANHO_MINIMO_DO_NUMERO = 10
TAMANHO_MAXIMO_DO_NUMERO = 15

SITUACAO_POR_ESTADO = {
    "open": (NIVEL_SUCESSO, "WhatsApp conectado e online", ""),
    "connecting": (
        NIVEL_AVISO,
        "Aguardando a leitura do QR Code",
        "A sessão está ativa e espera o escaneamento no celular.",
    ),
    "close": (NIVEL_ERRO, "WhatsApp desconectado", "Gere o QR Code abaixo para conectar."),
    "not_found": (
        NIVEL_ERRO,
        "Instância ainda não criada",
        "Gere o QR Code abaixo para criar a instância e conectar.",
    ),
    "offline": (
        NIVEL_ERRO,
        "Evolution API indisponível",
        "Verifique se o container da Evolution API está em execução.",
    ),
}


def normalizar_numero(numero: str) -> str:
    return re.sub(r"[\s()+-]", "", numero)


def validar_numero(numero: str) -> str | None:
    digitos = normalizar_numero(numero)
    if not digitos:
        return "Informe o número de destino, com DDI e DDD (exemplo: 5511999999999)."
    if not re.fullmatch(r"[0-9]+", digitos):
        return "Use apenas números, com DDI e DDD (exemplo: 5511999999999)."
    if not TAMANHO_MINIMO_DO_NUMERO <= len(digitos) <= TAMANHO_MAXIMO_DO_NUMERO:
        return "O número deve ter de 10 a 15 dígitos, incluindo DDI e DDD."
    return None


def descrever_conexao(status: dict) -> tuple[str, str, str]:
    """Devolve (nível, título, ajuda) para mostrar o estado da conexão."""
    estado = "open" if status.get("conectado") else (status.get("estado") or "desconhecido")
    return SITUACAO_POR_ESTADO.get(
        estado,
        (NIVEL_ERRO, f"Estado desconhecido: {estado}", "Atualize o status para consultar de novo."),
    )


def decodificar_qrcode(conteudo: str) -> bytes:
    """Converte o QR Code em base64 (com ou sem o prefixo data:image) em bytes de imagem."""
    _, _, dados = conteudo.rpartition("base64,")
    try:
        imagem = base64.b64decode(dados, validate=True)
    except (binascii.Error, ValueError) as erro:
        raise ValueError("O QR Code recebido da API é inválido.") from erro
    if not imagem:
        raise ValueError("O QR Code recebido da API está vazio.")
    return imagem
