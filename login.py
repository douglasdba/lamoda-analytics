import streamlit as st
import toml
from pathlib import Path

# =========================================================
# 1) CARREGAR CREDENCIAIS
# =========================================================
def load_credentials():
    # Streamlit Cloud
    if "users" in st.secrets:
        return {
            str(u).strip(): str(p).strip()
            for u, p in st.secrets["users"].items()
        }

    # Ambiente local
    base_dir = Path(__file__).resolve().parent
    local_path = base_dir / "credentials.local.toml"

    if not local_path.exists():
        st.error("Arquivo credentials.local.toml não encontrado.")
        st.stop()

    data = toml.load(local_path)
    return {
        str(u).strip(): str(p).strip()
        for u, p in data.get("users", {}).items()
    }


# ⚠️ CARREGA SEM CACHE
USERS = load_credentials()

# =========================================================
# 2) VALIDAR LOGIN
# =========================================================
def check_login(username, password):
    if not username or not password:
        return False

    return USERS.get(username.strip()) == password.strip()


# =========================================================
# 3) TELA DE LOGIN
# =========================================================
def show_login_page():
    st.markdown("## 🔐 Login — La Moda Analytics")
    st.markdown("Faça login para acessar o portal.")

    with st.form("login_form"):
        username = st.text_input("Usuário")
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
