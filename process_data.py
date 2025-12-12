import pandas as pd
import numpy as np
from datetime import date, datetime
from pathlib import Path
import re

# =========================================================
# CONFIGURAÇÕES DE CAMINHOS
# =========================================================
BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "raw"
MAP_DIR = BASE_DIR / "mapeamentos"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# >>>>> ATENÇÃO: Troque os nomes dos arquivos conforme a data semanal <<<<<
CLT_FILE = RAW_DIR / "02.12.25-CLT.xls"
PJ_FILE  = RAW_DIR / "02.12.25-PJ.xls"

print("📂 Lendo arquivos brutos...")
df = pd.read_excel(CLT_FILE, engine="xlrd")
df2 = pd.read_excel(PJ_FILE, engine="xlrd")

# =========================================================
# 1) LIMPEZA INICIAL
# =========================================================
print("🧹 Removendo linhas vazias e colunas inúteis...")

df = df.dropna(how='all').reset_index(drop=True)
df2 = df2.dropna(how='all').reset_index(drop=True)

df = df.drop(columns=['Posição do Local', 'Cadastro'], errors='ignore')
df2 = df2.drop(columns=['Posição do Local', 'Cadastro'], errors='ignore')

# =========================================================
# 2) LIMPEZA DE CARGOS
# =========================================================
print("🧹 Removendo cargos indesejados...")

padrao_clt = r'JOVEM APRENDIZ|ESTAGIARI[OA]|APRENDIZ'
padrao_pj  = r'PRESTADOR DE SERVIÇO|SERVENTE DE ZELADORIA|ESPEC\.? DE SERV\.? DE LAVANDERIA'

cargos_remover_df2 = [
    "MEDICO DE TRABALHO","FAXINEIRO","MODELO DE PROVA","NUTRICIONISTA","SECRETARIA",
    "MOTORISTA","PROFESSOR DE INGLES","ESTOQUISTA","IMPRESSOR DE ADESIVOS","ZELADORA",
    "ZELADOR","VIGILANTE","COACHING","AN ADM PESSOAL I"
]
padrao_df2_extra = r"|".join(list(set(cargos_remover_df2)))

df  = df[~df['Título Reduzido (Cargo)'].str.contains(padrao_clt, case=False, na=False)]
df2 = df2[~df2['Título Reduzido (Cargo)'].str.contains(padrao_df2_extra, case=False, na=False)]
df2 = df2[~df2['Título Reduzido (Cargo)'].str.contains(padrao_pj, case=False, na=False)]

print(f"✅ Registros restantes: CLT={len(df)} | PJ={len(df2)}")

# =========================================================
# 3) TRATAR DATAS COM SEGURANÇA
# =========================================================
print("📅 Tratando colunas de datas...")

date_cols = ["Nascimento", "Admissão", "Data Afastamento"]

# Limpar valores inválidos
for d in (df, df2):
    for col in date_cols:
        d[col] = d[col].replace(["00/00/0000"," 00:00:00","--","","0"], pd.NA)

# Converter para datetime
# Garantir que nada fique como string
for d in (df, df2):
    for col in date_cols:
        d[col] = (
            d[col]
            .astype(str)
            .str.strip()
            .replace(["", " ", "00/00/0000", "0", "--", "NaT", "nan"], pd.NA)
        )
        d[col] = pd.to_datetime(d[col], errors="coerce")


# Função segura para calcular idade
def calc_idade(dt):
    try:
        if pd.isna(dt):
            return 0
        # Garante conversão se ainda for string
        if isinstance(dt, str):
            dt = pd.to_datetime(dt, errors="coerce")
            if pd.isna(dt):
                return 0
        return int((date.today() - dt.to_pydatetime()).days / 365.25)
    except:
        return 0


# Criar idade e colunas mês/ano de admissão e afastamento
for d in (df, df2):
    d['Idade'] = d['Nascimento'].apply(calc_idade)

    d['Mes_Admissao'] = d['Admissão'].dt.month.fillna(0).astype(int)
    d['Ano_Admissao'] = d['Admissão'].dt.year.fillna(0).astype(int)

    d['Mes_Afastamento'] = d['Data Afastamento'].dt.month.fillna(0).astype(int)
    d['Ano_Afastamento'] = d['Data Afastamento'].dt.year.fillna(0).astype(int)

# =========================================================
# 4) MAPEAMENTOS (TABELAS TXT)
# =========================================================
def load_dict_from_txt(filename):
    path = MAP_DIR / filename
    try:
        with open(path, "r", encoding="utf-8") as f:
            return eval("{" + f.read() + "}")
    except:
        print(f"❌ Erro ao ler {filename}")
        return {}

def load_list_from_txt(filename):
    path = MAP_DIR / filename
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [linha.strip().strip('",') for linha in f if linha.strip()]
    except:
        print(f"❌ Erro ao ler {filename}")
        return []

print("📄 Lendo mapeamentos...")

causas_map      = load_dict_from_txt("causas_map.txt")
situacao_map    = load_dict_from_txt("situacao_map.txt")
cc_map          = load_dict_from_txt("cc_map.txt")
temporarios_lst = load_list_from_txt("temporarios_map.txt")

# Aplicar mapeamentos
df['Causa Escrita']  = df['Causa'].map(causas_map).fillna('Desconhecida')
df2['Causa Escrita'] = df2['Causa'].map(causas_map).fillna('Desconhecida')

df['Situacao Escrita']  = df['Situação'].astype(int).map(situacao_map).fillna('Desconhecida')
df2['Situacao Escrita'] = df2['Situação'].astype(int).map(situacao_map).fillna('Desconhecida')

situacoes_ativas = ["Trabalhando", "Férias", "Licença Maternidade", "Atestado Médico"]

df["Situacao_res"]  = np.where(df["Situacao Escrita"].isin(situacoes_ativas),"Ativo","Desligado/Afastado")
df2["Situacao_res"] = np.where(df2["Situacao Escrita"].isin(situacoes_ativas),"Ativo","Desligado/Afastado")

# =========================================================
# 5) REMOVER LOJAS FECHADAS
# =========================================================
print("🏬 Removendo lojas fechadas...")

lojas_keywords = ["OUTLET TIJUCAS", "CONTINENTE PARK SHOPPING"]
pattern = r"(" + r"|".join(re.escape(k) for k in lojas_keywords) + r")"

mask = df["Descrição (C.Custo)"].astype(str).str.upper().str.contains(pattern, na=False)
df = df[~mask].reset_index(drop=True)

# =========================================================
# 6) TEMPO DE CASA
# =========================================================
print("⏳ Calculando tempo de casa...")

hoje = pd.Timestamp(datetime.today())

def tempo_casa(adm):
    if pd.isna(adm):
        return 0
    anos = (hoje.year - adm.year) - (
        (hoje.month < adm.month) or ((hoje.month == adm.month) and (hoje.day < adm.day))
    )
    return int(anos)

df["Tempo_de_Casa"]  = df["Admissão"].apply(tempo_casa)
df2["Tempo_de_Casa"] = df2["Admissão"].apply(tempo_casa)

# =========================================================
# 7) REMOVER TEMPORÁRIOS
# =========================================================
print("🧹 Removendo temporários...")

df = df[~df['Nome'].isin(temporarios_lst)]

# =========================================================
# 8) MAPEAR AREA (C.CUSTO)
# =========================================================
print("🏢 Mapeando C.Custo -> Área...")

df["Area"]  = df["C.Custo"].astype(str).map(cc_map).fillna("0")
df2["Area"] = df2["C.Custo"].astype(str).map(cc_map).fillna("0")

df  = df[~((df['Area']=="0")  & (df['Situacao_res']=="Desligado/Afastado"))]
df2 = df2[~((df2['Area']=="0") & (df2['Situacao_res']=="Desligado/Afastado"))]


def classificar_area(area_original):
    area_original = str(area_original).upper().strip()

    if "LOJAS" in area_original:
        return "Varejo"
    elif "SUPPLY" in area_original:
        return "Indústria"
    else:
        return "Matriz"

df["Area"] = df["Area"].apply(classificar_area)
df2["Area"] = df2["Area"].apply(classificar_area)

# Remover áreas "0" apenas se desligados/afastados (mantém regra antiga)
df = df[~((df['Area']=="0") & (df['Situacao_res']=="Desligado/Afastado"))]
df2 = df2[~((df2['Area']=="0") & (df2['Situacao_res']=="Desligado/Afastado"))]


# =========================================================
# 9) UNIFICAR CLT + PJ
# =========================================================
print("📦 Unificando bases...")

df["TIPO"]  = "CLT"
df2["TIPO"] = "PJ"

df3 = pd.concat([df, df2], ignore_index=True)

print(f"📊 Total final: {len(df3)} registros.")

# =========================================================
# 10) SALVAR BASE FINAL
# =========================================================
OUTPUT_FILE = DATA_DIR / "base_tratada.csv"
df3.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")

print("✅ Arquivo base_tratada.csv salvo com sucesso!")
print(f"📄 Caminho: {OUTPUT_FILE}")
