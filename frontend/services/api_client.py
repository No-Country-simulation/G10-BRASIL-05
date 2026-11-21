"""Compatibilidade: a fachada HTTP está no pacote api."""
import sys
import api as _implementacao
sys.modules[__name__] = _implementacao
