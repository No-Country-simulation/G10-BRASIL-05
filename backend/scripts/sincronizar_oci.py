"""Envia para a OCI os arquivos que ficaram em storage_local/ por falha da nuvem (SCRUM-74).

Rodar de dentro da pasta backend/, depois que a OCI voltar:
    python scripts/sincronizar_oci.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.repositories.arquivos_oci import ArquivosOCIRepository  # noqa: E402

resultado = ArquivosOCIRepository().sincronizar_pendentes()

print(f"Enviados: {len(resultado['enviados'])}")
for caminho in resultado["enviados"]:
    print(f"  - {caminho}")
print(f"Ainda pendentes: {len(resultado['falhas'])}")
for caminho in resultado["falhas"]:
    print(f"  - {caminho}")

sys.exit(1 if resultado["falhas"] else 0)
