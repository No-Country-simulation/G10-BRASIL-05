"""Interface de Usuário e Controle de Acesso."""
from html import escape
from pathlib import Path
import re
from typing import Any
import streamlit as st

from api.cliente_http import (
    atualizar_usuario,
    desativar_usuario,
    listar_usuarios,
    provisionar_usuario,
)
from components.estilos import aplicar_css
from services.autenticacao import esta_autenticado, obter_usuario_autenticado
from services.erros import ErroDeApi
from utils.usuarios import (
    NIVEL_ADMIN_GERAL,
    NIVEL_DIRETOR,
    NIVEL_ENFERMEIRO,
    NIVEL_MEDICO,
    ROTULOS_DE_NIVEL,
)

LISTA_UFS = [
    "SP", "RJ", "MG", "RS", "PR", "SC", "BA", "PE", "CE", "DF",
    "ES", "GO", "MA", "MT", "MS", "PA", "PB", "PI", "RN", "RO",
    "RR", "SE", "TO", "AC", "AL", "AM", "AP"
]

DESCRICOES_PERFIL = {
    NIVEL_MEDICO: "Médico: envia documentos para triagem, confirma o roteamento e consulta o histórico. Sem acesso a usuários e revisão.",
    NIVEL_ENFERMEIRO: "Enfermeiro(a): envia documentos para triagem e consulta o histórico. Sem acesso a usuários e revisão.",
    NIVEL_DIRETOR: "Diretor Clínico: acesso completo a triagem, revisão humana, histórico e gerenciamento de equipe médica.",
    NIVEL_ADMIN_GERAL: "Administrador Geral: acesso irrestrito a todas as funcionalidades do sistema e governança.",
}

MAPA_CLASSES_BADGE = {
    NIVEL_ADMIN_GERAL: "badge-admin",
    NIVEL_DIRETOR: "badge-diretor",
    NIVEL_MEDICO: "badge-medico",
    NIVEL_ENFERMEIRO: "badge-enfermeiro",
}


def formatar_codigo_usuario(u_id: Any) -> str:
    if isinstance(u_id, str) and u_id.startswith("USR-"):
        return u_id
    try:
        num = int(str(u_id).split("-")[-1])
        return f"USR-{num:03d}"
    except Exception:
        return f"USR-{u_id}"


def extrair_id_numerico(u_id: Any) -> int:
    if isinstance(u_id, int):
        return u_id
    s = str(u_id)
    if "-" in s:
        s = s.split("-")[-1]
    return int(s)


def decompor_registro(registro_str: str | None) -> tuple[str, str, str]:
    """Extrai conselho, número e UF de registros como 'CRM 123456-SP'."""
    if not registro_str:
        return "CRM", "", "SP"
    s = registro_str.strip()
    conselho = "CRM"
    for cons in ["CRM", "COREN", "CRO", "CRF"]:
        if s.upper().startswith(cons):
            conselho = cons
            s = s[len(cons):].strip()
            break
    uf = "SP"
    for u in LISTA_UFS:
        if s.upper().endswith(f"-{u}") or s.upper().endswith(f"/{u}") or s.upper().endswith(f" {u}"):
            uf = u
            s = re.sub(rf"[-/\s]{u}$", "", s, flags=re.IGNORECASE).strip()
            break
    return conselho, s, uf


def render() -> None:
    if not esta_autenticado(st.session_state):
        st.switch_page("app.py")
        st.stop()

    usuario_atual = obter_usuario_autenticado(st.session_state) or {}
    nivel_atual = usuario_atual.get("nivel")

    # Injeção de Estilos CSS específicos da tela de Usuário
    aplicar_css(Path(__file__).with_name("style.css"))

    # Estado da sub-tela: "lista", "criar" ou "editar"
    modo_tela = st.session_state.get("usuario_modo_tela", "lista")
    pode_gerenciar_contas = nivel_atual in {NIVEL_ADMIN_GERAL, NIVEL_DIRETOR, NIVEL_MEDICO}

    # Validação de permissão para criação de novas contas
    if modo_tela == "criar" and not pode_gerenciar_contas:
        st.info("A criação de novas contas é restrita a Administradores Gerais, Diretores Clínicos e Médicos autorizados.")
        st.stop()

    alvo_edicao = st.session_state.get("usuario_em_edicao") or {}
    eh_autoedicao = str(alvo_edicao.get("id")) == str(usuario_atual.get("id"))
    if modo_tela == "editar" and not eh_autoedicao and not pode_gerenciar_contas:
        st.info("A administração de contas de outros profissionais é restrita a Administradores Gerais, Diretores Clínicos e Médicos autorizados.")
        st.stop()

    # Opções de perfil conforme nível hierárquico e contexto
    if eh_autoedicao:
        opcoes_papel = [alvo_edicao.get("nivel") or nivel_atual]
    elif nivel_atual == NIVEL_MEDICO:
        opcoes_papel = [NIVEL_ENFERMEIRO]
    elif nivel_atual == NIVEL_ADMIN_GERAL:
        opcoes_papel = [NIVEL_ADMIN_GERAL, NIVEL_DIRETOR, NIVEL_MEDICO, NIVEL_ENFERMEIRO]
    else:
        opcoes_papel = [NIVEL_MEDICO, NIVEL_ENFERMEIRO]

    # =========================================================================
    # SUB-TELA: CRIAR OU EDITAR CONTA PROFISSIONAL
    # =========================================================================
    if modo_tela in {"criar", "editar"}:
        eh_edicao = modo_tela == "editar"
        alvo = st.session_state.get("usuario_em_edicao") or {}

        # Botão de retorno superior
        with st.container(key="subtela_voltar_wrap"):
            st.markdown('<div class="subtela-voltar-link">', unsafe_allow_html=True)
            if st.button("< Voltar para contas", key="btn_voltar_para_contas"):
                st.session_state["usuario_modo_tela"] = "lista"
                st.session_state.pop("usuario_em_edicao", None)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        titulo_subtela = "Editar conta profissional" if eh_edicao else "Criar nova conta profissional"
        st.markdown(f'<div class="subtela-titulo">{titulo_subtela}</div>', unsafe_allow_html=True)

        # Preenchimento inicial em caso de edição
        nome_init = alvo.get("nome", "")
        email_init = alvo.get("email", "")
        nivel_init = alvo.get("nivel", opcoes_papel[0])
        idx_papel = opcoes_papel.index(nivel_init) if nivel_init in opcoes_papel else 0
        cons_init, num_reg_init, uf_reg_init = decompor_registro(alvo.get("registro"))
        esp_init = alvo.get("especialidade", "")

        with st.form("form_subtela_conta_profissional"):
            # 1. Card Dados pessoais
            st.markdown(
                """
                <div class="subtela-card-secao">
                    <div class="subtela-card-header">Dados pessoais</div>
                """,
                unsafe_allow_html=True,
            )
            col_dp1, col_dp2 = st.columns(2)
            with col_dp1:
                nome = st.text_input("Nome completo", value=nome_init, placeholder="Maria Souza Lima")
            with col_dp2:
                email = st.text_input("E-mail institucional", value=email_init, placeholder="nome@mediflow.com.br")
            st.markdown("</div>", unsafe_allow_html=True)

            # 2. Card Perfil e acesso
            st.markdown(
                """
                <div class="subtela-card-secao">
                    <div class="subtela-card-header">Perfil e acesso</div>
                """,
                unsafe_allow_html=True,
            )
            col_pa1, col_pa2 = st.columns([1.5, 2.5], vertical_alignment="center")
            with col_pa1:
                papel = st.selectbox(
                    "Perfil de acesso",
                    opcoes_papel,
                    index=idx_papel,
                    format_func=lambda item: ROTULOS_DE_NIVEL.get(item, item),
                )
            with col_pa2:
                desc_texto = DESCRICOES_PERFIL.get(papel, "")
                st.markdown(f'<div class="perfil-descricao-texto">{desc_texto}</div>', unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            # 3. Card Dados profissionais
            st.markdown(
                """
                <div class="subtela-card-secao">
                    <div class="subtela-card-header">Dados profissionais</div>
                """,
                unsafe_allow_html=True,
            )
            col_c1, col_c2, col_c3, col_c4 = st.columns([1.1, 1.8, 1.1, 2.8])
            with col_c1:
                opcoes_conselho = ["CRM", "COREN", "CRO", "CRF", "Outro"]
                idx_cons = opcoes_conselho.index(cons_init) if cons_init in opcoes_conselho else 0
                conselho = st.selectbox("Conselho", opcoes_conselho, index=idx_cons)
            with col_c2:
                num_registro = st.text_input("Número de registro", value=num_reg_init, placeholder="123456")
            with col_c3:
                idx_uf_cons = LISTA_UFS.index(uf_reg_init) if uf_reg_init in LISTA_UFS else 0
                uf_conselho = st.selectbox("UF do conselho", LISTA_UFS, index=idx_uf_cons)
            with col_c4:
                especialidade = st.text_input("Especialidade", value=esp_init, placeholder="Clínica Médica")

            col_dp_dep, col_dp_cargo = st.columns(2)
            with col_dp_dep:
                departamento = st.text_input("Departamento ou setor", placeholder="Pronto atendimento")
            with col_dp_cargo:
                cargo = st.text_input("Cargo ou função", placeholder="Médico plantonista")

            st.caption("Para médicos, o conselho é o CRM. Para enfermeiros, o COREN. Administradores não precisam preencher esta seção.")
            st.markdown("</div>", unsafe_allow_html=True)

            # 4. Card Endereço
            st.markdown(
                """
                <div class="subtela-card-secao">
                    <div class="subtela-card-header">Endereço</div>
                """,
                unsafe_allow_html=True,
            )
            col_end1, col_end2, col_end3 = st.columns([1.6, 3.4, 1.4])
            with col_end1:
                cep = st.text_input("CEP", placeholder="00000-000")
            with col_end2:
                logradouro = st.text_input("Logradouro", placeholder="Avenida Paulista")
            with col_end3:
                numero = st.text_input("Número", placeholder="1000")

            col_end4, col_end5, col_end6, col_end7 = st.columns([1.6, 2.0, 2.2, 1.0])
            with col_end4:
                complemento = st.text_input("Complemento", placeholder="Apto 42")
            with col_end5:
                bairro = st.text_input("Bairro", placeholder="Bela Vista")
            with col_end6:
                cidade = st.text_input("Cidade", placeholder="São Paulo")
            with col_end7:
                uf_end = st.selectbox("UF", LISTA_UFS, key="sb_uf_endereco")
            st.markdown("</div>", unsafe_allow_html=True)

            # 5. Card Credenciais
            st.markdown(
                """
                <div class="subtela-card-secao">
                    <div class="subtela-card-header">Credenciais</div>
                """,
                unsafe_allow_html=True,
            )
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                label_senha = "Nova senha (opcional; preencha para alterar)" if eh_edicao else "Senha inicial"
                senha = st.text_input(label_senha, type="password")
            with col_s2:
                confirmar_senha = st.text_input("Confirmar senha", type="password")

            col_cap_s, col_chk_s = st.columns([2, 2], vertical_alignment="center")
            with col_cap_s:
                st.caption("Mínimo de 12 caracteres.")
            with col_chk_s:
                troca_obrigatoria = st.checkbox("Exigir troca de senha no primeiro acesso", value=True)
            st.markdown("</div>", unsafe_allow_html=True)

            # Ações do Rodapé
            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
            col_vazia, col_btn_canc, col_btn_acao = st.columns([5.2, 1.4, 1.8], vertical_alignment="center")
            with col_btn_canc:
                cancelar_clicado = st.form_submit_button("Cancelar", use_container_width=True)
            with col_btn_acao:
                label_acao = "Salvar alterações" if eh_edicao else "Criar conta"
                salvar_clicado = st.form_submit_button(label_acao, type="primary", use_container_width=True)

        if cancelar_clicado:
            st.session_state["usuario_modo_tela"] = "lista"
            st.session_state.pop("usuario_em_edicao", None)
            st.rerun()

        if salvar_clicado:
            if not nome.strip() or not email.strip():
                st.error("Nome e e-mail institucional são obrigatórios.")
                st.stop()

            # Montagem do registro formatado
            registro_final = ""
            if num_registro.strip():
                registro_final = f"{conselho} {num_registro.strip()}-{uf_conselho}"

            if not eh_edicao:
                # Criação
                if not senha.strip():
                    st.error("A senha inicial é obrigatória.")
                    st.stop()
                if len(senha) < 12:
                    st.error("A senha deve ter pelo menos 12 caracteres.")
                    st.stop()
                if senha != confirmar_senha:
                    st.error("As senhas não coincidem.")
                    st.stop()

                try:
                    provisionar_usuario({
                        "nome": nome.strip(),
                        "email": email.strip(),
                        "senha": senha,
                        "nivel": papel,
                        "registro": registro_final,
                        "especialidade": especialidade.strip(),
                        "trocar_senha_obrigatorio": bool(troca_obrigatoria),
                    })
                    st.success("Conta profissional criada com sucesso!")
                    st.session_state["usuario_modo_tela"] = "lista"
                    st.rerun()
                except ErroDeApi as err:
                    st.error(str(err))
            else:
                # Edição
                dados_atualizacao = {
                    "nome": nome.strip(),
                    "email": email.strip(),
                    "nivel": papel,
                    "registro": registro_final,
                    "especialidade": especialidade.strip(),
                }
                if senha.strip():
                    if len(senha) < 12:
                        st.error("A nova senha deve ter no mínimo 12 caracteres.")
                        st.stop()
                    if senha != confirmar_senha:
                        st.error("As senhas não coincidem.")
                        st.stop()
                    dados_atualizacao["senha"] = senha.strip()

                try:
                    id_num = extrair_id_numerico(alvo["id"])
                    usuario_salvo = atualizar_usuario(id_num, dados_atualizacao)
                    if isinstance(usuario_salvo, dict) and (eh_autoedicao or str(alvo.get("id")) == str(usuario_atual.get("id"))):
                        usuario_atualizado = {**usuario_atual, **usuario_salvo}
                        st.session_state["mediflow_usuario_logado"] = usuario_atualizado
                        st.session_state["usuario_ativo_id"] = usuario_atualizado.get("id", "")
                        st.session_state["usuario_autenticado_email"] = usuario_atualizado.get("email", "")
                    st.success("Conta profissional atualizada com sucesso!")
                    st.session_state["usuario_modo_tela"] = "lista"
                    st.session_state.pop("usuario_em_edicao", None)
                    st.rerun()
                except ErroDeApi as err:
                    st.error(str(err))

        st.stop()

    # =========================================================================
    # VISÃO PADRÃO: LISTA DE USUÁRIOS E CONTAS PROFISSIONAIS
    # =========================================================================

    # Título e Subtítulo
    st.markdown('<div class="usuario-header-titulo">Usuário e controle de acesso</div>', unsafe_allow_html=True)
    st.markdown('<div class="usuario-header-subtitulo">Gerencie as contas profissionais e os perfis de acesso do portal.</div>', unsafe_allow_html=True)

    # Card "Meu perfil"
    nome_atual = usuario_atual.get("nome", "Admin")
    inicial_avatar = (nome_atual[:1] if nome_atual else "A").upper()
    email_atual = usuario_atual.get("email", "—")
    rotulo_perfil_atual = ROTULOS_DE_NIVEL.get(nivel_atual, nivel_atual or "Administrador")
    classe_perfil_atual = MAPA_CLASSES_BADGE.get(nivel_atual, "badge-admin")

    with st.container(border=True):
        col_avatar, col_nome_p, col_perfil_p, col_email_p, col_btn_p = st.columns(
            [0.8, 2.2, 2.5, 3.5, 2],
            vertical_alignment="center",
        )
        with col_avatar:
            st.markdown(f'<div class="avatar-circle">{inicial_avatar}</div>', unsafe_allow_html=True)
        with col_nome_p:
            st.markdown(
                f"""
                <div style="font-size:0.75rem; color:#64748B; line-height:1.2;">Meu perfil</div>
                <div style="font-size:1.05rem; font-weight:700; color:#0F172A; line-height:1.3;">{escape(nome_atual)}</div>
                """,
                unsafe_allow_html=True,
            )
        with col_perfil_p:
            st.markdown(
                f"""
                <div style="font-size:0.75rem; color:#64748B; line-height:1.2; margin-bottom:3px;">Perfil</div>
                <div><span class="badge-perfil {classe_perfil_atual}">{escape(rotulo_perfil_atual)}</span></div>
                """,
                unsafe_allow_html=True,
            )
        with col_email_p:
            st.markdown(
                f"""
                <div style="font-size:0.75rem; color:#64748B; line-height:1.2; margin-bottom:2px;">E-mail</div>
                <div style="font-size:0.92rem; color:#1E293B; font-weight:500;">{escape(email_atual)}</div>
                """,
                unsafe_allow_html=True,
            )
        with col_btn_p:
            if st.button("Editar perfil", icon=":material/edit:", key="btn_editar_meu_perfil", use_container_width=True):
                st.session_state["usuario_modo_tela"] = "editar"
                st.session_state["usuario_em_edicao"] = usuario_atual
                st.rerun()

    if not pode_gerenciar_contas:
        st.info("A administração e criação de contas de outros profissionais é restrita a Administradores Gerais, Diretores Clínicos e Médicos autorizados.")
        st.stop()

    try:
        usuarios = listar_usuarios() or []
    except ErroDeApi as erro:
        st.error(str(erro))
        st.stop()

    # Modal para Desativar Conta
    @st.dialog("Confirmar Desativação", width="small")
    def modal_desativar_conta(alvo: dict):
        st.markdown(
            f"""
            <div style="text-align: center; padding: 12px 0;">
                <div style="font-size: 1.05rem; font-weight: 700; color: #12304A; margin-bottom: 8px;">
                    Desativar conta de acesso?
                </div>
                <div style="font-size: 0.88rem; color: #475467; line-height: 1.45; margin-bottom: 16px;">
                    Tem certeza que deseja desativar o acesso de <strong>{escape(alvo.get('nome', ''))}</strong> ({escape(alvo.get('email', ''))})? O usuário não conseguirá mais entrar no portal.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col_c, col_conf = st.columns(2)
        with col_conf:
            if st.button("Sim, desativar", type="primary", use_container_width=True):
                try:
                    id_num = extrair_id_numerico(alvo["id"])
                    desativar_usuario(id_num)
                    st.success("Conta desativada.")
                    st.session_state.pop("modal_desativar_usuario_alvo", None)
                    st.rerun()
                except ErroDeApi as err:
                    st.error(str(err))

    if "modal_desativar_usuario_alvo" in st.session_state:
        modal_desativar_conta(st.session_state["modal_desativar_usuario_alvo"])

    # Card "Contas profissionais"
    with st.container(border=True):
        col_header_esq, col_header_dir = st.columns([7, 3], vertical_alignment="center")
        with col_header_esq:
            st.markdown(
                f"""
                <div style="font-size: 1.15rem; font-weight: 700; color: #0F172A; margin-bottom: 2px;">
                    Contas profissionais
                </div>
                <div style="font-size: 0.82rem; color: #64748B;">
                    {len(usuarios)} contas provisionadas
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_header_dir:
            if st.button("+ Criar nova conta", type="primary", key="btn_abrir_modal_criar", use_container_width=True):
                st.session_state["usuario_modo_tela"] = "criar"
                st.session_state.pop("usuario_em_edicao", None)
                st.rerun()

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        if not usuarios:
            st.info("Nenhuma conta profissional provisionada além da sua.")
        else:
            # Cabeçalho da tabela
            st.markdown(
                """
                <div style="display:grid; grid-template-columns: 1fr 2fr 2.3fr 1.4fr 1.4fr 1.8fr 0.9fr; padding: 10px 12px; background: #F8FAFC; border-radius: 8px 8px 0 0; border: 1px solid #E2E8F0; border-bottom: none; font-size: 0.74rem; font-weight: 600; color: #64748B; text-transform: uppercase; letter-spacing: 0.04em;">
                    <div>Código</div>
                    <div>Nome</div>
                    <div>E-mail</div>
                    <div>Perfil</div>
                    <div>Registro</div>
                    <div>Especialidade</div>
                    <div style="text-align: right;">Ações</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            for indice, u in enumerate(usuarios):
                codigo_fmt = formatar_codigo_usuario(u.get("id"))
                nome_u = u.get("nome", "—")
                email_u = u.get("email", "—")
                nivel_u = u.get("nivel", "")
                rotulo_perfil = ROTULOS_DE_NIVEL.get(nivel_u, nivel_u)
                classe_perfil = MAPA_CLASSES_BADGE.get(nivel_u, "badge-admin")
                registro_u = u.get("registro") or "—"
                especialidade_u = u.get("especialidade") or "—"
                u_id = u.get("id")

                with st.container():
                    c_cod, c_nom, c_eml, c_prf, c_reg, c_esp, c_act = st.columns(
                        [1, 2, 2.3, 1.4, 1.4, 1.8, 0.9],
                        vertical_alignment="center",
                    )
                    with c_cod:
                        st.markdown(f"<span style='font-size:0.86rem; color:#64748B;'>{escape(codigo_fmt)}</span>", unsafe_allow_html=True)
                    with c_nom:
                        st.markdown(f"<span style='font-size:0.88rem; font-weight:700; color:#0F172A;'>{escape(nome_u)}</span>", unsafe_allow_html=True)
                    with c_eml:
                        st.markdown(f"<span style='font-size:0.86rem; color:#475569;'>{escape(email_u)}</span>", unsafe_allow_html=True)
                    with c_prf:
                        st.markdown(f"<span class='badge-perfil {classe_perfil}'>{escape(rotulo_perfil)}</span>", unsafe_allow_html=True)
                    with c_reg:
                        st.markdown(f"<span style='font-size:0.85rem; color:#475569;'>{escape(registro_u)}</span>", unsafe_allow_html=True)
                    with c_esp:
                        st.markdown(f"<span style='font-size:0.85rem; color:#475569;'>{escape(especialidade_u)}</span>", unsafe_allow_html=True)
                    with c_act:
                        col_ed, col_de = st.columns(2, gap="small")
                        with col_ed:
                            if st.button("", icon=":material/edit:", key=f"btn_edit_u_{u_id}_{indice}", help="Editar conta"):
                                st.session_state["usuario_modo_tela"] = "editar"
                                st.session_state["usuario_em_edicao"] = u
                                st.rerun()
                        with col_de:
                            # Não permite desativar a própria conta
                            if u.get("id") != usuario_atual.get("id"):
                                if st.button("", icon=":material/delete:", key=f"btn_del_u_{u_id}_{indice}", help="Desativar conta"):
                                    st.session_state["modal_desativar_usuario_alvo"] = u
                                    st.rerun()

                    st.markdown(
                        '<div style="height: 1px; background: #F1F5F9; margin: 2px 0 4px 0;"></div>',
                        unsafe_allow_html=True,
                    )
