"""Compatibilidade: use api.cliente_http para chamadas HTTP."""
import sys
from api import cliente_http as _implementacao
sys.modules[__name__] = _implementacao
