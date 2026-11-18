import os
import json
from typing import Dict, Any
from app.repositories.storage import StorageRepository


class ArquivosOCIRepository(StorageRepository):
    """Upload do arquivo original e leitura de objetos no OCI Object Storage (SCRUM-72).

    Reaproveita a autenticação do StorageRepository sem alterá-lo.
    """

    def salvar_arquivo_original(
        self,
        documento_id: str,
        conteudo: bytes,
        nome_arquivo: str,
        content_type: str = "application/octet-stream",
    ) -> Dict[str, str]:
        """Salva a fonte localmente e no OCI, removendo cópias parciais em caso de falha."""
        resultado = super().salvar_arquivo_original(
            documento_id=documento_id,
            conteudo=conteudo,
            nome_original=nome_arquivo,
            extensao=os.path.splitext(nome_arquivo)[1].lower(),
            mimetype=content_type,
        )
        if not self.client:
            resultado["bucket"] = self.bucket_name
            resultado["status_backup"] = "sucesso (local_simulado)"
        return resultado

    def ler_arquivo(self, caminho_objeto: str) -> bytes:
        """Lê o conteúdo bruto de um objeto do Bucket OCI."""
        return self.oci_storage.ler(caminho_objeto)

    def ler_triagem_json(self, caminho_objeto: str) -> Dict[str, Any]:
        """Lê e decodifica um JSON de triagem salvo no Bucket OCI."""
        return json.loads(self.ler_arquivo(caminho_objeto).decode("utf-8"))
