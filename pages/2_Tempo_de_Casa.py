import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from login import require_login
from pathlib import Path


require_login()


# ==============================================================
# CONFIGURAÇÃO DE CAMINHOS (PADRÃO SEGURO)
# ==============================================================

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_ROOT = BASE_DIR.parent / "lamoda_dados"
DATA_DIR = DATA_ROOT / "data"


st.set_page_config(page_title="Tempo de Casa", page_icon="🏡", layout="wide")

# ==============================================================
# 1) GERAR / CARREGAR tempo_de_casa.csv A PARTIR DA base_tratada.csv
# ==============================================================

@st.cache_data(show_spinner="Carregando base de tempo de casa…")
def load_tempo_casa():
    path = DATA_DIR / "tempo_de_casa.csv"

    if not path.exists():
        st.error(
            "Base tempo_de_casa.csv não encontrada.\n\n"
            "Execute o process_data.py localmente para gerar as bases."
        )
        st.stop()

    df = pd.read_csv(path, sep=",", encoding="utf-8")

    df["Admissão"] = pd.to_datetime(df["Admissão"], errors="coerce")
    df["Data Afastamento"] = pd.to_datetime(df["Data Afastamento"], errors="coerce")

    return df


df = load_tempo_casa()

# ==============================================================
# 2) FILTROS LATERAIS — ESTILO PARECIDO COM O DO TURNOVER
# ==============================================================

with st.sidebar:
    st.header("Filtros")

    areas = sorted(df["Area"].dropna().unique())
    areas_sel = st.multiselect("Selecione as Áreas", areas, default=areas)

    situacoes = ["Todos", "Ativo", "Demitido"]
    sit_sel = st.selectbox("Situação", situacoes, index=0)

    faixas = ["Todos", "0–1 ano", "1–3 anos", "3–5 anos", "5+ anos"]
    faixa_sel = st.selectbox("Faixa de Tempo de Casa", faixas)

# Aplicar filtros básicos
df_filt = df[df["Area"].isin(areas_sel)].copy()

if sit_sel == "Ativo":
    df_filt = df_filt[df_filt["Situacao_res"] == "Ativo"]
elif sit_sel == "Demitido":
    df_filt = df_filt[df_filt["Situacao_res"] != "Ativo"]

# Filtro por faixa de tempo de casa
if faixa_sel == "0–1 ano":
    df_filt = df_filt[df_filt["Anos_de_Casa"] <= 1]
elif faixa_sel == "1–3 anos":
    df_filt = df_filt[(df_filt["Anos_de_Casa"] > 1) & (df_filt["Anos_de_Casa"] <= 3)]
elif faixa_sel == "3–5 anos":
    df_filt = df_filt[(df_filt["Anos_de_Casa"] > 3) & (df_filt["Anos_de_Casa"] <= 5)]
elif faixa_sel == "5+ anos":
    df_filt = df_filt[df_filt["Anos_de_Casa"] > 5]

# Se depois de tudo não sobrou ninguém, avisa e encerra
if df_filt.empty:
    st.title("🏡 Tempo de Casa — Dashboard Oficial")
    st.warning("Nenhum registro encontrado para os filtros selecionados.")
    st.stop()

# ==============================================================
# 3) RESUMO EXECUTIVO (KPIs)
# ==============================================================

st.title("🏡 Tempo de Casa — Dashboard Oficial")
st.success("✔ Arquivo carregado com sucesso!")

def safe_mean(series):
    """Retorna média arredondada ou '—' caso esteja vazia."""
    if series.empty:
        return "—"
    media = series.mean()
    if pd.isna(media):
        return "—"
    return round(media, 2)

# Tempos médios
tempo_medio_geral = safe_mean(df_filt["Anos_de_Casa"])
tempo_ativos = safe_mean(df_filt[df_filt["Situacao_res"] == "Ativo"]["Anos_de_Casa"])
tempo_desligados = safe_mean(df_filt[df_filt["Situacao_res"] != "Ativo"]["Anos_de_Casa"])

# Headcount ativo
headcount_ativos = df_filt[df_filt["Situacao_res"] == "Ativo"].shape[0]

total = len(df_filt)

def calc_pct(mask):
    """Calcula percentual com proteção contra divisões inválidas."""
    qtd = df_filt[mask].shape[0]
    return f"{round((qtd / total) * 100, 1)}%" if total > 0 else "0%"

pct_ate_1 = calc_pct(df_filt["Anos_de_Casa"] <= 1)
pct_1_3  = calc_pct((df_filt["Anos_de_Casa"] > 1) & (df_filt["Anos_de_Casa"] <= 3))
pct_3_5  = calc_pct((df_filt["Anos_de_Casa"] > 3) & (df_filt["Anos_de_Casa"] <= 5))
pct_5p   = calc_pct(df_filt["Anos_de_Casa"] > 5)

# KPIs principais
col1, col2, col3, col4 = st.columns(4)
col1.metric("⏳ Tempo Médio (Geral)", f"{tempo_medio_geral} anos")
col2.metric("🟩 Tempo Médio (Ativos)", f"{tempo_ativos} anos")
col3.metric("🟥 Tempo Médio (Desligados)", f"{tempo_desligados} anos")
col4.metric("👥 Headcount Ativo", headcount_ativos)

# Distribuição por faixas
col5, col6, col7, col8 = st.columns(4)
col5.metric("0–1 ano", pct_ate_1)
col6.metric("1–3 anos", pct_1_3)
col7.metric("3–5 anos", pct_3_5)
col8.metric("5+ anos", pct_5p)


# ==============================================================
# 4) GRÁFICOS
# ==============================================================

st.markdown("## 📊 Distribuição do Tempo de Casa (anos)")
fig_hist = px.histogram(
    df_filt,
    x="Anos_de_Casa",
    nbins=30,
    color="Area",
    marginal="box",
    labels={"Anos_de_Casa": "Tempo de Casa (anos)"},
)
st.plotly_chart(fig_hist, use_container_width=True)

st.markdown("## 🏬 Tempo de Casa por Área (Boxplot)")
fig_box = px.box(
    df_filt,
    x="Area",
    y="Anos_de_Casa",
    color="Area",
    points="outliers",
    labels={"Area": "Área", "Anos_de_Casa": "Tempo de Casa (anos)"},
)
st.plotly_chart(fig_box, use_container_width=True)

st.markdown("## 🥧 Distribuição por Faixas de Tempo de Casa")

df_faixas = pd.DataFrame(
    {
        "Faixa": ["0–1 ano", "1–3 anos", "3–5 anos", "5+ anos"],
        "Quantidade": [
            df_filt[df_filt["Anos_de_Casa"] <= 1].shape[0],
            df_filt[(df_filt["Anos_de_Casa"] > 1) & (df_filt["Anos_de_Casa"] <= 3)].shape[0],
            df_filt[(df_filt["Anos_de_Casa"] > 3) & (df_filt["Anos_de_Casa"] <= 5)].shape[0],
            df_filt[df_filt["Anos_de_Casa"] > 5].shape[0],
        ],
    }
)

fig_pie = px.pie(
    df_faixas,
    names="Faixa",
    values="Quantidade",
    hole=0.4,
)
fig_pie.update_traces(textposition="inside", textinfo="percent+label")
st.plotly_chart(fig_pie, use_container_width=True)

st.markdown("---")

# ==============================================================
# 5) TABELA FINAL
# ==============================================================

st.markdown("## 📋 Base filtrada")
st.dataframe(df_filt, use_container_width=True)
