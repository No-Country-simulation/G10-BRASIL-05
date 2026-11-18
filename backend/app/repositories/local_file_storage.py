import os
from pathlib import Path
from typing import Optional
from uuid import uuid4


class LocalFileStorageRepository:
    """Responsável somente pela leitura, gravação atômica e remoção no disco local."""

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = storage_dir or self._obter_diretorio_padrao()
        os.makedirs(self.storage_dir, exist_ok=True)

    @staticmethod
    def _obter_diretorio_padrao() -> str:
        candidatos = [
            os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../Storage")),
            os.path.abspath("Storage"),
            os.path.abspath("../Storage"),
        ]
        for caminho in candidatos:
            if os.path.exists(caminho):
                return caminho
        return candidatos[0]

    def salvar_atomico(self, caminho: str, conteudo: bytes) -> None:
        destino = Path(caminho)
        destino.parent.mkdir(parents=True, exist_ok=True)
        temporario = destino.with_name(f"{destino.name}.tmp-{uuid4().hex}")
        try:
            with temporario.open("wb") as arquivo:
                arquivo.write(conteudo)
                arquivo.flush()
                os.fsync(arquivo.fileno())
            os.replace(temporario, destino)
        finally:
            if temporario.exists():
                temporario.unlink()

    @staticmethod
    def remover(caminho: Optional[str]) -> None:
        if caminho and os.path.isfile(caminho):
            os.remove(caminho)
