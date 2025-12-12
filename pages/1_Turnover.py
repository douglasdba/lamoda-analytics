import streamlit as st
import pandas as pd
import plotly.express as px
from calendar import monthrange
from io import BytesIO
from login import require_login
from pathlib import Path

require_login()

# ==============================================================
# 1) CARREGAR BASE TRATADA
# ==============================================================

# ==============================================================
# CONFIGURAÇÃO DE CAMINHOS (PADRÃO SEGURO)
# ==============================================================

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_ROOT = BASE_DIR.parent / "lamoda_dados"
DATA_DIR = DATA_ROOT / "data"


@st.cache_data(show_spinner="Carregando base de dados…")
def load_data():
    if not (DATA_DIR / "base_tratada.csv").exists():
        st.error(
        "Base de dados não encontrada.\n\n"
        "Execute o process_data.py localmente para gerar a base tratada."
    )
    st.stop()

    df = pd.read_csv(DATA_DIR / "base_tratada.csv", sep=",", encoding="utf-8")
    # Datas
    df["Admissão"] = pd.to_datetime(df["Admissão"], errors="coerce")
    df["Data Afastamento"] = pd.to_datetime(df["Data Afastamento"], errors="coerce")

    # Garantir inteiros nas colunas auxiliares
    for col in ["Ano_Admissao", "Mes_Admissao", "Ano_Afastamento", "Mes_Afastamento"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    return df


df = load_data()

# Anos e áreas disponíveis
anos_disponiveis = sorted(
    set(
        df["Ano_Admissao"].replace(0, pd.NA).dropna().unique().tolist()
        + df["Ano_Afastamento"].replace(0, pd.NA).dropna().unique().tolist()
    )
)
if not anos_disponiveis:
    anos_disponiveis = [2023, 2024, 2025]

areas_disponiveis = sorted(df["Area"].dropna().unique().tolist())

# ==============================================================
# 2) BARRA LATERAL – FILTROS
# ==============================================================

with st.sidebar:
    st.header("Filtros")

    # -----------------------------
    # Filtro de ANOS (com "Todos" + ordenação)
    # -----------------------------
    opcao_todos_anos = "Todos os anos"

    anos_opcoes = [opcao_todos_anos] + [str(a) for a in anos_disponiveis]

    anos_selecionados_raw = st.multiselect(
        "Selecione os anos:",
        options=anos_opcoes,
        default=[opcao_todos_anos],
    )

    # Lógica dos anos (sempre ordenados)
    if (not anos_selecionados_raw) or (opcao_todos_anos in anos_selecionados_raw):
        anos_selecionados = anos_disponiveis
    else:
        anos_selecionados = sorted([int(a) for a in anos_selecionados_raw])

    # -----------------------------
    # Filtro de ÁREAS
    # -----------------------------
    areas_selecionadas = st.multiselect(
        "Selecione as Áreas:",
        options=areas_disponiveis,
        default=areas_disponiveis,
    )
    if not areas_selecionadas:
        areas_selecionadas = areas_disponiveis

    st.markdown("### ⚙️ Opções — Turnover por Centro de Custo")

    op_filtrar_cc_pequenos = st.checkbox(
        "Excluir centros com poucos colaboradores", value=True
    )

    min_ativos = st.slider(
        "Mínimo de colaboradores",
        min_value=1, max_value=20, value=8,
    )

    op_agrupar_pequenos = st.checkbox(
        "Agrupar centros pequenos em 'Outros'", value=False
    )

    op_exibir_aviso = st.checkbox(
        "Mostrar aviso sobre CC pequenos", value=True
    )

# Filtra a base apenas pelas áreas (anos são tratados nas funções/anos_selecionados)
df_area = df[df["Area"].isin(areas_selecionadas)].copy()

if df_area.empty:
    st.error("Nenhum dado encontrado para as áreas selecionadas.")
    st.stop()


# ==============================================================
# 3) EXPORTAÇÃO — EXCEL + PNG
# ==============================================================

def exportar_excel(df_export):
    output = BytesIO()
    # usando openpyxl para evitar erro de xlsxwriter
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_export.to_excel(writer, index=False, sheet_name="Dados")
    return output.getvalue()


def exportar_grafico_png(fig):
    buffer = BytesIO()
    # requer kaleido instalado: pip install -U kaleido
    fig.write_image(buffer, format="png")
    return buffer.getvalue()


# ==============================================================
# 4) FUNÇÕES DE CÁLCULO – PADRÃO
# ==============================================================

def turnover_moderno(adm, dem, ativos_ini, ativos_fim):
    ativos_med = (ativos_ini + ativos_fim) / 2
    return ((adm + dem) / 2) / ativos_med * 100 if ativos_med > 0 else 0


def turnover_total_colab(adm, dem, total_colab):
    return ((adm + dem) / 2) / total_colab * 100 if total_colab > 0 else 0


def calcular_turnover_periodo(df_base, ano, fim_perfil=None):
    """
    Turnover anual geral usando suas fórmulas originais.
    """
    df_local = df_base.copy()

    if fim_perfil is None:
        periodo_start = pd.Timestamp(f"{ano}-01-01")
        periodo_end = pd.Timestamp(f"{ano}-12-31")
    else:
        periodo_start = pd.Timestamp(f"{ano}-01-01")
        periodo_end = pd.Timestamp(fim_perfil)

    df_local["É_Desligamento"] = ~df_local["Causa Escrita"].isin(["ATIVO", "Morte"])

    # Admissões dentro do período
    adm = df_local[
        (df_local["Admissão"] >= periodo_start)
        & (df_local["Admissão"] <= periodo_end)
    ].shape[0]

    # Desligamentos válidos dentro do período
    dem = df_local[
        (df_local["É_Desligamento"])
        & (df_local["Data Afastamento"] >= periodo_start)
        & (df_local["Data Afastamento"] <= periodo_end)
    ].shape[0]

    # Ativos no início
    ativos_ini = df_local[
        (df_local["Admissão"] <= periodo_start)
        & (
            df_local["Data Afastamento"].isna()
            | (df_local["Data Afastamento"] > periodo_start)
        )
    ].shape[0]

    # Ativos no fim
    ativos_fim = df_local[
        (df_local["Admissão"] <= periodo_end)
        & (
            df_local["Data Afastamento"].isna()
            | (df_local["Data Afastamento"] > periodo_end)
        )
    ].shape[0]

    ativos_medios = (ativos_ini + ativos_fim) / 2

    turn1 = turnover_moderno(adm, dem, ativos_ini, ativos_fim)
    turn2 = turnover_total_colab(adm, dem, ativos_fim)

    return {
        "Ano": ano,
        "Admissões": adm,
        "Desligamentos": dem,
        "Ativos início": ativos_ini,
        "Ativos fim": ativos_fim,
        "Ativos médios": round(ativos_medios, 2),
        "Turnover Moderno (%)": round(turn1, 2),
        "Turnover Alternativo (%)": round(turn2, 2),
    }


def turnover_por_area(df_base, ano, fim_periodo=None):
    """
    Turnover anual por Área (Varejo / Indústria / Matriz).
    """
    df_local = df_base.copy()

    if fim_periodo is None:
        ini = pd.Timestamp(f"{ano}-01-01")
        fim = pd.Timestamp(f"{ano}-12-31")
    else:
        ini = pd.Timestamp(f"{ano}-01-01")
        fim = pd.Timestamp(fim_periodo)

    df_local["É_Desligamento"] = ~df_local["Causa Escrita"].isin(["ATIVO", "Morte"])

    areas = df_local["Area"].dropna().unique()
    linhas = []

    for area in areas:
        sub = df_local[df_local["Area"] == area]

        adm = sub[(sub["Admissão"] >= ini) & (sub["Admissão"] <= fim)].shape[0]

        dem = sub[
            (sub["É_Desligamento"])
            & (sub["Data Afastamento"] >= ini)
            & (sub["Data Afastamento"] <= fim)
        ].shape[0]

        ativos_ini = sub[
            (sub["Admissão"] <= ini)
            & (
                sub["Data Afastamento"].isna()
                | (sub["Data Afastamento"] > ini)
            )
        ].shape[0]

        ativos_fim = sub[
            (sub["Admissão"] <= fim)
            & (
                sub["Data Afastamento"].isna()
                | (sub["Data Afastamento"] > fim)
            )
        ].shape[0]

        turn_mod = turnover_moderno(adm, dem, ativos_ini, ativos_fim)
        turn_alt = turnover_total_colab(adm, dem, ativos_fim)

        linhas.append(
            {
                "Ano": ano,
                "Área": area,
                "Admissões": adm,
                "Desligamentos": dem,
                "Ativos início": ativos_ini,
                "Ativos fim": ativos_fim,
                "Ativos médios": round((ativos_ini + ativos_fim) / 2, 2),
                "Turnover Moderno (%)": round(turn_mod, 2),
                "Turnover Alternativo (%)": round(turn_alt, 2),
            }
        )

    return pd.DataFrame(linhas)


def turnover_por_centro_custo(df_base, ano):
    """
    Calcula turnover por Centro de Custo (Descrição C.Custo) para um ano específico.
    Usa a fórmula TURNOVER ALTERNATIVO = (Adm + Dem) / (2 × Ativos_fim)
    """
    ini = pd.Timestamp(f"{ano}-01-01")
    fim = pd.Timestamp(f"{ano}-12-31")

    df_local = df_base.copy()
    df_local["É_Desligamento"] = ~df_local["Causa Escrita"].isin(["ATIVO", "Morte"])

    centros = df_local["Descrição (C.Custo)"].dropna().unique()

    resultados = []

    for cc in centros:
        sub = df_local[df_local["Descrição (C.Custo)"] == cc]

        adm = sub[(sub["Admissão"] >= ini) & (sub["Admissão"] <= fim)].shape[0]

        dem = sub[
            (sub["É_Desligamento"])
            & (sub["Data Afastamento"] >= ini)
            & (sub["Data Afastamento"] <= fim)
        ].shape[0]

        ativos_fim = sub[
            (sub["Admissão"] <= fim)
            & (
                sub["Data Afastamento"].isna()
                | (sub["Data Afastamento"] > fim)
            )
        ].shape[0]

        if ativos_fim == 0:
            turnover = 0
        else:
            turnover = ((adm + dem) / (2 * ativos_fim)) * 100

        resultados.append({
            "Centro de Custo": cc,
            "Admissões": adm,
            "Desligamentos": dem,
            "Ativos Fim": ativos_fim,
            "Turnover (%)": round(turnover, 2),
        })

    df_cc = pd.DataFrame(resultados)
    df_cc = df_cc.sort_values("Turnover (%)", ascending=False)

    return df_cc


def turnover_por_cc(df_base, ano):
    """
    Versão com switches (ON/OFF) para filtros de CC pequenos e agrupamento em 'Outros'.
    Fórmula de turnover continua sendo a mesma.
    """
    df_local = df_base.copy()

    lista = []
    centros = df_local["Descrição (C.Custo)"].dropna().unique()

    for cc in centros:
        sub = df_local[df_local["Descrição (C.Custo)"] == cc]

        adm = sub[(sub["Ano_Admissao"] == ano)].shape[0]
        dem = sub[(sub["Ano_Afastamento"] == ano)].shape[0]

        fim = pd.Timestamp(f"{ano}-12-31")
        ativos_fim = sub[
            (sub["Admissão"] <= fim)
            & (
                sub["Data Afastamento"].isna()
                | (sub["Data Afastamento"] > fim)
            )
        ].shape[0]

        if ativos_fim > 0:
            turnover = ((adm + dem) / (2 * ativos_fim)) * 100
        else:
            turnover = 0

        lista.append(
            {
                "Centro de Custo": cc,
                "Admissões": adm,
                "Desligamentos": dem,
                "Ativos Fim": ativos_fim,
                "Turnover (%)": round(turnover, 2),
            }
        )

    df_cc = pd.DataFrame(lista)

    # 1) Filtrar CC pequenos
    if op_filtrar_cc_pequenos:
        df_cc = df_cc[df_cc["Ativos Fim"] >= min_ativos]

    # 2) Agrupar CC pequenos em "Outros"
    if op_agrupar_pequenos:
        pequenos = df_cc[df_cc["Ativos Fim"] < min_ativos]
        grandes = df_cc[df_cc["Ativos Fim"] >= min_ativos]

        if not pequenos.empty:
            soma = pequenos.sum(numeric_only=True)
            turnover_outros = (
                (soma["Admissões"] + soma["Desligamentos"]) /
                (2 * soma["Ativos Fim"])
            ) * 100 if soma["Ativos Fim"] > 0 else 0

            linha_outros = {
                "Centro de Custo": "OUTROS (Centros Pequenos)",
                "Admissões": int(soma["Admissões"]),
                "Desligamentos": int(soma["Desligamentos"]),
                "Ativos Fim": int(soma["Ativos Fim"]),
                "Turnover (%)": round(turnover_outros, 2),
            }
            df_cc = pd.concat([grandes, pd.DataFrame([linha_outros])], ignore_index=True)

    return df_cc.sort_values("Turnover (%)", ascending=False)


# ==============================================================
# 5) FUNÇÕES MENSAL – MESMA LÓGICA DO JUPYTER
# ==============================================================

def admissoes_mes(df_base, ano, mes):
    return df_base[
        (df_base["Ano_Admissao"] == ano)
        & (df_base["Mes_Admissao"] == mes)
    ].shape[0]


def demissoes_mes(df_base, ano, mes):
    return df_base[
        (df_base["Ano_Afastamento"] == ano)
        & (df_base["Mes_Afastamento"] == mes)
    ].shape[0]


def ativos_no_fim_mes(df_base, ano, mes):
    ultimo_dia = monthrange(ano, mes)[1]
    ref = pd.Timestamp(year=ano, month=mes, day=ultimo_dia)

    ativos = df_base[
        (df_base["Admissão"] <= ref)
        & (
            df_base["Data Afastamento"].isna()
            | (df_base["Data Afastamento"] > ref)
        )
    ]
    return ativos.shape[0]


def montar_tabela_mensal_area(df_base, anos, area_label=None):
    """
    Monta tabela mensal com Turnover(%) = ((Adm + Dem) / (2 * Ativos)) * 100
    Se area_label == 'Varejo', aplica o ajuste específico de nov/2025,
    replicando exatamente o seu notebook.
    """
    linhas = []

    for ano in anos:
        for mes in range(1, 13):
            adm = admissoes_mes(df_base, ano, mes)
            dem = demissoes_mes(df_base, ano, mes)
            ativos = ativos_no_fim_mes(df_base, ano, mes)

            linhas.append(
                {
                    "Ano": ano,
                    "Mês": mes,
                    "Ano-Mês": f"{ano}-{mes:02d}",
                    "Admissões": adm,
                    "Demissões": dem,
                    "Ativos no Final do Mês": ativos,
                }
            )

    tabela = pd.DataFrame(linhas)

    # -------------------------
    # Ajuste específico VAREJO
    # -------------------------
    if area_label == "Varejo" and 2025 in anos:
        mask_nov = (tabela["Ano"] == 2025) & (tabela["Mês"] == 11)
        mask_out = (tabela["Ano"] == 2025) & (tabela["Mês"] == 10)

        if mask_nov.any() and mask_out.any():
            ativos_outubro = tabela.loc[mask_out, "Ativos no Final do Mês"].iloc[0]

            tabela.loc[mask_nov, "Admissões"] = 12
            tabela.loc[mask_nov, "Demissões"] = 14
            tabela.loc[mask_nov, "Ativos no Final do Mês"] = ativos_outubro + 12 - 15

    tabela["Turnover (%)"] = (
        (tabela["Admissões"] + tabela["Demissões"])
        / (2 * tabela["Ativos no Final do Mês"].replace(0, pd.NA))
    ) * 100
    tabela["Turnover (%)"] = tabela["Turnover (%)"].fillna(0).round(2)

    return tabela


# ==============================================================
# 6) INTERFACE – DASHBOARD
# ==============================================================

st.title("📉 Dashboard de Turnover — La Moda")
st.markdown("**Painel • Filtros • KPIs • Gráficos**")
st.markdown(
    """
**📅 Dados atualizados em: 02/12/2025**  
**📂 Fonte: Sistema Senior**
"""
)

# ---------- RESUMO EXECUTIVO ----------
st.markdown("## 📌 Resumo — Visão Rápida do Turnover")

ano_atual = max(anos_selecionados)

# Turnover geral do ano atual (filtrado pelas áreas selecionadas)
turnover_atual = calcular_turnover_periodo(df_area, ano_atual)
turnover_valor = turnover_atual["Turnover Alternativo (%)"]

# Área padrão para o resumo mensal
if "Varejo" in df_area["Area"].unique():
    area_resumo = "Varejo"
else:
    area_resumo = df_area["Area"].unique()[0]

sub_resumo = df[df["Area"] == area_resumo].copy()
tabela_mensal_resumo = montar_tabela_mensal_area(sub_resumo, [ano_atual], area_label=area_resumo)
media_mensal = (
    tabela_mensal_resumo[tabela_mensal_resumo["Ano"] == ano_atual]["Turnover (%)"]
    .mean()
    .round(2)
)

df_area_atual = turnover_por_area(df_area, ano_atual)
if not df_area_atual.empty:
    maior_area = df_area_atual.sort_values("Turnover Moderno (%)", ascending=False).iloc[0]
    menor_area = df_area_atual.sort_values("Turnover Moderno (%)", ascending=True).iloc[0]
else:
    maior_area = menor_area = None

adm_total = turnover_atual["Admissões"]
dem_total = turnover_atual["Desligamentos"]

# 🔵 HEADCOUNT — total de colaboradores ativos nas áreas filtradas
headcount = df_area[df_area["Situacao_res"] == "Ativo"].shape[0]

col1, col2, col3, col4 = st.columns(4)
col1.metric("📉 Turnover Atual", f"{turnover_valor:.2f}%")
col2.metric("📈 Média Mensal do Ano", f"{media_mensal:.2f}%")
col3.metric(
    "📊 Maior Turnover",
    f"{maior_area['Área']} — {maior_area['Turnover Moderno (%)']:.2f}%"
    if maior_area is not None
    else "—",
)
col4.metric(
    "📉 Menor Turnover",
    f"{menor_area['Área']} — {menor_area['Turnover Moderno (%)']:.2f}%"
    if menor_area is not None
    else "—",
)

col5, col6, col7 = st.columns(3)
col5.metric("🟦 Total de Admissões", adm_total)
col6.metric("🟥 Total de Demissões", dem_total)
col7.metric("👥 Headcount (Ativos)", headcount)

st.markdown("### 📈 Tendência Anual do Turnover (Alternativo)")

df_turnover_resumo = pd.DataFrame(
    [calcular_turnover_periodo(df_area, ano) for ano in anos_selecionados]
)

fig_resumo = px.line(
    df_turnover_resumo,
    x="Ano",
    y="Turnover Alternativo (%)",
    markers=True,
    text="Turnover Alternativo (%)"
)

fig_resumo.update_traces(
    texttemplate="%{text:.2f}%",
    textposition="top center",
    hovertemplate="Ano: %{x}<br>Turnover: %{y:.2f}%"
)

fig_resumo.update_layout(height=260, margin=dict(l=20, r=20, t=20, b=20))
st.plotly_chart(fig_resumo, use_container_width=True)

st.download_button(
    label="📸 Baixar PNG – Tendência Anual",
    data=exportar_grafico_png(fig_resumo),
    file_name="tendencia_anual_turnover.png",
    mime="image/png",
)

st.markdown(f"### 📊 Tendência Mensal — {ano_atual} ({area_resumo})")

fig_mensal_resumo = px.line(
    tabela_mensal_resumo[tabela_mensal_resumo["Ano"] == ano_atual],
    x="Mês",
    y="Turnover (%)",
    markers=True,
    text="Turnover (%)"
)

fig_mensal_resumo.update_traces(
    texttemplate="%{text:.2f}%",
    textposition="top center",
    hovertemplate="Mês: %{x}<br>Turnover: %{y:.2f}%"
)

fig_mensal_resumo.update_layout(height=260, margin=dict(l=20, r=20, t=20, b=20))
st.plotly_chart(fig_mensal_resumo, use_container_width=True)

st.download_button(
    label="📸 Baixar PNG – Tendência Mensal",
    data=exportar_grafico_png(fig_mensal_resumo),
    file_name="tendencia_mensal_turnover.png",
    mime="image/png",
)

st.markdown("---")

# ---------- ESCOLHA DA ANÁLISE ----------
analise = st.radio(
    "Escolha a análise:",
    ["Visão Geral", "Turnover por Área", "Turnover Mensal", "Turnover por Centro de Custo"],
)

st.markdown("---")

# ==============================================================
# 6.1 VISÃO GERAL
# ==============================================================

if analise == "Visão Geral":
    st.subheader("📊 Turnover Geral (Todos os Colaboradores)")

    df_turnover = pd.DataFrame(
        [calcular_turnover_periodo(df_area, ano) for ano in anos_selecionados]
    )
    st.dataframe(df_turnover, use_container_width=True)

    st.download_button(
        label="⬇️ Baixar Excel – Turnover Geral",
        data=exportar_excel(df_turnover),
        file_name="turnover_geral.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.markdown("##### KPIs por Ano (Turnover Alternativo)")
    cols = st.columns(len(anos_selecionados))
    for col, ano in zip(cols, anos_selecionados):
        linha = df_turnover[df_turnover["Ano"] == ano]
        if linha.empty:
            valor = "–"
        else:
            valor = f"{linha['Turnover Alternativo (%)'].values[0]:.2f}%"
        col.metric(f"Turnover {ano}", valor)

    tipo_grafico_geral = st.radio(
        "Tipo de gráfico para a visão geral:",
        ["Linha", "Barras"],
        horizontal=True,
        key="graf_geral",
    )

    if tipo_grafico_geral == "Linha":
        fig = px.line(
            df_turnover,
            x="Ano",
            y=["Turnover Moderno (%)", "Turnover Alternativo (%)"],
            markers=True,
            title="Evolução Anual do Turnover",
        )
    else:
        fig = px.bar(
            df_turnover,
            x="Ano",
            y=["Turnover Moderno (%)", "Turnover Alternativo (%)"],
            barmode="group",
            title="Turnover Anual – Comparação de Fórmulas",
        )

    fig.update_layout(legend_title_text="Fórmula", xaxis_title="Ano")
    st.plotly_chart(fig, use_container_width=True)

# ==============================================================
# 6.2 TURNOVER POR ÁREA
# ==============================================================

elif analise == "Turnover por Área":
    st.subheader("🏢 Turnover por Área (Varejo / Indústria / Matriz)")

    df_area_anual = pd.concat(
        [turnover_por_area(df_area, ano) for ano in anos_selecionados],
        ignore_index=True,
    )

    if df_area_anual.empty:
        st.warning("Não há registros de turnover para essas combinações de ano e área.")
        st.stop()

    st.dataframe(df_area_anual, use_container_width=True)

    st.download_button(
        label="⬇️ Baixar Excel – Turnover por Área",
        data=exportar_excel(df_area_anual),
        file_name="turnover_por_area.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    tipo_grafico_area = st.radio(
        "Tipo de gráfico:",
        ["Barras agrupadas", "Linha"],
        horizontal=True,
        key="graf_area",
    )

    if tipo_grafico_area == "Linha":
        fig2 = px.line(
            df_area_anual,
            x="Ano",
            y="Turnover Moderno (%)",
            color="Área",
            markers=True,
            title="Evolução do Turnover por Área",
        )
    else:
        fig2 = px.bar(
            df_area_anual,
            x="Área",
            y="Turnover Moderno (%)",
            color="Ano",
            barmode="group",
            title="Turnover por Área e Ano",
        )

    fig2.update_yaxes(title="Turnover Moderno (%)", showgrid=False)
    st.plotly_chart(fig2, use_container_width=True)

# ==============================================================
# 6.3 TURNOVER MENSAL
# ==============================================================

elif analise == "Turnover Mensal":
    st.subheader("📆 Turnover Mensal — Geral e por Área")

    # Áreas
    areas_escolhidas = st.multiselect(
        "Selecione as Áreas:",
        options=areas_selecionadas,
        default=areas_selecionadas,
    )
    if not areas_escolhidas:
        st.warning("Selecione pelo menos uma área.")
        st.stop()

    # Anos
    anos_mensal = st.multiselect(
        "Selecione os anos:",
        options=anos_selecionados,
        default=anos_selecionados,
    )
    if not anos_mensal:
        st.warning("Selecione pelo menos um ano.")
        st.stop()

    anos_mensal = sorted(anos_mensal)

    # Tabelas por área
    tabelas = []
    for area in areas_escolhidas:
        sub_area = df[df["Area"] == area].copy()
        tabela_area = montar_tabela_mensal_area(sub_area, anos_mensal, area_label=area)
        tabela_area["Área"] = area
        tabelas.append(tabela_area)

    # Tabela do TOTAL GERAL (considerando todas as áreas selecionadas)
    sub_geral = df[df["Area"].isin(areas_escolhidas)].copy()
    tabela_geral = montar_tabela_mensal_area(sub_geral, anos_mensal, area_label="Geral")
    tabela_geral["Área"] = "Geral"
    tabelas.append(tabela_geral)

    # Junta tudo
    tabela_final = pd.concat(tabelas, ignore_index=True)
    tabela_final = tabela_final.sort_values(["Área", "Ano", "Mês"])

    st.dataframe(tabela_final, use_container_width=True)

    st.download_button(
        label="⬇️ Baixar Excel – Turnover Mensal",
        data=exportar_excel(tabela_final),
        file_name="turnover_mensal.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    # Gráfico linha comparando Geral x Áreas
    fig = px.line(
        tabela_final,
        x="Mês",
        y="Turnover (%)",
        color="Área",
        line_group="Ano",
        markers=True,
        facet_col="Ano",
        text="Turnover (%)",
        title="Turnover Mensal — Comparativo Geral e por Área",
    )

    fig.update_traces(
        texttemplate="%{text:.2f}%",
        textposition="top center",
        hovertemplate="Área: %{legendgroup}<br>Mês: %{x}<br>Turnover: %{y:.2f}%"
    )

    fig.update_yaxes(showgrid=False)
    st.plotly_chart(fig, use_container_width=True)

# ==============================================================
# 6.4 TURNOVER POR CENTRO DE CUSTO
# ==============================================================

elif analise == "Turnover por Centro de Custo":
    st.subheader("🏬 Turnover por Centro de Custo (15 maiores)")

    ano_cc = st.selectbox(
        "Selecione o ano:",
        anos_selecionados,
        index=len(anos_selecionados) - 1
    )

    df_cc = turnover_por_cc(df_area, ano_cc)

    # Tabela completa
    st.dataframe(df_cc, use_container_width=True)

    st.download_button(
        label="⬇️ Baixar Excel – Turnover por CC",
        data=exportar_excel(df_cc),
        file_name=f"turnover_por_cc_{ano_cc}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    if op_exibir_aviso:
        st.info(
            "Centros com poucos colaboradores podem apresentar percentuais de turnover muito altos ou voláteis. "
            "Use os filtros e o agrupamento em 'Outros' para reduzir distorções."
        )

    # Seleciona os 15 maiores
    top15 = df_cc.head(15)

    st.markdown("### 🔝 15 Centros de Custo com Maior Turnover")

    fig_cc = px.bar(
        top15[::-1],  # invertido para aparecer do maior para o menor
        x="Turnover (%)",
        y="Centro de Custo",
        orientation="h",
        text="Turnover (%)",
        title=f"Top 15 – Turnover por Centro de Custo ({ano_cc})",
    )

    fig_cc.update_traces(
        texttemplate="%{text:.2f}%",
        textposition="outside",
        marker_color="#6B7280",
    )

    fig_cc.update_layout(
        xaxis_title="Turnover (%)",
        yaxis_title="",
        margin=dict(l=50, r=30, t=60, b=20),
    )

    st.plotly_chart(fig_cc, use_container_width=True)
