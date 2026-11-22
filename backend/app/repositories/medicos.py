"""Re-exporta MedicosRepository para compatibilidade retroativa."""

from app.repositories.medicos_repository import MedicosRepository

__all__ = ["MedicosRepository"]
