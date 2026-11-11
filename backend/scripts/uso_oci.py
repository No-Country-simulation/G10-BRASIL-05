"""Mostra o uso do bucket contra o limite do Always Free (SCRUM-75).

Rodar de dentro da pasta backend/:
    python scripts/uso_oci.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Limite gratuito do Object Storage (Standard + Infrequent Access + Archive somados)
LIMITE_ALWAYS_FREE_BYTES = 20 * 1024 ** 3
PERCENTUAL_ALERTA = 80


def resumo_uso(tamanho_bytes: int, objetos: int, limite_bytes: int = LIMITE_ALWAYS_FREE_BYTES) -> dict:
    """Calcula o percentual usado e se já passou do limite de alerta."""
    percentual = tamanho_bytes / limite_bytes * 100
    return {
        "objetos": objetos,
        "tamanho_mb": round(tamanho_bytes / 1024 ** 2, 2),
        "limite_gb": round(limite_bytes / 1024 ** 3, 2),
        "percentual": round(percentual, 2),
        "alerta": percentual >= PERCENTUAL_ALERTA,
    }


def main() -> int:
    from app.config.settings import settings
    from app.repositories.storage import StorageRepository

    repo = StorageRepository()
    if repo.client is None or not settings.OCI_NAMESPACE:
        print("❌ OCI não configurada. Confira o backend/.env.")
        return 2

    bucket = repo.client.get_bucket(
        namespace_name=settings.OCI_NAMESPACE,
        bucket_name=repo.bucket_name,
        fields=["approximateSize", "approximateCount"],
    ).data
    uso = resumo_uso(bucket.approximate_size or 0, bucket.approximate_count or 0)

    print(f"Bucket:  {repo.bucket_name}")
    print(f"Objetos: {uso['objetos']}")
    print(f"Tamanho: {uso['tamanho_mb']} MB de {uso['limite_gb']} GB ({uso['percentual']}%)")
    if uso["alerta"]:
        print(f"⚠️  Acima de {PERCENTUAL_ALERTA}% do limite gratuito. Avise o time e limpe arquivos de teste.")
        return 1
    print("✅ Dentro do Always Free")
    return 0


if __name__ == "__main__":
    sys.exit(main())
