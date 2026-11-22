import secrets

from fastapi import HTTPException

from app.models.users import UsuarioSistemaModel
from app.repositories.medicos_repository import MedicosRepository
from app.repositories.users_repository import UsersRepository
from app.schemas.auth import UsuarioProvisionarRequest
from app.services.autenticacao import gerar_hash_senha, usuario_publico
from app.utils.validadores import REGEX_COREN, REGEX_CRM, UFS_BRASIL


class MedicosService:
    """Regras de negócio e provisionamento de profissionais de saúde."""

    def __init__(self, users_repo: UsersRepository, medicos_repo: MedicosRepository):
        self.users_repo = users_repo
        self.medicos_repo = medicos_repo

    @staticmethod
    def _extrair_crm_uf(registro: str | None) -> tuple[str, str]:
        if not registro or not registro.strip():
            return (f"CRM-{secrets.token_hex(4).upper()}", "SP")
        texto = registro.strip()
        match = REGEX_CRM.match(texto)
        if match:
            uf = (match.group("uf1") or match.group("uf2") or "SP").upper()
            num = match.group("num")
            return (num, uf)
        texto_up = texto.upper()
        for sep in ("-", "/"):
            if sep in texto_up:
                partes = texto_up.rsplit(sep, 1)
                num = partes[0].replace("CRM", "").strip(" /.-")
                uf = partes[1].strip()
                if uf in UFS_BRASIL:
                    return (num, uf)
        num = texto_up.replace("CRM", "").strip(" /.-")
        return (num or f"CRM-{secrets.token_hex(4).upper()}", "SP")

    @staticmethod
    def _extrair_coren_uf(registro: str | None) -> tuple[str, str]:
        if not registro or not registro.strip():
            return (f"COREN-{secrets.token_hex(4).upper()}", "SP")
        texto = registro.strip()
        match = REGEX_COREN.match(texto)
        if match:
            uf = (match.group("uf1") or match.group("uf2") or "SP").upper()
            num = match.group("num")
            return (num, uf)
        texto_up = texto.upper()
        for sep in ("-", "/"):
            if sep in texto_up:
                partes = texto_up.rsplit(sep, 1)
                num = partes[0].replace("COREN", "").strip(" /.-")
                uf = partes[1].strip()
                if uf in UFS_BRASIL:
                    return (num, uf)
        num = texto_up.replace("COREN", "").strip(" /.-")
        return (num or f"COREN-{secrets.token_hex(4).upper()}", "SP")

    def provisionar_profissional(
        self, payload: UsuarioProvisionarRequest, ator: UsuarioSistemaModel
    ) -> dict:
        if ator.papel == "MEDICO" and payload.nivel != "ENFERMEIRO":
            raise HTTPException(status_code=403, detail="Médicos podem provisionar somente enfermeiros.")
        if ator.papel == "DIRETOR" and payload.nivel not in {"MEDICO", "ENFERMEIRO"}:
            raise HTTPException(status_code=403, detail="Diretores podem provisionar somente médicos e enfermeiros.")

        if self.users_repo.buscar_por_email(payload.email):
            raise HTTPException(status_code=409, detail="Já existe uma conta com esse e-mail.")

        medico_id = None
        enfermeiro_id = None

        if payload.nivel == "MEDICO":
            crm, uf = self._extrair_crm_uf(payload.registro)
            if payload.registro and payload.registro.strip():
                existente = self.medicos_repo.buscar_por_crm_uf(crm, uf)
                if existente:
                    raise HTTPException(status_code=409, detail="Já existe um médico cadastrado com este CRM/UF.")
            medico = self.medicos_repo.criar_medico(
                nome=payload.nome.strip(),
                crm=crm,
                uf=uf,
                especialidade=payload.especialidade.strip() if payload.especialidade else None,
            )
            medico_id = medico.id

        elif payload.nivel == "ENFERMEIRO":
            coren, uf = self._extrair_coren_uf(payload.registro)
            if payload.registro and payload.registro.strip():
                existente = self.medicos_repo.buscar_enfermeiro_por_coren_uf(coren, uf)
                if existente:
                    raise HTTPException(status_code=409, detail="Já existe um enfermeiro cadastrado com este COREN/UF.")
            enfermeiro = self.medicos_repo.criar_enfermeiro(
                nome=payload.nome.strip(),
                coren=coren,
                uf=uf,
                area_atuacao=payload.especialidade.strip() if payload.especialidade else None,
            )
            enfermeiro_id = enfermeiro.id

        novo = self.users_repo.criar_usuario(
            email=payload.email,
            nome=payload.nome.strip(),
            senha_hash=gerar_hash_senha(payload.senha),
            papel=payload.nivel,
            trocar_senha_obrigatorio=bool(payload.trocar_senha_obrigatorio),
            registro=payload.registro.strip() if payload.registro else None,
            especialidade=payload.especialidade.strip() if payload.especialidade else None,
            medico_id=medico_id,
            enfermeiro_id=enfermeiro_id,
            ativo=True,
            pode_gerenciar_whatsapp=False,
        )

        if ator.papel == "DIRETOR":
            from app.models.clinico import (
                EstabelecimentoEnfermeiroModel,
                EstabelecimentoProfissionalModel,
                HospitalDiretorModel,
            )
            vinculo = (
                self.users_repo.db.query(HospitalDiretorModel.hospital_id)
                .filter(HospitalDiretorModel.usuario_id == ator.id, HospitalDiretorModel.fim_vinculo.is_(None))
                .first()
            )
            if vinculo and vinculo[0]:
                hosp_id = vinculo[0]
                if medico_id:
                    self.users_repo.db.add(EstabelecimentoProfissionalModel(estabelecimento_id=hosp_id, medico_id=medico_id))
                    self.users_repo.db.commit()
                elif enfermeiro_id:
                    self.users_repo.db.add(EstabelecimentoEnfermeiroModel(estabelecimento_id=hosp_id, enfermeiro_id=enfermeiro_id))
                    self.users_repo.db.commit()

        return usuario_publico(novo)
