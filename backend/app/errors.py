class DependencyUnavailableError(RuntimeError):
    """Serviço externo necessário ao fluxo indisponível."""


class QueueUnavailableError(DependencyUnavailableError):
    """Fila Redis ou RQ indisponível."""
