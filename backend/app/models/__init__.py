"""Módulo de modelos SQLAlchemy do MediFlow.

Re-exporta todos os modelos relacionais das divisões modulares:
- base: Base declarativa compartilhada
- users: Modelos de autenticação e usuários do sistema
- clinico: Modelos cadastrais e clínicos (hospitais, médicos, enfermeiros, pacientes)
- triagem: Modelos de triagem, atendimentos, documentos, roteamentos e auditoria
"""

from app.models.base import Base
from app.models.users import UsuarioSistemaModel
from app.models.clinico import (
    CidadeModel,
    CategoriaHospitalModel,
    EstabelecimentoSaudeModel,
    HospitalModel,
    ClinicaModel,
    EspecialidadeModel,
    MedicoModel,
    EnfermeiroModel,
    PacienteModel,
    medico_especialidades,
    EstabelecimentoProfissionalModel,
    EstabelecimentoEnfermeiroModel,
    HospitalDiretorModel,
)
from app.models.triagem import (
    AtendimentoModel,
    AtendimentoProfissionalModel,
    AtendimentoEnfermeiroModel,
    DestinoRoteamentoModel,
    DocumentoTriagemModel,
    DocumentoEspecialidadeModel,
    DocumentoArquivoModel,
    ArquivoMovimentacaoModel,
    RevisaoModel,
    ContatoWhatsAppModel,
    InstanciaWhatsAppModel,
    DocumentoOrigemWhatsAppModel,
    EncaminhamentoModel,
    AuditoriaOutboxModel,
)

__all__ = [
    # Base
    "Base",
    # Users
    "UsuarioSistemaModel",
    # Clinico
    "CidadeModel",
    "CategoriaHospitalModel",
    "EstabelecimentoSaudeModel",
    "HospitalModel",
    "ClinicaModel",
    "EspecialidadeModel",
    "MedicoModel",
    "EnfermeiroModel",
    "PacienteModel",
    "medico_especialidades",
    "EstabelecimentoProfissionalModel",
    "EstabelecimentoEnfermeiroModel",
    "HospitalDiretorModel",
    # Triagem
    "AtendimentoModel",
    "AtendimentoProfissionalModel",
    "AtendimentoEnfermeiroModel",
    "DestinoRoteamentoModel",
    "DocumentoTriagemModel",
    "DocumentoEspecialidadeModel",
    "DocumentoArquivoModel",
    "ArquivoMovimentacaoModel",
    "RevisaoModel",
    "ContatoWhatsAppModel",
    "InstanciaWhatsAppModel",
    "DocumentoOrigemWhatsAppModel",
    "EncaminhamentoModel",
    "AuditoriaOutboxModel",
]
