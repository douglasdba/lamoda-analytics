# import streamlit as st
# import pandas as pd
# import plotly.express as px
# from login import require_login

# require_login()

# st.title("📆 Absenteísmo")

# path = "data/absenteismo.csv"

# try:
#     df = pd.read_csv(path)

#     col1, col2 = st.columns(2)
#     col1.metric("Total de Faltas", df["Faltas"].sum())
#     col2.metric("Absenteísmo Médio (%)", round(df["Absenteismo"].mean(), 2))

#     fig = px.line(
#         df,
#         x="Mes",
#         y="Absenteismo",
#         markers=True,
#         title="Absenteísmo por Mês"
#     )
#     st.plotly_chart(fig, use_container_width=True)

# except:
#     st.warning("⚠️ O arquivo absenteismo.csv não está na pasta /data.")
