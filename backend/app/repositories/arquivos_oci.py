import os
import json
from typing import Dict, Any
from app.config.settings import settings
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
        """Salva o arquivo original recebido (PDF, imagem, texto) na pasta recebidos/ do Bucket OCI."""
        extensao = os.path.splitext(nome_arquivo)[1].lower()
        caminho_objeto = f"recebidos/{documento_id}{extensao}"

        # Se o cliente OCI estiver ativo, envia para a nuvem Oracle
        if self.client and settings.OCI_NAMESPACE:
            try:
                self.client.put_object(
                    namespace_name=settings.OCI_NAMESPACE,
                    bucket_name=self.bucket_name,
                    object_name=caminho_objeto,
                    put_object_body=conteudo,
                    content_type=content_type,
                )
                return {
                    "bucket": self.bucket_name,
                    "caminho_objeto": caminho_objeto,
                    "status_backup": "sucesso",
                }
            except Exception as e:
                print(f"[OCI Storage Error] Falha no upload do arquivo original: {e}")
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

    def ler_arquivo(self, caminho_objeto: str) -> bytes:
        """Lê o conteúdo bruto de um objeto do Bucket OCI."""
        if not (self.client and settings.OCI_NAMESPACE):
            raise RuntimeError("OCI Object Storage não configurado: leitura indisponível no modo simulado.")

        import oci
        try:
            resposta = self.client.get_object(
                namespace_name=settings.OCI_NAMESPACE,
                bucket_name=self.bucket_name,
                object_name=caminho_objeto,
            )
        except oci.exceptions.ServiceError as e:
            if e.status == 404:
                raise FileNotFoundError(f"Objeto não encontrado no bucket: {caminho_objeto}") from e
            raise
        return resposta.data.content

    def ler_triagem_json(self, caminho_objeto: str) -> Dict[str, Any]:
        """Lê e decodifica um JSON de triagem salvo no Bucket OCI."""
        return json.loads(self.ler_arquivo(caminho_objeto).decode("utf-8"))
