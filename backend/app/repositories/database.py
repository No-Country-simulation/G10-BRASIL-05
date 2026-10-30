from typing import Generator, List, Optional, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from app.config.settings import settings
from app.models.triagem import (
    Base,
    HospitalModel,
    MedicoModel,
    PacienteModel,
    DocumentoTriagemModel,
    TrilhaAuditoriaModel,
)

# Engine com pool seguro; suporte a SQLite em memória compartilhado com StaticPool para testes locais
if "sqlite" in settings.DATABASE_URL:
    engine = create_engine(
        settings.DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    engine = create_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def seed_dados_iniciais(db: Session):
    """Insere unidades hospitalares e corpo clínico inicial de referência para demonstração."""
    try:
        # Seed de Hospitais
        if db.query(HospitalModel).count() == 0:
            hospitais_padrao = [
                HospitalModel(
                    nome="Hospital Central MediFlow",
                    cnpj="12.345.678/0001-90",
                    cidade="São Paulo",
                    uf="SP",
                ),
                HospitalModel(
                    nome="UPA Pronto Atendimento 24h",
                    cnpj="98.765.432/0001-10",
                    cidade="São Paulo",
                    uf="SP",
                ),
                HospitalModel(
                    nome="Ambulatório Geral de Especialidades",
                    cnpj="55.443.221/0001-33",
                    cidade="Campinas",
                    uf="SP",
                ),
            ]
            db.add_all(hospitais_padrao)
            db.commit()

        # Seed de Médicos
        if db.query(MedicoModel).count() == 0:
            medicos_padrao = [
                MedicoModel(
                    nome="Dra. Renata Silveira",
                    crm="145892-SP",
                    especialidade="Radiologia / Pneumologia",
                    uf="SP",
                ),
                MedicoModel(
                    nome="Dr. Lucas Ramos",
                    crm="87654-SP",
                    especialidade="Clínica Médica",
                    uf="SP",
                ),
                MedicoModel(
                    nome="Dr. Roberto Silva",
                    crm="112233-SP",
                    especialidade="Auditoria Médica",
                    uf="SP",
                ),
            ]
            db.add_all(medicos_padrao)
            db.commit()
    except Exception as e:
        db.rollback()
        # Não bloqueia inicialização caso haja restrição pontual de conexão
        pass


def init_db():
    """Cria as tabelas no banco de dados se não existirem e executa seed inicial."""
    Base.metadata.create_all(bind=engine)

    # Migração defensiva para adicionar colunas relacionais caso a tabela já existisse
    try:
        with engine.connect() as conn:
            if "postgresql" in settings.DATABASE_URL:
                conn.execute(text("ALTER TABLE documentos_triagem ADD COLUMN IF NOT EXISTS paciente_id INTEGER REFERENCES pacientes(id);"))
                conn.execute(text("ALTER TABLE documentos_triagem ADD COLUMN IF NOT EXISTS medico_id INTEGER REFERENCES medicos(id);"))
                conn.execute(text("ALTER TABLE documentos_triagem ADD COLUMN IF NOT EXISTS hospital_id INTEGER REFERENCES hospitais(id);"))
                conn.commit()
    except Exception:
        pass

    db = SessionLocal()
    try:
        seed_dados_iniciais(db)
    finally:
        db.close()


def get_db() -> Generator[Session, None, None]:
    """Dependência FastAPI para injeção de sessão do banco de dados."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class DatabaseRepository:
    """Repositório de persistência para triagens clínicas, ecossistema hospitalar e auditoria."""

    def __init__(self, db: Session):
        self.db = db

    # --------------------------------------------------------------------------
    # Upsert e Gestão de Pacientes
    # --------------------------------------------------------------------------
    def obter_ou_criar_paciente(
        self,
        nome: str,
        idade: Optional[int] = None,
        cpf: Optional[str] = None,
    ) -> PacienteModel:
        """Busca paciente existente ou cria novo cadastro (provisório se sem CPF)."""
        paciente = None
        if cpf:
            paciente = self.db.query(PacienteModel).filter(PacienteModel.cpf == cpf).first()

        if not paciente and nome:
            # Busca por combinação de nome aproximado
            paciente = self.db.query(PacienteModel).filter(
                PacienteModel.nome.ilike(nome.strip())
            ).first()

        if not paciente:
            try:
                paciente = PacienteModel(
                    nome=nome.strip() if nome else "Paciente Não Identificado",
                    idade=idade,
                    cpf=cpf,
                    cadastro_provisorio=True if not cpf else False,
                )
                self.db.add(paciente)
                self.db.commit()
                self.db.refresh(paciente)
            except Exception:
                self.db.rollback()
                if cpf:
                    paciente = self.db.query(PacienteModel).filter(PacienteModel.cpf == cpf).first()
                if not paciente and nome:
                    paciente = self.db.query(PacienteModel).filter(PacienteModel.nome.ilike(nome.strip())).first()

        return paciente

    def listar_pacientes(self, skip: int = 0, limit: int = 50) -> List[PacienteModel]:
        return self.db.query(PacienteModel).order_by(PacienteModel.nome.asc()).offset(skip).limit(limit).all()

    def buscar_paciente_por_id(self, paciente_id: int) -> Optional[PacienteModel]:
        return self.db.query(PacienteModel).filter(PacienteModel.id == paciente_id).first()

    def listar_historico_paciente(self, paciente_id: int) -> List[DocumentoTriagemModel]:
        return (
            self.db.query(DocumentoTriagemModel)
            .filter(DocumentoTriagemModel.paciente_id == paciente_id)
            .order_by(DocumentoTriagemModel.created_at.desc())
            .all()
        )

    # --------------------------------------------------------------------------
    # Upsert e Gestão de Médicos
    # --------------------------------------------------------------------------
    def obter_ou_criar_medico(
        self,
        nome: str,
        crm: str,
        especialidade: Optional[str] = None,
    ) -> MedicoModel:
        """Busca médico por CRM único ou registra novo no corpo clínico."""
        crm_formatado = crm.strip().upper() if crm else "CRM-INDEFINIDO"
        medico = self.db.query(MedicoModel).filter(MedicoModel.crm == crm_formatado).first()

        if not medico:
            uf = "SP"
            if "-" in crm_formatado:
                partes = crm_formatado.split("-")
                if len(partes) > 1 and len(partes[-1]) == 2:
                    uf = partes[-1]

            try:
                medico = MedicoModel(
                    nome=nome.strip() if nome else "Médico Solicitante",
                    crm=crm_formatado,
                    especialidade=especialidade or "Clínica Médica",
                    uf=uf,
                )
                self.db.add(medico)
                self.db.commit()
                self.db.refresh(medico)
            except Exception:
                self.db.rollback()
                medico = self.db.query(MedicoModel).filter(MedicoModel.crm == crm_formatado).first()

        return medico

    def listar_medicos(self, skip: int = 0, limit: int = 50) -> List[MedicoModel]:
        return self.db.query(MedicoModel).order_by(MedicoModel.nome.asc()).offset(skip).limit(limit).all()

    # --------------------------------------------------------------------------
    # Upsert e Gestão de Hospitais
    # --------------------------------------------------------------------------
    def obter_ou_criar_hospital(self, nome_ou_canal: str) -> HospitalModel:
        """Busca unidade hospitalar ou cadastra o canal como polo de atendimento."""
        nome_limpo = (nome_ou_canal or "Hospital Central MediFlow").replace("_", " ").title()
        hospital = self.db.query(HospitalModel).filter(
            HospitalModel.nome.ilike(nome_limpo)
        ).first()

        if not hospital:
            try:
                hospital = HospitalModel(
                    nome=nome_limpo,
                    cidade="São Paulo",
                    uf="SP",
                    ativo=True,
                )
                self.db.add(hospital)
                self.db.commit()
                self.db.refresh(hospital)
            except Exception:
                self.db.rollback()
                hospital = self.db.query(HospitalModel).filter(
                    HospitalModel.nome.ilike(nome_limpo)
                ).first()

        return hospital

    def listar_hospitais(self) -> List[HospitalModel]:
        return self.db.query(HospitalModel).filter(HospitalModel.ativo == True).all()

    # --------------------------------------------------------------------------
    # Gestão de Triagens e Roteamento
    # --------------------------------------------------------------------------
    def salvar(self, model: DocumentoTriagemModel) -> DocumentoTriagemModel:
        """Salva a triagem associando automaticamente as entidades relacionais (Upsert)."""
        dados = model.dados_extraidos or {}

        # 1. Vincula Paciente
        paciente_info = dados.get("paciente") or {}
        nome_paciente = paciente_info.get("nome")
        idade_paciente = paciente_info.get("idade")
        cpf_paciente = paciente_info.get("cpf")

        if nome_paciente and not model.paciente_id:
            paciente_obj = self.obter_ou_criar_paciente(
                nome=nome_paciente,
                idade=idade_paciente,
                cpf=cpf_paciente,
            )
            model.paciente_id = paciente_obj.id

        # 2. Vincula Médico Solicitante
        medico_info = dados.get("medico_solicitante") or {}
        crm_medico = medico_info.get("crm")
        nome_medico = medico_info.get("nome")
        if crm_medico and not model.medico_id:
            medico_obj = self.obter_ou_criar_medico(
                nome=nome_medico or "Médico Solicitante",
                crm=crm_medico,
                especialidade=model.especialidade,
            )
            model.medico_id = medico_obj.id

        # 3. Vincula Unidade Hospitalar
        if model.canal_origem and not model.hospital_id:
            hospital_obj = self.obter_ou_criar_hospital(model.canal_origem)
            model.hospital_id = hospital_obj.id

        existente = self.buscar_por_documento_id(model.documento_id)
        if existente:
            existente.tipo_arquivo = model.tipo_arquivo
            existente.canal_origem = model.canal_origem
            existente.documento_texto = model.documento_texto
            existente.tipo_documento = model.tipo_documento
            existente.especialidade = model.especialidade
            existente.nivel_prioridade = model.nivel_prioridade
            existente.score_confianca = model.score_confianca
            existente.destino_principal = model.destino_principal
            existente.requer_auditoria_humana = model.requer_auditoria_humana
            existente.status_processamento = model.status_processamento
            existente.justificativa_roteamento = model.justificativa_roteamento
            existente.dados_extraidos = model.dados_extraidos
            existente.bucket_oci = model.bucket_oci
            existente.caminho_objeto_oci = model.caminho_objeto_oci
            existente.paciente_id = model.paciente_id
            existente.medico_id = model.medico_id
            existente.hospital_id = model.hospital_id
            self.db.commit()
            self.db.refresh(existente)
            return existente

        try:
            self.db.add(model)
            self.db.commit()
            self.db.refresh(model)
            return model
        except Exception:
            self.db.rollback()
            existente = self.buscar_por_documento_id(model.documento_id)
            if existente:
                existente.tipo_arquivo = model.tipo_arquivo
                existente.canal_origem = model.canal_origem
                existente.documento_texto = model.documento_texto
                existente.tipo_documento = model.tipo_documento
                existente.especialidade = model.especialidade
                existente.nivel_prioridade = model.nivel_prioridade
                existente.score_confianca = model.score_confianca
                existente.destino_principal = model.destino_principal
                existente.requer_auditoria_humana = model.requer_auditoria_humana
                existente.status_processamento = model.status_processamento
                existente.justificativa_roteamento = model.justificativa_roteamento
                existente.dados_extraidos = model.dados_extraidos
                existente.bucket_oci = model.bucket_oci
                existente.caminho_objeto_oci = model.caminho_objeto_oci
                existente.paciente_id = model.paciente_id
                existente.medico_id = model.medico_id
                existente.hospital_id = model.hospital_id
                self.db.commit()
                self.db.refresh(existente)
                return existente
            raise

    def buscar_por_documento_id(self, documento_id: str) -> Optional[DocumentoTriagemModel]:
        return self.db.query(DocumentoTriagemModel).filter(
            DocumentoTriagemModel.documento_id == documento_id
        ).first()

    def listar_todos(self, skip: int = 0, limit: int = 50) -> List[DocumentoTriagemModel]:
        return (
            self.db.query(DocumentoTriagemModel)
            .order_by(DocumentoTriagemModel.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def listar_auditoria(self) -> List[DocumentoTriagemModel]:
        """Retorna apenas documentos que requerem auditoria humana pendente."""
        return (
            self.db.query(DocumentoTriagemModel)
            .filter(
                DocumentoTriagemModel.requer_auditoria_humana == True,
                DocumentoTriagemModel.status_processamento == "em_auditoria",
            )
            .order_by(DocumentoTriagemModel.created_at.desc())
            .all()
        )

    def registrar_decisao(
        self,
        documento_id: str,
        decisao: str,
        auditor_nome: str,
        justificativa: str,
        dados_corrigidos: Optional[Dict[str, Any]] = None,
    ) -> Optional[DocumentoTriagemModel]:
        doc = self.buscar_por_documento_id(documento_id)
        if not doc:
            return None

        # Trilha de auditoria
        trilha = TrilhaAuditoriaModel(
            documento_id=documento_id,
            auditor_nome=auditor_nome,
            decisao=decisao,
            justificativa=justificativa,
            dados_anteriores=doc.dados_extraidos,
            dados_finais=dados_corrigidos or doc.dados_extraidos,
        )
        self.db.add(trilha)

        # Atualiza status do documento
        doc.status_processamento = f"auditoria_{decisao}"
        doc.requer_auditoria_humana = False
        if dados_corrigidos:
            doc.dados_extraidos = dados_corrigidos

        self.db.commit()
        self.db.refresh(doc)
        return doc
