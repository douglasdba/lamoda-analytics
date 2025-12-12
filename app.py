import streamlit as st
from pathlib import Path
from login import require_login

# ======================================================
# CONFIGURAÇÃO DA PÁGINA (UMA ÚNICA VEZ)
# ======================================================
st.set_page_config(
    page_title="Lamoda Analytics",
    page_icon="static/logo_la_moda.png",
    layout="wide"
)

# ======================================================
# LOGIN — BLOQUEIA ACESSO
# ======================================================
require_login()

# ======================================================
# CAMINHOS PADRÃO
# ======================================================
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
STREAMLIT_DIR = BASE_DIR / ".streamlit"

# ======================================================
# CARREGAR CSS GLOBAL
# ======================================================
css_path = STREAMLIT_DIR / "styles.css"

if css_path.exists():
    st.markdown(
        f"<style>{css_path.read_text(encoding='utf-8')}</style>",
        unsafe_allow_html=True
    )

# ======================================================
# SIDEBAR — LOGO + MENU + LOGOUT
# ======================================================
with st.sidebar:

    logo_path = STATIC_DIR / "logo_la_moda.png"

    if logo_path.exists():
        st.image(str(logo_path), width=130)

    st.markdown(
        """
        <h2 style='text-align:center; margin-top:0;'>Lamoda Analytics</h2>
        <hr style="margin-top:10px; margin-bottom:10px; border:1px solid #333;">
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="sidebar-signature">
            <b>Douglas Santos</b><br>
            <i>Desenvolvedor do Portal</i>
        </div>
        """,
        unsafe_allow_html=True
    )

    if st.button("🚪 Sair", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ======================================================
# CONTEÚDO PRINCIPAL — HOME
# ======================================================
usuario = st.session_state.get("logged_user", "Usuário")

st.markdown(
    f"""
    <div style="
        background-color:#111827;
        padding: 12px 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        border: 1px solid #1F2937;
        font-size: 18px;
    ">
        👋 <b>Bem-vindo, {usuario.split('.')[0].capitalize()}!</b>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div style="
        background-color: #0D1117;
        border: 1px solid #1F2937;
        padding: 18px 22px;
        border-radius: 12px;
        margin-bottom: 20px;
    ">
        <h4 style="color:#58A6FF; margin:0;">📅 Atualização dos Dados</h4>
        <p style="color:#E5E7EB; margin-top:6px;">
            Dados atualizados em:
            <strong style="color:#93C5FD;">02/12/2025</strong>
        </p>
        <p style="color:#9CA3AF; font-size:14px;">
            Fonte: <strong>Sistema Senior – Gestão de Pessoas</strong>
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

st.title("📊 Lamoda Analytics")
st.subheader("Portal de BI Oficial")

st.write(
    """
    Bem-vindo ao painel corporativo de análises e indicadores.

    Utilize o menu lateral para acessar dashboards como:

    - **Turnover**
    - **Tempo de Casa**
    - **Absenteísmo**
    - **Assistente IA**
    """
)

st.info("Escolha uma página no menu lateral para começar.")
