"""Exceções específicas para a inicialização dos dados do sistema."""


class BootstrapAdminError(RuntimeError):
    """Erro de configuração ou conflito ao provisionar o administrador inicial."""
