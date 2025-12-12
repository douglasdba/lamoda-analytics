import streamlit as st
import os
from login import require_login


# 🔐 Oculta sidebar antes do login
if "logged_user" not in st.session_state:
    st.set_page_config(page_title="Lamoda Analytics", layout="wide")
    hide_sidebar = """
        <style>
        section[data-testid="stSidebar"] {display: none;}
        </style>
    """
    st.markdown(hide_sidebar, unsafe_allow_html=True)
    require_login()
else:
    st.set_page_config(page_title="Lamoda Analytics", layout="wide")
    require_login()


# ============================================
# SAUDAÇÃO AO USUÁRIO LOGADO
# ============================================
usuario = st.session_state.get("logged_user", "")

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



# ======================================================
# CONFIGURAÇÃO DA PÁGINA
# ======================================================
st.set_page_config(
    page_title="Lamoda Analytics",
    page_icon="static/logo_la_moda.png",
    layout="wide"
)

# ======================================================
# LOGIN — BLOQUEIA ACESSO SE NÃO ESTIVER LOGADO
# ======================================================]

if "logged_user" not in st.session_state:
    st.sidebar.empty()


require_login()

# ======================================================
# CARREGAR CSS GLOBAL
# ======================================================
css_path = os.path.join(os.path.dirname(__file__), ".streamlit", "styles.css")

if os.path.exists(css_path):
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
else:
    st.warning("⚠️ Arquivo styles.css não encontrado em .streamlit/")

# ======================================================
# SIDEBAR — LOGO + MENU + LOGOUT
# ======================================================
logo_path = os.path.join(os.getcwd(), "static", "logo_la_moda.png")

with st.sidebar:

    # LOGO
    if os.path.exists(logo_path):
        st.image(logo_path, width=130)
    else:
        st.error("Logo não encontrado: static/logo_la_moda.png")

    # TÍTULO
    st.markdown(
        """
        <h2 style='text-align:center; margin-top:0;'>Lamoda Analytics</h2>
        <hr style="margin-top:10px; margin-bottom:10px; border:1px solid #333;">
        """,
        unsafe_allow_html=True
    )

    # ASSINATURA
    st.markdown(
        """
        <div class="sidebar-signature">
            <b>Douglas Santos</b><br>
            <i>Desenvolvedor do Portal</i>
        </div>
        """,
        unsafe_allow_html=True
    )

    # BOTÃO LOGOUT
    if st.button("🚪 Sair", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ======================================================
# CONTEÚDO PRINCIPAL — HOME PAGE
# ======================================================

# CARD DE ATUALIZAÇÃO
st.markdown(
    """
    <div style="
        background-color: #0D1117;
        border: 1px solid #1F2937;
        padding: 18px 22px;
        border-radius: 12px;
        margin-top: 10px;
        margin-bottom: 20px;
    ">
        <h4 style="color:#58A6FF; margin:0; padding:0;">📅 Atualização dos Dados</h4>
        <p style="color:#E5E7EB; margin-top:6px; font-size:15px;">
            Os dados exibidos neste portal foram atualizados em:<br>
            <strong style="color:#93C5FD; font-size:17px;">02/12/2025</strong>
        </p>
        <p style="color:#9CA3AF; font-size:14px; margin-top:2px;">
            Fonte dos dados: <strong>Sistema Senior – Gestão de Pessoas</strong>.
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# TÍTULO PRINCIPAL
st.title("📊 Lamoda Analytics")
st.subheader("Portal de BI Oficial")

# TEXTO DE BOAS-VINDAS
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

# MENSAGEM FINAL
st.info("Escolha uma página no menu lateral para começar.")
