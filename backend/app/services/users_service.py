from typing import List

from fastapi import HTTPException

from app.models.users import UsuarioSistemaModel
from app.repositories.users_repository import UsersRepository
from app.schemas.auth import UsuarioAtualizarRequest
from app.services.autenticacao import gerar_hash_senha, usuario_publico


class UsersService:
    """Regras de negócio e operações para gestão de usuários do sistema."""

    def __init__(self, users_repo: UsersRepository):
        self.users_repo = users_repo

    def listar_usuarios(self, ator: UsuarioSistemaModel) -> List[dict]:
        if ator.papel == "MEDICO":
            usuarios = self.users_repo.listar_ativos(papel="ENFERMEIRO")
        elif ator.papel == "DIRETOR":
            from app.models.clinico import (
                EstabelecimentoEnfermeiroModel,
                EstabelecimentoProfissionalModel,
                HospitalDiretorModel,
            )
            vinculos = (
                self.users_repo.db.query(HospitalDiretorModel.hospital_id)
                .filter(HospitalDiretorModel.usuario_id == ator.id, HospitalDiretorModel.fim_vinculo.is_(None))
                .all()
            )
            hospital_ids = [v[0] for v in vinculos if v[0] is not None]
            if hospital_ids:
                medicos_ids = {
                    m[0]
                    for m in self.users_repo.db.query(EstabelecimentoProfissionalModel.medico_id)
                    .filter(
                        EstabelecimentoProfissionalModel.estabelecimento_id.in_(hospital_ids),
                        EstabelecimentoProfissionalModel.fim_vinculo.is_(None),
                    )
                    .all()
                }
                enfermeiros_ids = {
                    e[0]
                    for e in self.users_repo.db.query(EstabelecimentoEnfermeiroModel.enfermeiro_id)
                    .filter(
                        EstabelecimentoEnfermeiroModel.estabelecimento_id.in_(hospital_ids),
                        EstabelecimentoEnfermeiroModel.fim_vinculo.is_(None),
                    )
                    .all()
                }
                todos = self.users_repo.listar_ativos(papeis=["DIRETOR", "MEDICO", "ENFERMEIRO"])
                usuarios = [
                    u
                    for u in todos
                    if u.id == ator.id
                    or (u.papel == "MEDICO" and u.medico_id in medicos_ids)
                    or (u.papel == "ENFERMEIRO" and u.enfermeiro_id in enfermeiros_ids)
                ]
            else:
                todos = self.users_repo.listar_ativos(papeis=["DIRETOR", "MEDICO", "ENFERMEIRO"])
                usuarios = [u for u in todos if u.id == ator.id or u.papel in {"MEDICO", "ENFERMEIRO"}]
        else:
            usuarios = self.users_repo.listar_ativos(papeis=["DIRETOR", "MEDICO", "ENFERMEIRO"])
        return [usuario_publico(item) for item in usuarios]

    def desativar_usuario(self, usuario_id: int, ator: UsuarioSistemaModel) -> None:
        alvo = self.users_repo.buscar_por_id(usuario_id)
        if not alvo or alvo.papel == "INSTITUCIONAL_WHATSAPP":
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        if alvo.papel == "ADMIN_GERAL" and ator.papel != "ADMIN_GERAL":
            raise HTTPException(status_code=403, detail="Somente o Administrador Geral pode gerenciar esse perfil.")
        if ator.id == alvo.id:
            raise HTTPException(status_code=400, detail="Não é possível desativar a própria conta.")
        if ator.papel == "MEDICO" and alvo.papel != "ENFERMEIRO":
            raise HTTPException(status_code=403, detail="Médicos podem gerenciar somente enfermeiros.")
        if ator.papel == "DIRETOR":
            if alvo.papel in {"ADMIN_GERAL", "DIRETOR"}:
                raise HTTPException(status_code=403, detail="Diretores não podem gerenciar outros diretores ou administradores.")
            from app.models.clinico import (
                EstabelecimentoEnfermeiroModel,
                EstabelecimentoProfissionalModel,
                HospitalDiretorModel,
            )
            vinculos = (
                self.users_repo.db.query(HospitalDiretorModel.hospital_id)
                .filter(HospitalDiretorModel.usuario_id == ator.id, HospitalDiretorModel.fim_vinculo.is_(None))
                .all()
            )
            hospital_ids = [v[0] for v in vinculos if v[0] is not None]
            if hospital_ids:
                medicos_ids = {
                    m[0]
                    for m in self.users_repo.db.query(EstabelecimentoProfissionalModel.medico_id)
                    .filter(
                        EstabelecimentoProfissionalModel.estabelecimento_id.in_(hospital_ids),
                        EstabelecimentoProfissionalModel.fim_vinculo.is_(None),
                    )
                    .all()
                }
                enfermeiros_ids = {
                    e[0]
                    for e in self.users_repo.db.query(EstabelecimentoEnfermeiroModel.enfermeiro_id)
                    .filter(
                        EstabelecimentoEnfermeiroModel.estabelecimento_id.in_(hospital_ids),
                        EstabelecimentoEnfermeiroModel.fim_vinculo.is_(None),
                    )
                    .all()
                }
                if (alvo.papel == "MEDICO" and alvo.medico_id not in medicos_ids) or (
                    alvo.papel == "ENFERMEIRO" and alvo.enfermeiro_id not in enfermeiros_ids
                ):
                    raise HTTPException(status_code=403, detail="Você só pode gerenciar usuários vinculados ao seu hospital.")
        if alvo.papel == "DIRETOR":
            diretores_ativos = self.users_repo.contar_diretores_ativos()
            if diretores_ativos <= 1:
                raise HTTPException(status_code=409, detail="É necessário manter ao menos um diretor ativo.")
        self.users_repo.remover_ou_desativar(alvo.id)

    def atualizar_usuario(
        self, usuario_id: int, dados: UsuarioAtualizarRequest, ator: UsuarioSistemaModel
    ) -> dict:
        alvo = self.users_repo.buscar_por_id(usuario_id)
        if not alvo or alvo.papel == "INSTITUCIONAL_WHATSAPP":
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        if alvo.papel == "ADMIN_GERAL" and ator.papel != "ADMIN_GERAL":
            raise HTTPException(status_code=403, detail="Somente o Administrador Geral pode gerenciar esse perfil.")
        if ator.id != alvo.id:
            if ator.papel == "MEDICO" and alvo.papel != "ENFERMEIRO":
                raise HTTPException(status_code=403, detail="Médicos podem gerenciar somente enfermeiros.")
            if ator.papel == "ENFERMEIRO":
                raise HTTPException(status_code=403, detail="Enfermeiros não têm permissão para gerenciar outros usuários.")
            if ator.papel == "DIRETOR":
                if alvo.papel in {"ADMIN_GERAL", "DIRETOR"}:
                    raise HTTPException(status_code=403, detail="Diretores não podem gerenciar outros diretores ou administradores.")
                from app.models.clinico import (
                    EstabelecimentoEnfermeiroModel,
                    EstabelecimentoProfissionalModel,
                    HospitalDiretorModel,
                )
                vinculos = (
                    self.users_repo.db.query(HospitalDiretorModel.hospital_id)
                    .filter(HospitalDiretorModel.usuario_id == ator.id, HospitalDiretorModel.fim_vinculo.is_(None))
                    .all()
                )
                hospital_ids = [v[0] for v in vinculos if v[0] is not None]
                if hospital_ids:
                    medicos_ids = {
                        m[0]
                        for m in self.users_repo.db.query(EstabelecimentoProfissionalModel.medico_id)
                        .filter(
                            EstabelecimentoProfissionalModel.estabelecimento_id.in_(hospital_ids),
                            EstabelecimentoProfissionalModel.fim_vinculo.is_(None),
                        )
                        .all()
                    }
                    enfermeiros_ids = {
                        e[0]
                        for e in self.users_repo.db.query(EstabelecimentoEnfermeiroModel.enfermeiro_id)
                        .filter(
                            EstabelecimentoEnfermeiroModel.estabelecimento_id.in_(hospital_ids),
                            EstabelecimentoEnfermeiroModel.fim_vinculo.is_(None),
                        )
                        .all()
                    }
                    if (alvo.papel == "MEDICO" and alvo.medico_id not in medicos_ids) or (
                        alvo.papel == "ENFERMEIRO" and alvo.enfermeiro_id not in enfermeiros_ids
                    ):
                        raise HTTPException(status_code=403, detail="Você só pode gerenciar usuários vinculados ao seu hospital.")

        alteracoes = dados.model_dump(exclude_unset=True) if hasattr(dados, "model_dump") else dict(dados)
        if "email" in alteracoes:
            existente = self.users_repo.buscar_por_email(alteracoes["email"])
            if existente and existente.id != alvo.id:
                raise HTTPException(status_code=409, detail="Já existe uma conta com esse e-mail.")
        if ator.id == alvo.id and alteracoes.get("ativo") is False:
            raise HTTPException(status_code=400, detail="Não é possível desativar a própria conta.")
        if ator.id == alvo.id and alteracoes.get("nivel", alvo.papel) != alvo.papel:
            raise HTTPException(status_code=400, detail="Não é possível alterar o próprio perfil.")
        if ator.papel == "MEDICO" and alteracoes.get("nivel", "ENFERMEIRO") != "ENFERMEIRO":
            raise HTTPException(status_code=403, detail="Médicos não podem alterar o papel de enfermeiro.")

        papel_final = alteracoes.get("nivel", alvo.papel)
        remove_direcao_ativa = (
            alvo.papel == "DIRETOR"
            and alvo.ativo
            and (papel_final != "DIRETOR" or alteracoes.get("ativo") is False)
        )
        if remove_direcao_ativa:
            diretores_ativos = self.users_repo.contar_diretores_ativos()
            if diretores_ativos <= 1:
                raise HTTPException(status_code=409, detail="É necessário manter ao menos um diretor ativo.")

        if alteracoes.get("senha"):
            alvo.senha_hash = gerar_hash_senha(alteracoes.pop("senha"))
        if "nivel" in alteracoes:
            alteracoes["papel"] = alteracoes.pop("nivel")
        for campo in ("nome", "email", "papel", "registro", "especialidade", "ativo"):
            if campo in alteracoes:
                setattr(alvo, campo, alteracoes[campo])
        if alvo.papel not in {"INSTITUCIONAL_WHATSAPP", "ADMIN_GERAL"}:
            alvo.pode_gerenciar_whatsapp = False

        salvo = self.users_repo.salvar(alvo)
        return usuario_publico(salvo)
