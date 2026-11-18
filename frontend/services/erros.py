class ErroDeApi(Exception):
    pass


class ErroDeConfiguracao(ErroDeApi):
    """Configuração inválida que impede escolher com segurança a API ou o mock."""
