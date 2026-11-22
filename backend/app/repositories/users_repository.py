from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.users import UsuarioSistemaModel


class UsersRepository:
    """Repositório de persistência e consulta de usuários do sistema."""

    def __init__(self, db: Session):
        self.db = db

    def buscar_por_id(self, id: int) -> Optional[UsuarioSistemaModel]:
        return self.db.query(UsuarioSistemaModel).filter_by(id=id).first()

    def buscar_por_email(self, email: str) -> Optional[UsuarioSistemaModel]:
        email_normalizado = (email or "").strip().lower()
        return (
            self.db.query(UsuarioSistemaModel)
            .filter(UsuarioSistemaModel.email == email_normalizado)
            .first()
        )

    def listar_ativos(
        self, papel: Optional[str] = None, papeis: Optional[List[str]] = None
    ) -> List[UsuarioSistemaModel]:
        consulta = self.db.query(UsuarioSistemaModel).filter(UsuarioSistemaModel.ativo.is_(True))
        if papel:
            consulta = consulta.filter(UsuarioSistemaModel.papel == papel)
        elif papeis:
            consulta = consulta.filter(UsuarioSistemaModel.papel.in_(papeis))
        return consulta.order_by(UsuarioSistemaModel.nome).all()

    def criar_usuario(
        self,
        email: str,
        nome: str,
        senha_hash: str,
        papel: str,
        trocar_senha_obrigatorio: bool = False,
        registro: Optional[str] = None,
        especialidade: Optional[str] = None,
        medico_id: Optional[int] = None,
        enfermeiro_id: Optional[int] = None,
        pode_gerenciar_whatsapp: bool = False,
        ativo: bool = True,
    ) -> UsuarioSistemaModel:
        novo = UsuarioSistemaModel(
            email=(email or "").strip().lower(),
            nome=(nome or "").strip(),
            senha_hash=senha_hash,
            papel=papel,
            trocar_senha_obrigatorio=trocar_senha_obrigatorio,
            registro=(registro or "").strip() or None,
            especialidade=(especialidade or "").strip() or None,
            medico_id=medico_id,
            enfermeiro_id=enfermeiro_id,
            pode_gerenciar_whatsapp=pode_gerenciar_whatsapp,
            ativo=ativo,
        )
        self.db.add(novo)
        self.db.commit()
        self.db.refresh(novo)
        return novo

    def salvar(self, usuario: UsuarioSistemaModel) -> UsuarioSistemaModel:
        self.db.add(usuario)
        self.db.commit()
        self.db.refresh(usuario)
        return usuario

    def contar_diretores_ativos(self) -> int:
        return (
            self.db.query(UsuarioSistemaModel)
            .filter_by(papel="DIRETOR", ativo=True)
            .count()
        )

    def remover_ou_desativar(self, id: int) -> Optional[UsuarioSistemaModel]:
        alvo = self.buscar_por_id(id)
        if alvo:
            alvo.ativo = False
            self.db.commit()
            self.db.refresh(alvo)
        return alvo
