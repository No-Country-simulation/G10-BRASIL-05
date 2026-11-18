import os
import json
import re
import unicodedata
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import uuid4

from app.config.settings import settings
from app.config.logger import logger


class StoragePersistenceError(RuntimeError):
    """Falha crítica ao persistir um artefato local ou remoto."""


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
        """Inicializa autenticação local por API key ou Instance Principal na OCI."""
        modo = (settings.OCI_AUTH_MODE or "api_key").strip().lower()
        if modo == "instance_principal":
            try:
                import oci

                signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
                self.client = oci.object_storage.ObjectStorageClient(
                    {"region": settings.OCI_REGION},
                    signer=signer,
                )
                return
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
            return

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
            raise StoragePersistenceError(
                "Configuração OCI incompleta: " + ", ".join(ausentes)
            )
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
            self.client = oci.object_storage.ObjectStorageClient(config)
        except Exception as erro:
            raise StoragePersistenceError("Falha ao inicializar a autenticação OCI por API key.") from erro

    @property
    def oci_ativo(self) -> bool:
        return self.client is not None

    def _salvar_local_atomico(self, caminho: str, conteudo: bytes) -> None:
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        temporario = f"{caminho}.tmp-{uuid4().hex}"
        try:
            with open(temporario, "wb") as arquivo:
                arquivo.write(conteudo)
                arquivo.flush()
                os.fsync(arquivo.fileno())
            os.replace(temporario, caminho)
        finally:
            if os.path.exists(temporario):
                os.remove(temporario)

    def _enviar_objeto_oci(self, caminho_objeto: str, conteudo: bytes, content_type: str) -> None:
        if not self.client:
            return
        try:
            self.client.put_object(
                namespace_name=settings.OCI_NAMESPACE,
                bucket_name=self.bucket_name,
                object_name=caminho_objeto,
                put_object_body=conteudo,
                content_type=content_type,
            )
        except Exception as erro:
            logger.exception("Falha ao enviar objeto para OCI: %s", caminho_objeto)
            raise StoragePersistenceError(f"Falha ao salvar objeto OCI '{caminho_objeto}'.") from erro

    def _excluir_objeto_oci(self, caminho_objeto: str) -> None:
        if not self.client or not caminho_objeto:
            return
        try:
            self.client.delete_object(
                namespace_name=settings.OCI_NAMESPACE,
                bucket_name=self.bucket_name,
                object_name=caminho_objeto,
            )
        except Exception as erro:
            logger.exception("Falha na limpeza compensatória do objeto OCI %s", caminho_objeto)
            raise StoragePersistenceError(
                f"Falha ao remover objeto OCI durante rollback: '{caminho_objeto}'."
            ) from erro

    @staticmethod
    def _remover_arquivo_local(caminho: Optional[str]) -> None:
        if caminho and os.path.isfile(caminho):
            os.remove(caminho)

    def salvar_arquivo_original(
        self,
        documento_id: str,
        conteudo: bytes,
        nome_original: Optional[str] = None,
        extensao: Optional[str] = None,
        mimetype: Optional[str] = None,
        subpasta: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Salva fonte localmente e, quando configurado, no prefixo recebidos/ do OCI.

        Uma falha em qualquer destino remove o artefato já gravado no outro destino.
        """
        extensao_limpa = (extensao or os.path.splitext(nome_original or "")[1] or "").lower()
        if extensao_limpa and not extensao_limpa.startswith("."):
            extensao_limpa = f".{extensao_limpa}"
        nome_renomeado = self.gerar_nome_arquivo_whatsapp(
            documento_id=documento_id,
            nome_original=nome_original,
            extensao=extensao_limpa or None,
        )
        if subpasta is None:
            subpasta = "pdf" if extensao_limpa == ".pdf" else "imagem" if (mimetype or "").startswith("image/") else None
        destino_dir = os.path.join(self.local_storage_dir, subpasta) if subpasta else self.local_storage_dir
        caminho_local = os.path.join(destino_dir, nome_renomeado)
        caminho_objeto = f"recebidos/{documento_id}{extensao_limpa or '.bin'}"
        tipo_conteudo = mimetype or "application/octet-stream"

        try:
            self._salvar_local_atomico(caminho_local, conteudo)
            if self.client:
                self._enviar_objeto_oci(caminho_objeto, conteudo, tipo_conteudo)
        except Exception:
            try:
                self._remover_arquivo_local(caminho_local)
            except OSError:
                logger.exception("Falha ao remover cópia local durante rollback: %s", caminho_local)
            if self.client:
                try:
                    self._excluir_objeto_oci(caminho_objeto)
                except StoragePersistenceError:
                    pass
            raise

        return {
            "bucket": self.bucket_name if self.client else "local-storage",
            "caminho_objeto": caminho_objeto,
            "caminho_objeto_fonte": caminho_objeto if self.client else None,
            "caminho_local": caminho_local,
            "caminho_relativo": os.path.relpath(caminho_local, os.path.dirname(self.local_storage_dir)),
            "nome_arquivo": nome_renomeado,
            "diretorio": destino_dir,
            "tamanho_bytes": len(conteudo),
            "mimetype": tipo_conteudo,
            "status_backup": "sucesso" if self.client else "sucesso_local",
        }

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
        """Compatibilidade para o fluxo WhatsApp, agora com upload OCI quando configurado."""
        return self.salvar_arquivo_original(
            documento_id=documento_id,
            conteudo=conteudo,
            nome_original=nome_original,
            extensao=extensao,
            mimetype=mimetype,
            subpasta=subpasta,
        )

    def salvar_triagem_json(
        self,
        documento_id: str,
        dados_resultado: Dict[str, Any],
        is_urgente: bool = False,
        requer_auditoria: bool = False,
    ) -> Dict[str, str]:
        """Salva o JSON estruturado e desfaz cópias parciais se algum destino falhar."""
        if requer_auditoria:
            prefixo = "auditoria_humana"
        elif is_urgente:
            prefixo = "processados/urgentes"
        else:
            prefixo = "processados/rotina"

        caminho_objeto = f"{prefixo}/{documento_id}.json"
        payload_bytes = json.dumps(dados_resultado, ensure_ascii=False, indent=2).encode("utf-8")

        caminho_local = os.path.join(self.local_storage_dir, prefixo, f"{documento_id}.json")
        try:
            self._salvar_local_atomico(caminho_local, payload_bytes)
            if self.client:
                self._enviar_objeto_oci(caminho_objeto, payload_bytes, "application/json")
        except Exception:
            try:
                self._remover_arquivo_local(caminho_local)
            except OSError:
                logger.exception("Falha ao remover JSON local durante rollback: %s", caminho_local)
            if self.client:
                try:
                    self._excluir_objeto_oci(caminho_objeto)
                except StoragePersistenceError:
                    pass
            raise

        return {
            "bucket": self.bucket_name if self.client else "local-storage",
            "caminho_objeto": caminho_objeto,
            "caminho_local": caminho_local,
            "status_backup": "sucesso" if self.client else "sucesso (local_simulado)",
        }

    def excluir_artefatos_triagem(
        self,
        documento_id: str,
        caminho_fonte: Optional[str] = None,
        caminho_objeto: Optional[str] = None,
        caminhos_objetos: Optional[list[str]] = None,
    ) -> None:
        """Apaga fonte e artefatos da triagem após confirmação humana de conteúdo fora de escopo."""
        raiz = os.path.realpath(self.local_storage_dir)
        candidatos = [
            os.path.join(raiz, "auditoria_humana", f"{documento_id}.json"),
            os.path.join(raiz, "processados", "urgentes", f"{documento_id}.json"),
            os.path.join(raiz, "processados", "rotina", f"{documento_id}.json"),
        ]
        if caminho_fonte:
            fonte = os.path.realpath(caminho_fonte)
            if os.path.commonpath([raiz, fonte]) == raiz:
                candidatos.append(fonte)
        for candidato in candidatos:
            try:
                if os.path.isfile(candidato):
                    os.remove(candidato)
            except OSError as erro:
                logger.warning(f"Falha ao remover artefato local de documento fora de escopo: {erro}")

        objetos = set(caminhos_objetos or [])
        if caminho_objeto:
            objetos.add(caminho_objeto)
        for objeto in objetos:
            try:
                self._excluir_objeto_oci(objeto)
            except StoragePersistenceError:
                continue

    def rollback_tentativa(
        self,
        caminho_fonte: Optional[str] = None,
        objetos_oci: Optional[list[str]] = None,
        caminho_json_local: Optional[str] = None,
    ) -> None:
        """Remove somente os artefatos criados pela tentativa atual."""
        for caminho in (caminho_fonte, caminho_json_local):
            try:
                self._remover_arquivo_local(caminho)
            except OSError:
                logger.exception("Falha ao remover artefato local durante rollback: %s", caminho)
        for objeto in set(objetos_oci or []):
            try:
                self._excluir_objeto_oci(objeto)
            except StoragePersistenceError:
                continue
