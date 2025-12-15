import streamlit as st
import toml
from pathlib import Path

# =========================================================
# 1) CARREGAR CREDENCIAIS (SECRETS → LOCAL)
# =========================================================
@st.cache_resource
def load_credentials():
    """
    Prioridade:
    1) Streamlit Cloud -> st.secrets["users"]
    2) Local           -> credentials.local.toml
    """

    # =====================================================
    # 1) STREAMLIT CLOUD
    # =====================================================
    try:
        if "users" in st.secrets:
            return {
                str(u).strip(): str(p).strip()
                for u, p in st.secrets["users"].items()
            }
    except Exception:
        pass

    # =====================================================
    # 2) LOCAL
    # =====================================================
    base_dir = Path(__file__).resolve().parent
    local_path = base_dir / "credentials.local.toml"

    if not local_path.exists():
        st.error(
            "Arquivo **credentials.local.toml** não encontrado.\n\n"
            "➡️ Crie para desenvolvimento local\n"
            "➡️ Ou configure Secrets no Streamlit Cloud"
        )
        st.stop()

    data = toml.load(local_path)
    raw_users = data.get("users", {})

    return {
        str(u).strip(): str(p).strip()
        for u, p in raw_users.items()
    }


USERS = load_credentials()

# =========================================================
# 2) VALIDAR LOGIN
# =========================================================
def check_login(username, password):
    if not username or not password:
        return False

    user = username.strip()
    pwd = password.strip()

    stored_pwd = USERS.get(user)
    if not stored_pwd:
        return False

    return pwd == stored_pwd


# =========================================================
# 3) TELA DE LOGIN
# =========================================================
def show_login_page():
    st.markdown("## 🔐 Login — La Moda Analytics")
    st.markdown("Faça login para acessar o portal.")

    with st.form("login_form"):
        username = st.text_input("Usuário", placeholder="Usuário")
        password = st.text_input("Senha", type="password")

        submitted = st.form_submit_button("Entrar", use_container_width=True)

        if submitted:
            if check_login(username, password):
                st.session_state["logged_user"] = username.strip()
                st.success("Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")


# =========================================================
# 4) PROTEÇÃO GLOBAL
# =========================================================
def require_login():
    if "logged_user" not in st.session_state:
        show_login_page()
        st.stop()
