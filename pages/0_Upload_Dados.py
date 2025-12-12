import streamlit as st
import pandas as pd
import numpy as np
from datetime import date
import re
from login import require_login

require_login()

st.set_page_config(
    page_title="Upload de Dados — La Moda BI",
    page_icon="📤",
    layout="wide"
)

st.title("📤 Upload de Dados — La Moda BI")
st.markdown(
    "Faça o upload dos arquivos **CLT** e **PJ** no formato `.xls`.\n\n"
    "⚠️ Os dados **não são salvos** e **não ficam no GitHub**."
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
# PROCESSAMENTO (MESMA LÓGICA DO process_data.py)
# =========================================================

with st.spinner("Processando dados..."):

    df = pd.read_excel(file_clt, engine="xlrd")
    df2 = pd.read_excel(file_pj, engine="xlrd")

    # ---------------- LIMPEZA INICIAL ----------------
    def limpeza_inicial(d):
        d = d.dropna(how="all").reset_index(drop=True)
        return d.drop(columns=["Posição do Local", "Cadastro"], errors="ignore")

    df = limpeza_inicial(df)
    df2 = limpeza_inicial(df2)

    # ---------------- REMOÇÃO DE CARGOS ----------------
    padrao_clt = r"JOVEM APRENDIZ|ESTAGIARI[OA]|APRENDIZ"
    padrao_pj = r"PRESTADOR DE SERVIÇO|SERVENTE DE ZELADORIA|ESPEC\.? DE SERV\.? DE LAVANDERIA"

    cargos_remover_df2 = [
        "MEDICO DE TRABALHO","FAXINEIRO","MODELO DE PROVA","NUTRICIONISTA","SECRETARIA",
        "MOTORISTA","PROFESSOR DE INGLES","ESTOQUISTA","IMPRESSOR DE ADESIVOS",
        "ZELADORA","ZELADOR","VIGILANTE","COACHING","AN ADM PESSOAL I"
    ]

    padrao_df2_extra = r"|".join(map(re.escape, cargos_remover_df2))

    df = df[~df["Título Reduzido (Cargo)"].str.contains(padrao_clt, case=False, na=False)]
    df2 = df2[~df2["Título Reduzido (Cargo)"].str.contains(padrao_df2_extra, case=False, na=False)]
    df2 = df2[~df2["Título Reduzido (Cargo)"].str.contains(padrao_pj, case=False, na=False)]

    # ---------------- DATAS ----------------
    DATE_COLS = ["Nascimento", "Admissão", "Data Afastamento"]

    def tratar_datas(d):
        for col in DATE_COLS:
            d[col] = (
                d[col].astype(str)
                .str.strip()
                .replace(["", " ", "0", "00/00/0000", "--", "NaT", "nan"], pd.NA)
            )
            d[col] = pd.to_datetime(d[col], errors="coerce")
        return d

    df = tratar_datas(df)
    df2 = tratar_datas(df2)

    def calc_idade(dt):
        if pd.isna(dt):
            return 0
        return int((date.today() - dt.date()).days / 365.25)

    for d in (df, df2):
        d["Idade"] = d["Nascimento"].apply(calc_idade)
        d["Mes_Admissao"] = d["Admissão"].dt.month.fillna(0).astype(int)
        d["Ano_Admissao"] = d["Admissão"].dt.year.fillna(0).astype(int)
        d["Mes_Afastamento"] = d["Data Afastamento"].dt.month.fillna(0).astype(int)
        d["Ano_Afastamento"] = d["Data Afastamento"].dt.year.fillna(0).astype(int)

    # ---------------- SITUAÇÃO ----------------
    situacoes_ativas = ["Trabalhando", "Férias", "Licença Maternidade", "Atestado Médico"]

    df["Situacao_res"] = np.where(df["Situação"].isin([1, 2, 3, 4]), "Ativo", "Desligado/Afastado")
    df2["Situacao_res"] = np.where(df2["Situação"].isin([1, 2, 3, 4]), "Ativo", "Desligado/Afastado")

    # ---------------- ÁREA ----------------
    def classificar_area(cc):
        cc = str(cc).upper()
        if "LOJAS" in cc:
            return "Varejo"
        if "SUPPLY" in cc:
            return "Indústria"
        return "Matriz"

    for d in (df, df2):
        d["Area"] = d["C.Custo"].astype(str).apply(classificar_area)

    # ---------------- UNIFICA ----------------
    df["TIPO"] = "CLT"
    df2["TIPO"] = "PJ"

    df_final = pd.concat([df, df2], ignore_index=True)

# =========================================================
# SALVA EM MEMÓRIA
# =========================================================

st.session_state["base_tratada"] = df_final

st.success(f"✅ Base carregada com sucesso! Registros: {len(df_final)}")

st.markdown(
    "➡️ Agora navegue pelas páginas **Turnover**, **Tempo de Casa** ou **Assistente IA**."
)
