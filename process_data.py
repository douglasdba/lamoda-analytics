import pandas as pd
import numpy as np
from datetime import date, datetime
from pathlib import Path
import re
import sys

# =========================================================
# CONFIGURAÇÕES DE CAMINHOS (PADRÃO PROFISSIONAL)
# =========================================================
BASE_DIR = Path(__file__).resolve().parent
DATA_ROOT = BASE_DIR / "lamoda_dados"

RAW_DIR = DATA_ROOT / "raw"
DATA_DIR = DATA_ROOT / "data"
MAP_DIR = BASE_DIR / "mapeamentos"

# Garante estrutura mínima
for d in [DATA_ROOT, RAW_DIR, DATA_DIR]:
    d.mkdir(exist_ok=True)

# =========================================================
# CONFIGURAÇÃO DOS ARQUIVOS DA SEMANA
# =========================================================
CLT_FILE = RAW_DIR / "02.12.25-CLT.xls"
PJ_FILE  = RAW_DIR / "02.12.25-PJ.xls"

def validar_arquivo(path: Path):
    if not path.exists():
        print(f"❌ Arquivo não encontrado: {path}")
        sys.exit(1)

validar_arquivo(CLT_FILE)
validar_arquivo(PJ_FILE)

print("📂 Lendo arquivos brutos...")
df  = pd.read_excel(CLT_FILE, engine="xlrd")
df2 = pd.read_excel(PJ_FILE, engine="xlrd")

# =========================================================
# 1) LIMPEZA INICIAL
# =========================================================
print("🧹 Limpeza inicial...")

def limpeza_inicial(d):
    d = d.dropna(how="all").reset_index(drop=True)
    return d.drop(columns=["Posição do Local", "Cadastro"], errors="ignore")

df  = limpeza_inicial(df)
df2 = limpeza_inicial(df2)

# =========================================================
# 2) LIMPEZA DE CARGOS
# =========================================================
print("🧹 Removendo cargos indesejados...")

padrao_clt = r"JOVEM APRENDIZ|ESTAGIARI[OA]|APRENDIZ"
padrao_pj  = r"PRESTADOR DE SERVIÇO|SERVENTE DE ZELADORIA|ESPEC\.? DE SERV\.? DE LAVANDERIA"

cargos_remover_df2 = [
    "MEDICO DE TRABALHO","FAXINEIRO","MODELO DE PROVA","NUTRICIONISTA","SECRETARIA",
    "MOTORISTA","PROFESSOR DE INGLES","ESTOQUISTA","IMPRESSOR DE ADESIVOS",
    "ZELADORA","ZELADOR","VIGILANTE","COACHING","AN ADM PESSOAL I"
]

padrao_df2_extra = r"|".join(map(re.escape, cargos_remover_df2))

df  = df[~df["Título Reduzido (Cargo)"].str.contains(padrao_clt, case=False, na=False)]
df2 = df2[~df2["Título Reduzido (Cargo)"].str.contains(padrao_df2_extra, case=False, na=False)]
df2 = df2[~df2["Título Reduzido (Cargo)"].str.contains(padrao_pj, case=False, na=False)]

print(f"✅ Registros restantes: CLT={len(df)} | PJ={len(df2)}")

# =========================================================
# 3) TRATAMENTO DE DATAS
# =========================================================
print("📅 Tratando datas...")

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

df  = tratar_datas(df)
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

# =========================================================
# 4) MAPEAMENTOS (SEGURO)
# =========================================================
print("📄 Lendo mapeamentos...")

def load_dict_from_txt(filename):
    path = MAP_DIR / filename
    if not path.exists():
        print(f"❌ Mapeamento não encontrado: {filename}")
        sys.exit(1)

    data = {}
    with open(path, "r", encoding="utf-8") as f:
        for linha in f:
            if ":" in linha:
                k, v = linha.split(":", 1)
                data[k.strip().strip('"')] = v.strip().strip('",')
    return data

def load_list_from_txt(filename):
    path = MAP_DIR / filename
    if not path.exists():
        print(f"❌ Lista não encontrada: {filename}")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        return [l.strip().strip('",') for l in f if l.strip()]

causas_map      = load_dict_from_txt("causas_map.txt")
situacao_map    = load_dict_from_txt("situacao_map.txt")
cc_map          = load_dict_from_txt("cc_map.txt")
temporarios_lst = load_list_from_txt("temporarios_map.txt")

df["Causa Escrita"]  = df["Causa"].map(causas_map).fillna("Desconhecida")
df2["Causa Escrita"] = df2["Causa"].map(causas_map).fillna("Desconhecida")

df["Situacao Escrita"]  = df["Situação"].astype(int).map(situacao_map).fillna("Desconhecida")
df2["Situacao Escrita"] = df2["Situação"].astype(int).map(situacao_map).fillna("Desconhecida")

situacoes_ativas = ["Trabalhando", "Férias", "Licença Maternidade", "Atestado Médico"]

df["Situacao_res"]  = np.where(df["Situacao Escrita"].isin(situacoes_ativas), "Ativo", "Desligado/Afastado")
df2["Situacao_res"] = np.where(df2["Situacao Escrita"].isin(situacoes_ativas), "Ativo", "Desligado/Afastado")

# =========================================================
# 5) REMOÇÕES E CLASSIFICAÇÕES
# =========================================================
print("🏬 Removendo lojas fechadas e temporários...")

lojas_keywords = ["OUTLET TIJUCAS", "CONTINENTE PARK SHOPPING"]
pattern = r"|".join(map(re.escape, lojas_keywords))

df = df[~df["Descrição (C.Custo)"].astype(str).str.upper().str.contains(pattern, na=False)]
df = df[~df["Nome"].isin(temporarios_lst)]

def classificar_area(cc):
    cc = str(cc).upper()
    if "LOJAS" in cc:
        return "Varejo"
    if "SUPPLY" in cc:
        return "Indústria"
    return "Matriz"

for d in (df, df2):
    d["Area"] = d["C.Custo"].astype(str).map(cc_map).fillna("0")
    d["Area"] = d["Area"].apply(classificar_area)
    d.drop(d[(d["Area"] == "0") & (d["Situacao_res"] != "Ativo")].index, inplace=True)

# =========================================================
# 6) UNIFICAR BASES
# =========================================================
print("📦 Unificando bases...")

df["TIPO"]  = "CLT"
df2["TIPO"] = "PJ"

df_final = pd.concat([df, df2], ignore_index=True)
print(f"📊 Total final: {len(df_final)} registros")

# =========================================================
# 7) SALVAR BASE FINAL
# =========================================================
OUTPUT_FILE = DATA_DIR / "base_tratada.csv"
df_final.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")


# ================================
# GERAR TEMPO DE CASA
# ================================
hoje = pd.to_datetime("today")

df_final["Data Ref"] = df_final["Data Afastamento"].fillna(hoje)
df_final["Dias_de_Casa"] = (df_final["Data Ref"] - df_final["Admissão"]).dt.days.clip(lower=0)
df_final["Meses_de_Casa"] = (df_final["Dias_de_Casa"] / 30.44).round(1)
df_final["Anos_de_Casa"] = (df_final["Dias_de_Casa"] / 365).round(2)

tempo_cols = [
    "Nome", "Admissão", "Data Afastamento", "Situacao_res", "Area",
    "Descrição (C.Custo)", "Título Reduzido (Cargo)",
    "Dias_de_Casa", "Meses_de_Casa", "Anos_de_Casa"
]

df_final[tempo_cols].to_csv(DATA_DIR / "tempo_de_casa.csv", index=False, encoding="utf-8")


print("✅ Base tratada gerada com sucesso!")
print(f"📄 Caminho: {OUTPUT_FILE}")
