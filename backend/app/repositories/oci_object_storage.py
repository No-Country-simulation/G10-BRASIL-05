import os
from typing import Optional

from app.config.logger import logger
from app.config.settings import settings
from app.repositories.storage_errors import StoragePersistenceError


class OCIObjectStorageRepository:
    """Autenticação e operações de objetos remotos no OCI Object Storage."""

    def __init__(self):
        self.bucket_name = settings.OCI_BUCKET_NAME
        self.client = self._criar_cliente()

    @staticmethod
    def _criar_cliente():
        modo = settings.OCI_AUTH_MODE.strip().lower()

        if modo == "instance_principal":
            if not settings.OCI_NAMESPACE:
                raise StoragePersistenceError("OCI_NAMESPACE é obrigatório no modo Instance Principal.")
            try:
                import oci

                signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
                return oci.object_storage.ObjectStorageClient(
                    {"region": settings.OCI_REGION},
                    signer=signer,
                )
            except Exception as erro:
                raise StoragePersistenceError(
                    "Não foi possível autenticar o backend OCI como Instance Principal."
                ) from erro

        if modo != "api_key":
            raise ValueError("OCI_AUTH_MODE deve ser 'api_key' ou 'instance_principal'.")

        configuracao_iniciada = any((
            settings.OCI_USER_OCID,
            settings.OCI_TENANCY_OCID,
            settings.OCI_FINGERPRINT,
            settings.OCI_KEY_FILE,
            settings.OCI_NAMESPACE,
        ))
        if not configuracao_iniciada:
            raise StoragePersistenceError("Credenciais do OCI Object Storage não configuradas.")

        caminho_chave = os.path.expanduser(settings.OCI_KEY_FILE or "")
        obrigatorios = {
            "OCI_USER_OCID": settings.OCI_USER_OCID,
            "OCI_TENANCY_OCID": settings.OCI_TENANCY_OCID,
            "OCI_FINGERPRINT": settings.OCI_FINGERPRINT,
            "OCI_KEY_FILE": caminho_chave,
            "OCI_NAMESPACE": settings.OCI_NAMESPACE,
        }
        ausentes = [nome for nome, valor in obrigatorios.items() if not valor]
        if ausentes:
            raise StoragePersistenceError("Configuração OCI incompleta: " + ", ".join(ausentes))
        if not os.path.isfile(caminho_chave):
            raise StoragePersistenceError("O arquivo informado em OCI_KEY_FILE não existe.")

        try:
            import oci

            config = {
                "user": settings.OCI_USER_OCID,
                "key_file": caminho_chave,
                "fingerprint": settings.OCI_FINGERPRINT,
                "tenancy": settings.OCI_TENANCY_OCID,
                "region": settings.OCI_REGION,
            }
            return oci.object_storage.ObjectStorageClient(config)
        except Exception as erro:
            raise StoragePersistenceError("Falha ao inicializar autenticação OCI por API key.") from erro

    @property
    def ativo(self) -> bool:
        return self.client is not None

    def salvar(self, caminho: str, conteudo: bytes, content_type: str) -> None:
        try:
            self.client.put_object(
                namespace_name=settings.OCI_NAMESPACE,
                bucket_name=self.bucket_name,
                object_name=caminho,
                put_object_body=conteudo,
                content_type=content_type,
            )
        except Exception as erro:
            logger.exception("Falha ao enviar objeto para OCI: %s", caminho)
            raise StoragePersistenceError(f"Falha ao salvar objeto OCI '{caminho}'.") from erro

    def remover(self, caminho: Optional[str]) -> None:
        if not caminho:
            return
        try:
            self.client.delete_object(
                namespace_name=settings.OCI_NAMESPACE,
                bucket_name=self.bucket_name,
                object_name=caminho,
            )
        except Exception as erro:
            if getattr(erro, "status", None) == 404:
                return
            logger.exception("Falha na limpeza compensatória do objeto OCI %s", caminho)
            raise StoragePersistenceError(f"Falha ao remover objeto OCI durante rollback: '{caminho}'.") from erro

    def ler(self, caminho: str) -> bytes:
        try:
            resposta = self.client.get_object(
                namespace_name=settings.OCI_NAMESPACE,
                bucket_name=self.bucket_name,
                object_name=caminho,
            )
            return resposta.data.content
        except Exception as erro:
            if getattr(erro, "status", None) == 404:
                raise FileNotFoundError(f"Objeto não encontrado no bucket: {caminho}") from erro
            raise StoragePersistenceError(f"Falha ao ler objeto OCI '{caminho}'.") from erro
