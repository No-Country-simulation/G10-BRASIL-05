"""Componentes para pré-visualizar arquivos e transcrições clínicas."""
import base64
from html import escape
import io

from PIL import Image, ImageOps
import streamlit as st
import streamlit.components.v1 as components

DOCUMENTO_INDISPONIVEL = "Documento original não disponível."


def _renderizar_visualizador_pdf(conteudo_pdf: bytes, altura: int = 420) -> None:
    b64 = base64.b64encode(conteudo_pdf).decode("utf-8")
    html_pdf = f"""
    <div id="pdf-wrap" style="width:100%;height:{altura - 8}px;border:1px solid #CBD5E1;
         border-radius:10px;overflow:hidden;background:#F1F5F9;"></div>
    <script>
    (function() {{
        try {{
            const b64 = "{b64}";
            const bin = atob(b64);
            const bytes = new Uint8Array(bin.length);
            for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
            const blob = new Blob([bytes], {{ type: "application/pdf" }});
            const url = URL.createObjectURL(blob);
            const iframe = document.createElement("iframe");
            iframe.src = url + "#toolbar=1&navpanes=0&view=FitH";
            iframe.style.width = "100%";
            iframe.style.height = "100%";
            iframe.style.border = "none";
            document.getElementById("pdf-wrap").appendChild(iframe);
        }} catch (e) {{
            document.getElementById("pdf-wrap").innerHTML =
                '<div style="padding:20px;color:#475569;font-family:sans-serif;font-size:14px;">' +
                'Não foi possível renderizar o PDF incorporado neste navegador. Utilize o botão de download acima.</div>';
        }}
    }})();
    </script>
    """
    components.html(html_pdf, height=altura, scrolling=False)


def _renderizar_folha_textual(documento_id: str, texto: str, nome_arquivo: str | None = None) -> None:
    linhas_escapadas = "<br>".join(escape(linha) for linha in (texto or DOCUMENTO_INDISPONIVEL).splitlines())
    subtitulo = escape(nome_arquivo or f"Transcrição Clínica • {documento_id}")
    st.markdown(
        f"""
        <div style="background:#FFFFFF;border:1px solid #CBD5E1;border-top:4px solid #0B3C7A;
                    border-radius:10px;padding:16px 18px;max-height:380px;overflow-y:auto;
                    box-shadow:inset 0 1px 2px rgba(15,23,42,0.03);">
            <div style="display:flex;justify-content:space-between;align-items:center;
                        padding-bottom:10px;margin-bottom:12px;border-bottom:1px solid #E2E8F0;">
                <span style="font-size:0.76rem;font-weight:700;color:#0B3C7A;text-transform:uppercase;
                             letter-spacing:0.05em;">{subtitulo}</span>
                <span style="font-size:0.73rem;color:#64748B;background:#F1F5F9;padding:2px 8px;
                             border-radius:999px;font-weight:600;">{escape(documento_id)}</span>
            </div>
            <div style="font-family:'Inter',system-ui,sans-serif;font-size:0.86rem;color:#1E293B;
                        line-height:1.55;white-space:normal;">
                {linhas_escapadas}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.dialog("Pré-visualização do Documento Original", width="large")
def modal_preview_documento(
    documento_id: str,
    fonte: tuple[bytes, str, str | None] | None,
    texto_extraido: str,
) -> None:
    if fonte:
        conteudo, mime, nome = fonte
        st.caption(f"Documento: `{documento_id}` • Arquivo: **{nome or 'documento_original'}** (`{mime}`)")
        if mime.startswith("image/"):
            col_rot, col_tam = st.columns([1, 2], vertical_alignment="center")
            with col_rot:
                if st.button("Girar 90°", icon=":material/rotate_right:", key=f"btn_rot_prev_{documento_id}", use_container_width=True):
                    st.session_state[f"rot_prev_{documento_id}"] = (st.session_state.get(f"rot_prev_{documento_id}", 0) - 90) % 360
                    st.rerun()
            with col_tam:
                largura = st.slider(
                    "Tamanho",
                    min_value=300,
                    max_value=900,
                    value=520,
                    step=40,
                    key=f"slide_w_prev_{documento_id}",
                    label_visibility="collapsed",
                )
            try:
                img = Image.open(io.BytesIO(conteudo))
                img = ImageOps.exif_transpose(img)
                angulo = st.session_state.get(f"rot_prev_{documento_id}", 0)
                if angulo:
                    img = img.rotate(angulo, expand=True)
                st.image(img, caption=nome or "Fonte original", width=largura)
            except Exception:
                st.image(conteudo, caption=nome or "Fonte original", width=520)
        elif mime == "application/pdf" or (nome and nome.lower().endswith(".pdf")):
            _renderizar_visualizador_pdf(conteudo, altura=600)
        else:
            _renderizar_folha_textual(documento_id, texto_extraido, nome)
    else:
        st.caption(f"Documento: `{documento_id}` • Visualização da transcrição textual")
        _renderizar_folha_textual(documento_id, texto_extraido)
