import streamlit as st
import pandas as pd
from datetime import datetime
from calendar import monthrange
import unicodedata
import re
from login import require_login
from pathlib import Path

# ======================================================
# CONFIGURAÇÃO DA PÁGINA (OBRIGATÓRIO PRIMEIRO)
# ======================================================
st.set_page_config(
    page_title="Assistente IA — La Moda BI",
    page_icon="🧠",
    layout="wide"
)


require_login()

# ======================================================
# CAMINHOS PADRÃO
# ======================================================
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_ROOT = BASE_DIR.parent / "lamoda_dados"
DATA_DIR = DATA_ROOT / "data"
STREAMLIT_DIR = BASE_DIR / ".streamlit"


# =====================================================================
# 0) CONFIGURAÇÃO GERAL + PERSONA (A ALMA DO SEU ASSISTENTE)
# =====================================================================

css_path = STREAMLIT_DIR / "styles.css"
if css_path.exists():
    st.markdown(
        f"<style>{css_path.read_text(encoding='utf-8')}</style>",
        unsafe_allow_html=True
    )



PERSONA = """
Você é o Assistente Inteligente de BI da La Moda — o “ChatGPT da La Moda”.
Seu estilo deve ser:

- Conversar como um humano de verdade
- Explicar insights de forma clara, simples e profissional
- Ser amigável, educado e sempre prestativo
- Entender português formal, informal, gírias, abreviações e erros comuns
- Falar como um consultor de BI que conhece profundamente os dados da empresa
- Trazer contexto, insights e interpretações quando fizer sentido
- Ser firme quando precisar de mais informações, mas sempre gentil

Evite linguagem muito técnica.
Use um tom natural, como alguém experiente explicando algo a um colega.
Pode usar emojis com moderação (📊, 🧠, 🔎, 👇, etc.).
Por padrão, responda como se estivesse conversando pelo chat da empresa.
"""

# =====================================================================
# 1) CARREGAR BASE TRATADA
# =====================================================================

@st.cache_data(show_spinner="Carregando base de dados…")
def load_base():
    path = DATA_DIR / "base_tratada.csv"

    if not path.exists():
        st.error(
            "Base **base_tratada.csv** não encontrada.\n\n"
            "Execute o `process_data.py` localmente para gerar a base."
        )
        st.stop()

    df = pd.read_csv(path, sep=",", encoding="utf-8")

    df["Admissão"] = pd.to_datetime(df["Admissão"], errors="coerce")
    df["Data Afastamento"] = pd.to_datetime(df["Data Afastamento"], errors="coerce")

    for col in ["Ano_Admissao", "Mes_Admissao", "Ano_Afastamento", "Mes_Afastamento"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    return df


df_base = load_base()

ANOS_DISPONIVEIS = sorted(
    set(
        df_base["Ano_Admissao"].replace(0, pd.NA).dropna().unique().tolist()
        + df_base["Ano_Afastamento"].replace(0, pd.NA).dropna().unique().tolist()
    )
)


# =====================================================================
# 2) NORMALIZAÇÃO • ENTENDE PORTUGUÊS INFORMAL, ERROS E ABREVIAÇÕES
# =====================================================================

GIRIAS = {
    "qnts": "quantos",
    "qntos": "quantos",
    "qto": "quanto",
    "td": "tudo",
    "pq": "porque",
    "p q": "porque",
    "turn": "turnover",
    "var": "varejo",
    "ind": "indústria",
    "adm": "admissão",
    "dem": "desligamento",
    "func": "colaboradores",
    "funcionario": "colaborador",
    "funcionarios": "colaboradores",
    "galera": "colaboradores",
    "empresa geral": "geral",
}

def normalizar(texto: str) -> str:
    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(ch for ch in texto if unicodedata.category(ch) != "Mn")

    for k, v in GIRIAS.items():
        texto = texto.replace(k, v)

    return texto


def extrair_anos(t):
    anos = re.findall(r"(20\d{2})", t)
    return [int(a) for a in anos]


def extrair_mes_e_ano(t):
    m = re.search(r"(\d{1,2})[/-](20\d{2})", t)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


def extrair_area(t):
    if "varejo" in t: return "Varejo"
    if "industria" in t: return "Indústria"
    if "matriz" in t: return "Matriz"
    if "geral" in t or "empresa" in t: return "Geral"
    return None


def extrair_status(t):
    if "ativo" in t and not ("deslig" in t or "demit" in t):
        return "Ativo"
    if "deslig" in t or "demit" in t:
        return "Desligado"
    return None


def filtrar_area(df, area):
    if not area or area == "Geral":
        return df
    return df[df["Area"] == area]


def turnover_moderno(a, d, ini, fim):
    med = (ini + fim) / 2
    return ((a + d) / 2) / med * 100 if med > 0 else 0


def turnover_alt(a, d, ativos_fim):
    return ((a + d) / 2) / ativos_fim * 100 if ativos_fim > 0 else 0


def calcular_turnover_anual(df, ano, area=None):
    df = filtrar_area(df, area)

    ini = pd.Timestamp(f"{ano}-01-01")
    fim = pd.Timestamp(f"{ano}-12-31")

    df["É_Desligamento"] = ~df["Causa Escrita"].isin(["ATIVO", "Morte"])

    adm = df[(df["Admissão"] >= ini) & (df["Admissão"] <= fim)].shape[0]
    dem = df[(df["É_Desligamento"]) & (df["Data Afastamento"] >= ini) & (df["Data Afastamento"] <= fim)].shape[0]

    ativos_ini = df[(df["Admissão"] <= ini) & (df["Data Afastamento"].isna() | (df["Data Afastamento"] > ini))].shape[0]
    ativos_fim = df[(df["Admissão"] <= fim) & (df["Data Afastamento"].isna() | (df["Data Afastamento"] > fim))].shape[0]

    return {
        "Ano": ano,
        "Admissões": adm,
        "Desligamentos": dem,
        "Ativos início": ativos_ini,
        "Ativos fim": ativos_fim,
        "Turnover Alternativo (%)": round(turnover_alt(adm, dem, ativos_fim), 2),
        "Turnover Moderno (%)": round(turnover_moderno(adm, dem, ativos_ini, ativos_fim), 2),
    }


def interpretar_intencao(pergunta: str):
    t = normalizar(pergunta)

    area = extrair_area(t)
    status = extrair_status(t)
    anos = extrair_anos(t)
    mes, ano_mes = extrair_mes_e_ano(t)

    if "turnover" in t:
        if mes and ano_mes:
            return {"tipo": "turnover_mensal", "area": area, "ano": ano_mes, "mes": mes}

        if "maior" in t or "pior" in t:
            return {"tipo": "turnover_max"}

        if anos:
            return {"tipo": "turnover_anual", "area": area, "anos": anos}

        return {"tipo": "turnover_falta_ano"}

    if "qtd" in t or "quantos" in t or "colaborador" in t or "headcount" in t:
        return {"tipo": "headcount", "area": area, "status": status or "Ativo"}

    if "tempo de casa" in t or "tempo casa" in t:
        return {"tipo": "tempo_casa", "area": area, "status": status or "Ativo"}

    if "admiss" in t:
        return {"tipo": "admissoes", "area": area, "anos": anos}

    if "deslig" in t or "demiss" in t:
        return {"tipo": "desligamentos", "area": area, "anos": anos}

    return {"tipo": "descritivo"}


def responder(pergunta: str, df):

    intent = interpretar_intencao(pergunta)
    tipo = intent["tipo"]

    prefixo = "🧠 **Vamos lá! Aqui vai uma resposta bem clara e direta:**\n\n"

    # ---------------- HEADCOUNT ----------------
    if tipo == "headcount":
        area = intent["area"]
        status = intent["status"]

        df_local = filtrar_area(df, area)
        if status == "Ativo":
            df_local = df_local[df_local["Situacao_res"] == "Ativo"]
        elif status == "Desligado":
            df_local = df_local[df_local["Situacao_res"] != "Ativo"]

        qtd = df_local.shape[0]

        area_txt = "na empresa como um todo" if not area or area == "Geral" else f"na área **{area}**"

        return prefixo + (
            f"Hoje temos **{qtd} colaboradores {status.lower()}s** {area_txt}.\n\n"
            "Se quiser, posso te mostrar isso por ano, área, centro de custo ou histórico completo. 👇"
        )

    # ---------------- TEMPO DE CASA ----------------
    if tipo == "tempo_casa":
        area = intent["area"]
        status = intent["status"]

        df_local = filtrar_area(df, area)
        if status == "Ativo":
            df_local = df_local[df_local["Situacao_res"] == "Ativo"]
        elif status == "Desligado":
            df_local = df_local[df_local["Situacao_res"] != "Ativo"]

        hoje = pd.Timestamp(datetime.today())
        df_local["Data Ref"] = df_local["Data Afastamento"].fillna(hoje)
        df_local["Tempo_de_Casa"] = (
            (df_local["Data Ref"] - df_local["Admissão"]).dt.days / 365
        )
        media = df_local["Tempo_de_Casa"].mean()


        area_txt = "na empresa" if not area or area == "Geral" else f"na área **{area}**"

        return prefixo + (
            f"O **tempo de casa médio** {area_txt}, considerando colaboradores **{status.lower()}s**, "
            f"é de **{media:.2f} anos**.\n\n"
            "Se quiser, posso separar por faixa de tempo ou por cargo 😉"
        )

    # ---------------- ADMISSÕES ----------------
    if tipo == "admissoes":
        anos = intent.get("anos", [])
        if not anos:
            return prefixo + "Me diz pelo menos um ano para eu verificar as admissões 😊"

        area = intent.get("area")
        df_local = filtrar_area(df, area)
        partes = []

        for ano in anos:
            qtd = df_local[df_local["Ano_Admissao"] == ano].shape[0]
            partes.append(f"👉 **{ano}: {qtd} admissões**")

        area_txt = "" if not area or area == "Geral" else f" na área **{area}**"
        return prefixo + f"Aqui está o que encontrei{area_txt}:\n\n" + "\n".join(partes)

    # ---------------- DESLIGAMENTOS ----------------
    if tipo == "desligamentos":
        anos = intent.get("anos", [])
        if not anos:
            return prefixo + "Me diga o ano para eu te mostrar os desligamentos 😉"

        area = intent.get("area")
        df_local = filtrar_area(df, area)
        partes = []

        for ano in anos:
            qtd = df_local[df_local["Ano_Afastamento"] == ano].shape[0]
            partes.append(f"👉 **{ano}: {qtd} desligamentos**")

        area_txt = "" if not area or area == "Geral" else f" na área **{area}**"
        return prefixo + f"Beleza! Aqui vai{area_txt}:\n\n" + "\n".join(partes)

    # ---------------- TURNOVER MENSAL ----------------
    if tipo == "turnover_mensal":
        ano = intent["ano"]
        mes = intent["mes"]
        area = intent["area"]

        df_local = filtrar_area(df, area)

        adm = df_local[(df_local["Ano_Admissao"] == ano) & (df_local["Mes_Admissao"] == mes)].shape[0]
        dem = df_local[(df_local["Ano_Afastamento"] == ano) & (df_local["Mes_Afastamento"] == mes)].shape[0]
        ativos = df_local[
            (df_local["Admissão"] <= pd.Timestamp(ano, mes, monthrange(ano, mes)[1]))
            & (df_local["Data Afastamento"].isna() | (df_local["Data Afastamento"] > pd.Timestamp(ano, mes, monthrange(ano, mes)[1])))
        ].shape[0]

        turno = ((adm + dem) / (2 * ativos)) * 100 if ativos > 0 else 0

        area_txt = "na empresa" if not area or area == "Geral" else f"na área **{area}**"

        return prefixo + (
            f"O turnover de **{mes:02d}/{ano} {area_txt}** foi de **{turno:.2f}%**.\n\n"
            f"- Admissões: **{adm}**\n"
            f"- Desligamentos: **{dem}**\n"
            f"- Ativos no fim do mês: **{ativos}**\n\n"
            "Se quiser, posso comparar com outro mês ou área 😉"
        )

    # ---------------- TURNOVER ANUAL ----------------
    if tipo == "turnover_anual":
        anos = intent["anos"]
        area = intent["area"]

        df_res = [calcular_turnover_anual(df, ano, area) for ano in anos]
        linhas = []

        for r in df_res:
            linhas.append(
                f"📆 **{r['Ano']}** → Turnover Alternativo: **{r['Turnover Alternativo (%)']:.2f}%**, "
                f"Admissões: {r['Admissões']}, Desligamentos: {r['Desligamentos']}"
            )

        area_txt = "na empresa como um todo" if not area or area == "Geral" else f"na área **{area}**"

        return prefixo + (
            f"Aqui está o turnover anual {area_txt}:\n\n" +
            "\n".join(linhas) +
            "\n\nSe quiser comparar com outro ano, posso fazer na hora 😉"
        )

    # ---------------- TURNOVER FALTANDO ANO ----------------
    if tipo == "turnover_falta_ano":
        return prefixo + (
            "Para calcular turnover eu preciso saber **o ano**. "
            "Exemplo: `qual o turnover de 2024 no varejo?` 😉"
        )

    # ---------------- MAIOR TURNOVER HISTÓRICO ----------------
    if tipo == "turnover_max":
        resultados = [calcular_turnover_anual(df, ano) for ano in ANOS_DISPONIVEIS]
        df_res = pd.DataFrame(resultados)

        linha = df_res.sort_values("Turnover Alternativo (%)", ascending=False).iloc[0]

        return prefixo + (
            f"O **maior turnover da história** foi em **{int(linha['Ano'])}**, "
            f"com **{linha['Turnover Alternativo (%)']:.2f}%**.\n\n"
            "Se quiser, posso te mostrar quem mais contribuiu para esse número 😉"
        )

    # ---------------- DESCRITIVO ----------------
    return (
        prefixo +
        "Para te ajudar melhor, tente perguntar algo como:\n\n"
        "- *Quantos colaboradores ativos temos na Indústria?*\n"
        "- *Qual o turnover de 11/2025 na Matriz?*\n"
        "- *Compare o turnover do Varejo entre 2023 e 2024*.\n\n"
        "Tô por aqui! É só mandar a próxima pergunta 😄"
    )


st.markdown("## 🧠 Assistente Inteligente — La Moda BI")

# Botão de voz para ditado
st.markdown("""
<button class="voice-btn" onclick="startRecognition()">🎤 Falar</button>

<script>
function startRecognition() {
    var recognition = new(window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.lang = "pt-BR";
    recognition.onresult = function(event) {
        var text = event.results[0][0].transcript;
        document.querySelector('.input-ai input').value = text;
    };
    recognition.start();
}
</script>
""", unsafe_allow_html=True)


pergunta = st.text_input("Digite sua pergunta:", placeholder="Ex: qual o turnover 11/2025 no varejo?")
botao = st.button("Perguntar")

if botao and pergunta.strip():
    resposta = responder(pergunta, df_base)
    st.markdown("### ✅ Resposta")
    st.success(resposta)
