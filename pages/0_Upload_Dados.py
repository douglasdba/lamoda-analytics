import streamlit as st
import pandas as pd
import numpy as np
from datetime import date
import re
from login import require_login



# =========================================================
# CONFIGURAÇÃO DA PÁGINA (SEMPRE PRIMEIRO)
# =========================================================
st.set_page_config(
    page_title="Upload de Dados — La Moda BI",
    page_icon="📤",
    layout="wide"
)

# =========================================================
# LOGIN
# =========================================================
require_login()

# =========================================================
# TÍTULO
# =========================================================
st.title("📤 Upload de Dados — La Moda BI")
st.markdown(
    "Faça o upload dos arquivos **CLT** e **PJ** no formato `.xls`.\n\n"
    " Os dados **não são salvos** e **não ficam no GitHub**."
)

# =========================================================
# UPLOAD
# =========================================================
col1, col2 = st.columns(2)

with col1:
    file_clt = st.file_uploader(
        "Arquivo CLT (.xls)",
        type=["xls"],
        accept_multiple_files=False
    )

with col2:
    file_pj = st.file_uploader(
        "Arquivo PJ (.xls)",
        type=["xls"],
        accept_multiple_files=False
    )

if not file_clt or not file_pj:
    st.info("📌 Envie os dois arquivos para continuar.")
    st.stop()

# =========================================================
# PROCESSAMENTO
# =========================================================
with st.spinner("Processando dados..."):

    df_clt = pd.read_excel(file_clt, engine="xlrd")
    df_pj = pd.read_excel(file_pj, engine="xlrd")

    # ---------------- LIMPEZA INICIAL ----------------
    def limpeza_inicial(d):
        d = d.dropna(how="all").reset_index(drop=True)
        return d.drop(columns=["Posição do Local", "Cadastro"], errors="ignore")

    df_clt = limpeza_inicial(df_clt)
    df_pj = limpeza_inicial(df_pj)

    # ---------------- REMOÇÃO DE CARGOS ----------------
    padrao_clt = r"JOVEM APRENDIZ|ESTAGIARI[OA]|APRENDIZ"
    padrao_pj = r"PRESTADOR DE SERVIÇO|SERVENTE DE ZELADORIA|ESPEC\.? DE SERV\.? DE LAVANDERIA"

    cargos_remover_pj = [
        "MEDICO DE TRABALHO", "FAXINEIRO", "MODELO DE PROVA", "NUTRICIONISTA",
        "SECRETARIA", "MOTORISTA", "PROFESSOR DE INGLES", "ESTOQUISTA",
        "IMPRESSOR DE ADESIVOS", "ZELADORA", "ZELADOR", "VIGILANTE",
        "COACHING", "AN ADM PESSOAL I"
    ]

    padrao_pj_extra = r"|".join(map(re.escape, cargos_remover_pj))

    df_clt = df_clt[
        ~df_clt["Título Reduzido (Cargo)"].str.contains(padrao_clt, case=False, na=False)
    ]

    df_pj = df_pj[
        ~df_pj["Título Reduzido (Cargo)"].str.contains(padrao_pj_extra, case=False, na=False)
    ]

    df_pj = df_pj[
        ~df_pj["Título Reduzido (Cargo)"].str.contains(padrao_pj, case=False, na=False)
    ]

    # ---------------- DATAS ----------------
    DATE_COLS = ["Nascimento", "Admissão", "Data Afastamento"]

    def tratar_datas(d):
        for col in DATE_COLS:
            d[col] = (
                d[col]
                .astype(str)
                .str.strip()
                .replace(["", " ", "0", "00/00/0000", "--", "NaT", "nan"], pd.NA)
            )
            d[col] = pd.to_datetime(d[col], errors="coerce")
        return d

    df_clt = tratar_datas(df_clt)
    df_pj = tratar_datas(df_pj)

    def calc_idade(dt):
        if pd.isna(dt):
            return 0
        return int((date.today() - dt.date()).days / 365.25)

    for d in (df_clt, df_pj):
        d["Idade"] = d["Nascimento"].apply(calc_idade)
        d["Mes_Admissao"] = d["Admissão"].dt.month.fillna(0).astype(int)
        d["Ano_Admissao"] = d["Admissão"].dt.year.fillna(0).astype(int)
        d["Mes_Afastamento"] = d["Data Afastamento"].dt.month.fillna(0).astype(int)
        d["Ano_Afastamento"] = d["Data Afastamento"].dt.year.fillna(0).astype(int)

    # ---------------- SITUAÇÃO ----------------
    df_clt["Situacao_res"] = np.where(
        df_clt["Situação"].isin([1, 2, 3, 4]),
        "Ativo",
        "Desligado/Afastado"
    )

    df_pj["Situacao_res"] = np.where(
        df_pj["Situação"].isin([1, 2, 3, 4]),
        "Ativo",
        "Desligado/Afastado"
    )

    # ---------------- ÁREA ----------------
    def classificar_area(cc):
        cc = str(cc).upper()
        if "LOJAS" in cc:
            return "Varejo"
        if "SUPPLY" in cc:
            return "Indústria"
        return "Matriz"

    for d in (df_clt, df_pj):
        d["Area"] = d["C.Custo"].astype(str).apply(classificar_area)

    # ---------------- UNIFICA ----------------
    df_clt["TIPO"] = "CLT"
    df_pj["TIPO"] = "PJ"

    df_base = pd.concat([df_clt, df_pj], ignore_index=True)

def read_xls(uploaded_file):
    try:
        return pd.read_excel(uploaded_file, engine="xlrd")
    except ImportError:
        st.error(
            "Faltou instalar a dependência **xlrd** no Streamlit Cloud.\n\n"
            "✅ Corrija o `requirements.txt` com: `xlrd==2.0.1` e faça **Reboot** no app."
        )
        st.stop()
    except Exception as e:
        st.error(f"Erro ao ler o arquivo .xls: {e}")
        st.stop()

df_clt = read_xls(file_clt)
df_pj  = read_xls(file_pj)    

# =========================================================
# SALVA NA SESSÃO
# =========================================================
st.session_state["df_clt"] = df_clt
st.session_state["df_pj"] = df_pj
st.session_state["df_base"] = df_base
st.session_state["data_upload"] = pd.Timestamp.now()

# =========================================================
# FEEDBACK
# =========================================================
st.success(
    f"✅ Dados carregados com sucesso!\n\n"
    f"CLT: {len(df_clt)} registros | PJ: {len(df_pj)} registros"
)

st.markdown(
    "➡️ Agora navegue pelas páginas **Turnover**, **Tempo de Casa** ou **Assistente IA**."
)
