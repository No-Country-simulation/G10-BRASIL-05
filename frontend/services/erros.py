class ErroDeApi(Exception):
    pass


class ErroDeConfiguracao(ErroDeApi):
    """Configuração inválida que impede conectar o frontend aos serviços necessários."""
