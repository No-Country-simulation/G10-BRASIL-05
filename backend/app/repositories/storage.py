import os
import json
from typing import Dict, Any, Optional
from app.config.settings import settings


class StorageRepository:
    """Repositório de armazenamento segregado no OCI Object Storage (Always Free).

    Inclui fallback local para execução de desenvolvimento sem quebrar a API.
    """

    def __init__(self):
        self.bucket_name = settings.OCI_BUCKET_NAME
        self.client = None
        self._inicializar_cliente_oci()

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
                # Loga o erro sem interromper o serviço em desenvolvimento local
                print(f"[OCI Storage Warning] Falha ao inicializar SDK OCI: {e}. Usando modo simulado.")
                self.client = None

    def salvar_triagem_json(
        self,
        documento_id: str,
        dados_resultado: Dict[str, Any],
        is_urgente: bool = False,
        requer_auditoria: bool = False,
    ) -> Dict[str, str]:
        """Salva o JSON estruturado na pasta correspondente do Bucket OCI."""
        if requer_auditoria:
            prefixo = "auditoria_humana"
        elif is_urgente:
            prefixo = "processados/urgentes"
        else:
            prefixo = "processados/rotina"

        caminho_objeto = f"{prefixo}/{documento_id}.json"
        payload_bytes = json.dumps(dados_resultado, ensure_ascii=False, indent=2).encode("utf-8")

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
                print(f"[OCI Storage Error] Falha no upload para nuvem: {e}")
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
