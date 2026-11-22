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
        if ator.papel == "MEDICO" and alvo.papel != "ENFERMEIRO":
            raise HTTPException(status_code=403, detail="Médicos podem gerenciar somente enfermeiros.")

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
