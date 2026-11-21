import os
import json
import re
import unicodedata
from datetime import datetime
from typing import Dict, Any, Optional

from app.config.settings import settings
from app.config.logger import logger
from app.repositories.local_file_storage import LocalFileStorageRepository
from app.repositories.oci_object_storage import OCIObjectStorageRepository
from app.repositories.storage_errors import StoragePersistenceError


class StorageRepository:
    """Repositório de armazenamento segregado no OCI Object Storage e pasta local Storage.

    Gerencia o salvamento dos documentos originais recebidos (via WhatsApp ou upload direto),
    renomeando-os com padronização rigorosa, e armazenando os JSONs de triagem.
    """

    def __init__(self, local_storage_dir: Optional[str] = None):
        self.bucket_name = settings.OCI_BUCKET_NAME
        self.local_storage = LocalFileStorageRepository(local_storage_dir)
        self.oci_storage = OCIObjectStorageRepository()
        self.local_storage_dir = self.local_storage.storage_dir

    @property
    def client(self):
        """Compatibilidade com consumidores que inspecionam ou substituem o cliente OCI."""
        return self.oci_storage.client

    @client.setter
    def client(self, valor):
        self.oci_storage.client = valor

    @property
    def oci_ativo(self) -> bool:
        return self.oci_storage.ativo

    def _salvar_local_atomico(self, caminho: str, conteudo: bytes) -> None:
        self.local_storage.salvar_atomico(caminho, conteudo)

    def _enviar_objeto_oci(self, caminho_objeto: str, conteudo: bytes, content_type: str) -> None:
        self.oci_storage.salvar(caminho_objeto, conteudo, content_type)

    def _excluir_objeto_oci(self, caminho_objeto: str) -> None:
        self.oci_storage.remover(caminho_objeto)

    def _remover_arquivo_local(self, caminho: Optional[str]) -> None:
        self.local_storage.remover(caminho)

    def _desfazer_persistencia_parcial(
        self,
        caminho_local: str,
        caminho_objeto: str,
        objeto_tentado: bool,
        artefato: str,
    ) -> None:
        try:
            self._remover_arquivo_local(caminho_local)
        except OSError:
            logger.exception("Falha ao remover cópia local durante rollback: %s", caminho_local)
        if objeto_tentado:
            try:
                self._excluir_objeto_oci(caminho_objeto)
            except StoragePersistenceError:
                logger.exception("Rollback remoto incompleto para %s", artefato)

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
        tipo_conteudo = mimetype or "application/octet-stream"
        caminho_objeto = self.gerar_caminho_objeto_original(
            documento_id=documento_id,
            extensao=extensao_limpa,
            mimetype=tipo_conteudo,
        )
        objeto_tentado = False

        try:
            self._salvar_local_atomico(caminho_local, conteudo)
            objeto_tentado = True
            self._enviar_objeto_oci(caminho_objeto, conteudo, tipo_conteudo)
        except Exception as erro:
            self._desfazer_persistencia_parcial(
                caminho_local, caminho_objeto, objeto_tentado, f"a fonte {documento_id}"
            )
            if isinstance(erro, StoragePersistenceError):
                raise
            raise StoragePersistenceError("Falha ao persistir documento original; operação desfeita.") from erro

        return {
            "bucket": self.bucket_name,
            "caminho_objeto": caminho_objeto,
            "caminho_objeto_fonte": caminho_objeto,
            "caminho_local": caminho_local,
            "caminho_relativo": os.path.relpath(caminho_local, os.path.dirname(self.local_storage_dir)),
            "nome_arquivo": nome_renomeado,
            "diretorio": destino_dir,
            "tamanho_bytes": len(conteudo),
            "mimetype": tipo_conteudo,
            "status_backup": "sucesso",
        }

    @staticmethod
    def gerar_caminho_objeto_original(
        documento_id: str,
        extensao: Optional[str],
        mimetype: Optional[str] = None,
    ) -> str:
        """Organiza originais no bucket por tipo: recebidos/pdf ou recebidos/imagens."""
        extensao_limpa = (extensao or "").lower()
        if extensao_limpa and not extensao_limpa.startswith("."):
            extensao_limpa = f".{extensao_limpa}"
        tipo_conteudo = (mimetype or "").split(";", 1)[0].strip().lower()
        extensoes_imagem = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".gif", ".bmp", ".tif", ".tiff", ".img"}

        if extensao_limpa == ".pdf" or tipo_conteudo == "application/pdf":
            pasta = "pdf"
        elif tipo_conteudo.startswith("image/") or extensao_limpa in extensoes_imagem:
            pasta = "imagens"
        else:
            # Mantém compatibilidade para tipos que não sejam PDF nem imagem.
            pasta = None

        nome_objeto = f"{documento_id}{extensao_limpa or '.bin'}"
        if pasta:
            return f"recebidos/{pasta}/{nome_objeto}"
        return f"recebidos/{nome_objeto}"

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
        objeto_tentado = False
        try:
            self._salvar_local_atomico(caminho_local, payload_bytes)
            objeto_tentado = True
            self._enviar_objeto_oci(caminho_objeto, payload_bytes, "application/json")
        except Exception as erro:
            self._desfazer_persistencia_parcial(
                caminho_local, caminho_objeto, objeto_tentado, f"JSON de triagem {documento_id}"
            )
            if isinstance(erro, StoragePersistenceError):
                raise
            raise StoragePersistenceError("Falha ao persistir JSON da triagem; operação desfeita.") from erro

        return {
            "bucket": self.bucket_name,
            "caminho_objeto": caminho_objeto,
            "caminho_local": caminho_local,
            "status_backup": "sucesso",
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
                raise

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
                raise
