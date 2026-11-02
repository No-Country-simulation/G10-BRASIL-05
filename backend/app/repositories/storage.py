import os
import json
import re
import unicodedata
from datetime import datetime
from typing import Dict, Any, Optional

from app.config.settings import settings
from app.config.logger import logger


class StorageRepository:
    """Repositório de armazenamento segregado no OCI Object Storage e pasta local Storage.

    Gerencia o salvamento dos documentos originais recebidos (via WhatsApp ou upload direto),
    renomeando-os com padronização rigorosa, e armazenando os JSONs de triagem.
    """

    def __init__(self, local_storage_dir: Optional[str] = None):
        self.bucket_name = settings.OCI_BUCKET_NAME
        self.client = None
        self._inicializar_cliente_oci()
        self.local_storage_dir = local_storage_dir or self._obter_diretorio_storage_local()
        os.makedirs(self.local_storage_dir, exist_ok=True)

    def _obter_diretorio_storage_local(self) -> str:
        """Determina o caminho absoluto para o diretório local 'Storage' na raiz do projeto."""
        candidatos = [
            os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../Storage")),
            os.path.abspath("Storage"),
            os.path.abspath("../Storage"),
        ]
        for caminho in candidatos:
            if os.path.exists(caminho):
                return caminho

        caminho_padrao = candidatos[0]
        os.makedirs(caminho_padrao, exist_ok=True)
        return caminho_padrao
    def _inicializar_cliente_oci(self):
        """Tenta autenticar no SDK OCI se os parâmetros estiverem presentes."""
        if settings.OCI_USER_OCID and os.path.exists(os.path.expanduser(settings.OCI_KEY_FILE or "")):
            try:
                import oci
                config = {
                    "user": settings.OCI_USER_OCID,
                    "key_file": os.path.expanduser(settings.OCI_KEY_FILE),
                    "fingerprint": settings.OCI_FINGERPRINT,
                    "tenancy": settings.OCI_TENANCY_OCID,
                    "region": settings.OCI_REGION,
                }
                self.client = oci.object_storage.ObjectStorageClient(config)
            except Exception as e:
                logger.warning(f"[OCI Storage Warning] Falha ao inicializar SDK OCI: {e}. Usando modo simulado.")
                self.client = None

    @staticmethod
    def sanitizar_nome_arquivo(nome_arquivo: Optional[str]) -> str:
        """Sanitiza o nome do arquivo removendo acentos, pontuações e caracteres inválidos."""
        if not nome_arquivo:
            return "documento_clinico"

        nome_base = os.path.basename(nome_arquivo)
        nome_sem_ext, _ = os.path.splitext(nome_base)

        # Normaliza removendo acentos
        nfkd = unicodedata.normalize("NFKD", nome_sem_ext)
        ascii_text = nfkd.encode("ascii", "ignore").decode("ascii")

        # Converte para minúsculas e substitui caracteres não-alfanuméricos por sublinhado
        limpo = re.sub(r"[^\w\-_]", "_", ascii_text.strip().lower())
        limpo = re.sub(r"_+", "_", limpo).strip("_")

        return limpo or "documento_clinico"

    def gerar_nome_arquivo_whatsapp(
        self,
        documento_id: str,
        nome_original: Optional[str] = None,
        extensao: Optional[str] = None,
    ) -> str:
        """Gera um nome padronizado e rastreável para arquivos recebidos via WhatsApp.

        Formato: WPP_{documento_id}_{timestamp}_{nome_sanitizado}{extensao}
        Exemplo: WPP_DOC-WPP-8F21B304_20261102_162540_laudo_torax.pdf
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Determina a extensão normalizada
        ext = ""
        if extensao:
            ext = extensao if extensao.startswith(".") else f".{extensao}"
        elif nome_original and "." in nome_original:
            ext = os.path.splitext(nome_original)[1].lower()

        if not ext:
            ext = ".bin"

        nome_sanitizado = self.sanitizar_nome_arquivo(nome_original)
        doc_id_limpo = documento_id.replace(" ", "_")

        return f"WPP_{doc_id_limpo}_{timestamp}_{nome_sanitizado}{ext}"

    def salvar_arquivo_whatsapp(
        self,
        documento_id: str,
        conteudo: bytes,
        nome_original: Optional[str] = None,
        extensao: Optional[str] = None,
        mimetype: Optional[str] = None,
        subpasta: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Redireciona e salva o arquivo binário recebido via WhatsApp exclusivamente na pasta local Storage.

        Separa automaticamente em subpastas:
        - Imagens (.jpg, .jpeg, .png, etc.) -> Storage/imagem/
        - PDFs (.pdf) -> Storage/pdf/
        Aplica renomeação padronizada rastreável, operando 100% em disco local (sem envio para nuvem).
        """
        # Determina a subpasta por extensão ou mimetype caso não tenha sido especificada
        if subpasta is None:
            ext_limpa = (extensao or os.path.splitext(nome_original or "")[1] or "").lower()
            if not ext_limpa.startswith(".") and ext_limpa:
                ext_limpa = f".{ext_limpa}"

            mime = (mimetype or "").lower()

            if ext_limpa == ".pdf" or "pdf" in mime:
                subpasta = "pdf"
            elif ext_limpa in (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff") or "image" in mime:
                subpasta = "imagem"

        nome_renomeado = self.gerar_nome_arquivo_whatsapp(
            documento_id=documento_id,
            nome_original=nome_original,
            extensao=extensao,
        )

        destino_dir = self.local_storage_dir
        if subpasta:
            destino_dir = os.path.join(destino_dir, subpasta)
        os.makedirs(destino_dir, exist_ok=True)

        caminho_completo = os.path.join(destino_dir, nome_renomeado)

        with open(caminho_completo, "wb") as f:
            f.write(conteudo)

        return {
            "bucket": "local-storage",
            "caminho_local": caminho_completo,
            "caminho_relativo": os.path.relpath(caminho_completo, os.path.dirname(self.local_storage_dir)),
            "nome_arquivo": nome_renomeado,
            "diretorio": destino_dir,
            "tamanho_bytes": len(conteudo),
            "mimetype": mimetype or "application/octet-stream",
            "caminho_objeto": f"Storage/{nome_renomeado}",
            "status_backup": "sucesso_local",
        }

    def salvar_triagem_json(
        self,
        documento_id: str,
        dados_resultado: Dict[str, Any],
        is_urgente: bool = False,
        requer_auditoria: bool = False,
    ) -> Dict[str, str]:
        """Salva o JSON estruturado na pasta correspondente do Bucket OCI e em Storage local."""
        if requer_auditoria:
            prefixo = "auditoria_humana"
        elif is_urgente:
            prefixo = "processados/urgentes"
        else:
            prefixo = "processados/rotina"

        caminho_objeto = f"{prefixo}/{documento_id}.json"
        payload_bytes = json.dumps(dados_resultado, ensure_ascii=False, indent=2).encode("utf-8")

        # Persistência no Storage local
        try:
            pasta_local = os.path.join(self.local_storage_dir, prefixo)
            os.makedirs(pasta_local, exist_ok=True)
            caminho_arquivo_local = os.path.join(pasta_local, f"{documento_id}.json")
            with open(caminho_arquivo_local, "wb") as f:
                f.write(payload_bytes)
        except Exception as e:
            logger.warning(f"[Storage Warning] Falha ao gravar JSON local: {e}")

        # Se o cliente OCI estiver ativo, envia para a nuvem Oracle
        if self.client and settings.OCI_NAMESPACE:
            try:
                self.client.put_object(
                    namespace_name=settings.OCI_NAMESPACE,
                    bucket_name=self.bucket_name,
                    object_name=caminho_objeto,
                    put_object_body=payload_bytes,
                    content_type="application/json",
                )
                return {
                    "bucket": self.bucket_name,
                    "caminho_objeto": caminho_objeto,
                    "status_backup": "sucesso",
                }
            except Exception as e:
                logger.error(f"[OCI Storage Error] Falha no upload para nuvem: {e}")
                return {
                    "bucket": self.bucket_name,
                    "caminho_objeto": caminho_objeto,
                    "status_backup": f"falha: {str(e)}",
                }

        # Modo fallback local: simula o caminho OCI
        return {
            "bucket": self.bucket_name,
            "caminho_objeto": caminho_objeto,
            "status_backup": "sucesso (local_simulado)",
        }
