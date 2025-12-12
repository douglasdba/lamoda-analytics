import streamlit as st
import toml
import os

# =========================================================
# 1) Carrega credenciais do arquivo credentials.toml
# =========================================================
@st.cache_resource
def load_credentials():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cred_path = os.path.join(base_dir, "credentials.toml")

    if not os.path.exists(cred_path):
        raise FileNotFoundError(f"Arquivo de credenciais não encontrado em: {cred_path}")

    data = toml.load(cred_path)

    # Pega a seção [users] e já normaliza (strip em chave e valor)
    raw_users = data.get("users", {})
    users = {str(user).strip(): str(pwd).strip() for user, pwd in raw_users.items()}

    # DEBUG opcional: descomente uma vez se quiser ver no terminal
    # print("USERS CARREGADOS:", users)

    return users


USERS = load_credentials()

# =========================================================
# 2) Função para validar login
# =========================================================
def check_login(username, password):
    user = username.strip()
    pwd = password.strip()

    # DEBUG opcional:
    # print(f"Tentativa de login -> user='{user}', pwd='{pwd}'")

    if not user or not pwd:
        return False

    stored_pwd = USERS.get(user)
    if stored_pwd is None:
        return False

    return pwd == stored_pwd

# =========================================================
# 3) Interface de Login
# =========================================================
def show_login_page():
    st.markdown("## 🔐 Login — La Moda Analytics")
    st.markdown("### Bem-vindo! Faça login para acessar o dashboard.")

    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")

    if st.button("Entrar", use_container_width=True):
        if check_login(username, password):
            st.session_state["logged_user"] = username.strip()
            st.success("Login realizado com sucesso!")
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")

# =========================================================
# 4) Exibir login caso usuário não esteja logado
# =========================================================
def require_login():
    if "logged_user" not in st.session_state:
        show_login_page()
        st.stop()

# Teste isolado
if __name__ == "__main__":
    require_login()
