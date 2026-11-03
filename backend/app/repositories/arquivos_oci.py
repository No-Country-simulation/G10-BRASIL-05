import os
import json
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.config.settings import settings
from app.repositories.storage import StorageRepository

logger = logging.getLogger(__name__)

# Pasta usada quando a OCI não está disponível (SCRUM-74). Fica em backend/storage_local/
PASTA_LOCAL_PADRAO = Path(__file__).resolve().parents[2] / "storage_local"

# Lista dos arquivos que caíram na pasta local por falha da OCI e ainda precisam subir
ARQUIVO_PENDENTES = "_pendentes_oci.json"


class ArquivosOCIRepository(StorageRepository):
    """Upload do arquivo original, leitura e roteamento de objetos no OCI Object Storage (SCRUM-72, 73, 74).

    Reaproveita a autenticação do StorageRepository sem alterá-lo.
    Sem credenciais OCI, ou se a OCI falhar, os arquivos são guardados em disco
    com a mesma estrutura de pastas do bucket.
    """

    def __init__(self, pasta_local: Optional[Path] = None):
        super().__init__()
        self.pasta_local = Path(pasta_local or PASTA_LOCAL_PADRAO).resolve()

    def _oci_ativo(self) -> bool:
        return bool(self.client and settings.OCI_NAMESPACE)

    def _retry(self):
        """Estratégia de nova tentativa do SDK para erros passageiros (rede, 429, 5xx)."""
        import oci
        return oci.retry.DEFAULT_RETRY_STRATEGY

    def _caminho_local(self, caminho_objeto: str) -> Path:
        """Converte o caminho do objeto em caminho no disco, sem deixar sair da pasta local."""
        caminho = (self.pasta_local / caminho_objeto).resolve()
        if not caminho.is_relative_to(self.pasta_local):
            raise ValueError(f"Caminho inválido: {caminho_objeto}")
        return caminho

    def _salvar_local(self, caminho_objeto: str, conteudo: bytes) -> None:
        caminho = self._caminho_local(caminho_objeto)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_bytes(conteudo)

    def _ler_pendentes(self) -> Dict[str, str]:
        """Retorna {caminho_objeto: content_type} dos arquivos que aguardam envio para a OCI."""
        arquivo = self.pasta_local / ARQUIVO_PENDENTES
        if not arquivo.exists():
            return {}
        return json.loads(arquivo.read_text(encoding="utf-8"))

    def _gravar_pendentes(self, pendentes: Dict[str, str]) -> None:
        self.pasta_local.mkdir(parents=True, exist_ok=True)
        (self.pasta_local / ARQUIVO_PENDENTES).write_text(
            json.dumps(pendentes, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _resposta(self, caminho_objeto: str, status: str) -> Dict[str, str]:
        return {
            "bucket": self.bucket_name,
            "caminho_objeto": caminho_objeto,
            "status_backup": status,
        }

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
        if self._oci_ativo():
            try:
                self.client.put_object(
                    namespace_name=settings.OCI_NAMESPACE,
                    bucket_name=self.bucket_name,
                    object_name=caminho_objeto,
                    put_object_body=conteudo,
                    content_type=content_type,
                    retry_strategy=self._retry(),
                )
                return self._resposta(caminho_objeto, "sucesso")
            except Exception as e:
                logger.error("Falha no upload para a OCI (%s): %s. Salvando localmente.", caminho_objeto, e)
                status_local = "falha_oci (salvo_local)"
        else:
            status_local = "sucesso (local)"

        # Modo local: guarda em disco para o documento não se perder
        try:
            self._salvar_local(caminho_objeto, conteudo)
            # Só o que caiu aqui por falha da OCI deve subir depois (não os arquivos de desenvolvimento)
            if status_local.startswith("falha_oci"):
                pendentes = self._ler_pendentes()
                pendentes[caminho_objeto] = content_type
                self._gravar_pendentes(pendentes)
            return self._resposta(caminho_objeto, status_local)
        except Exception as e:
            logger.error("Falha ao salvar localmente (%s): %s", caminho_objeto, e)
            return self._resposta(caminho_objeto, f"falha: {str(e)}")

    def ler_arquivo(self, caminho_objeto: str) -> bytes:
        """Lê o conteúdo bruto de um objeto do Bucket OCI ou, se não houver, da pasta local."""
        caminho_local = self._caminho_local(caminho_objeto)

        if self._oci_ativo():
            import oci
            try:
                resposta = self.client.get_object(
                    namespace_name=settings.OCI_NAMESPACE,
                    bucket_name=self.bucket_name,
                    object_name=caminho_objeto,
                    retry_strategy=self._retry(),
                )
                return resposta.data.content
            except oci.exceptions.ServiceError as e:
                # O arquivo pode ter sido salvo localmente numa falha anterior da OCI
                if not caminho_local.exists():
                    if e.status == 404:
                        raise FileNotFoundError(f"Objeto não encontrado no bucket: {caminho_objeto}") from e
                    raise
                logger.warning("Objeto %s indisponível na OCI (%s). Lendo da pasta local.", caminho_objeto, e.status)
            except Exception as e:
                if not caminho_local.exists():
                    raise
                logger.warning("Falha ao ler %s da OCI: %s. Lendo da pasta local.", caminho_objeto, e)

        if not caminho_local.exists():
            raise FileNotFoundError(f"Objeto não encontrado na pasta local: {caminho_objeto}")
        return caminho_local.read_bytes()

    def ler_triagem_json(self, caminho_objeto: str) -> Dict[str, Any]:
        """Lê e decodifica um JSON de triagem salvo no Bucket OCI."""
        return json.loads(self.ler_arquivo(caminho_objeto).decode("utf-8"))

    def mover_por_status(
        self,
        caminho_atual: str,
        is_urgente: bool = False,
        requer_auditoria: bool = False,
    ) -> Dict[str, str]:
        """Move o arquivo original de recebidos/ para a pasta do resultado da triagem (SCRUM-73).

        Usa a mesma prioridade do salvar_triagem_json: auditoria > urgente > rotina.
        """
        if requer_auditoria:
            prefixo = "auditoria_humana"
        elif is_urgente:
            prefixo = "processados/urgentes"
        else:
            prefixo = "processados/rotina"

        caminho_destino = f"{prefixo}/{os.path.basename(caminho_atual)}"
        origem_local = self._caminho_local(caminho_atual)
        erro = "arquivo não encontrado"

        # Se o cliente OCI estiver ativo, renomeia o objeto na nuvem Oracle (equivale a mover)
        if self._oci_ativo():
            import oci
            try:
                self.client.rename_object(
                    namespace_name=settings.OCI_NAMESPACE,
                    bucket_name=self.bucket_name,
                    rename_object_details=oci.object_storage.models.RenameObjectDetails(
                        source_name=caminho_atual,
                        new_name=caminho_destino,
                    ),
                    retry_strategy=self._retry(),
                )
                return self._resposta(caminho_destino, "sucesso")
            except Exception as e:
                erro = str(e)
                if origem_local.exists():
                    logger.warning("Falha ao mover %s na OCI: %s. Movendo na pasta local.", caminho_atual, e)
                else:
                    logger.error("Falha ao mover %s na OCI: %s", caminho_atual, e)

        # Modo local: move o arquivo dentro da pasta local
        if origem_local.exists():
            destino_local = self._caminho_local(caminho_destino)
            destino_local.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(origem_local), str(destino_local))
            # Se o arquivo aguardava envio, a pendência passa a apontar para o novo caminho
            pendentes = self._ler_pendentes()
            if caminho_atual in pendentes:
                pendentes[caminho_destino] = pendentes.pop(caminho_atual)
                self._gravar_pendentes(pendentes)
            return self._resposta(caminho_destino, "sucesso (local)")

        return self._resposta(caminho_atual, f"falha: {erro}")

    def sincronizar_pendentes(self) -> Dict[str, List[str]]:
        """Envia para a OCI os arquivos salvos localmente por falha e apaga a cópia local (SCRUM-74).

        O caminho na nuvem é o mesmo do disco, então o caminho_objeto guardado no banco continua válido.
        """
        pendentes = self._ler_pendentes()
        resultado: Dict[str, List[str]] = {"enviados": [], "falhas": []}

        if not pendentes:
            return resultado
        if not self._oci_ativo():
            logger.warning("OCI não configurada: %d arquivo(s) continuam pendentes.", len(pendentes))
            resultado["falhas"] = list(pendentes)
            return resultado

        for caminho_objeto, content_type in list(pendentes.items()):
            caminho_local = self._caminho_local(caminho_objeto)
            if not caminho_local.exists():
                logger.warning("Pendente %s não existe mais na pasta local. Removido da lista.", caminho_objeto)
                pendentes.pop(caminho_objeto)
                continue
            try:
                self.client.put_object(
                    namespace_name=settings.OCI_NAMESPACE,
                    bucket_name=self.bucket_name,
                    object_name=caminho_objeto,
                    put_object_body=caminho_local.read_bytes(),
                    content_type=content_type,
                    retry_strategy=self._retry(),
                )
            except Exception as e:
                logger.error("Falha ao sincronizar %s: %s", caminho_objeto, e)
                resultado["falhas"].append(caminho_objeto)
                continue
            caminho_local.unlink()
            pendentes.pop(caminho_objeto)
            resultado["enviados"].append(caminho_objeto)

        self._gravar_pendentes(pendentes)
        return resultado
