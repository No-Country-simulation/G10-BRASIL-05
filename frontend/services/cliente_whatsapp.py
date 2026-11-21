"""Compatibilidade: use api.cliente_whatsapp para chamadas HTTP."""
import sys
from api import cliente_whatsapp as _implementacao
sys.modules[__name__] = _implementacao
