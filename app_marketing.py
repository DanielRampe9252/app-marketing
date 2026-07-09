Skip to content
DanielRampe9252
app-marketing
Repository navigation
Code
Issues
Pull requests
Actions
Projects
Wiki
Security and quality
Insights
Settings
Files
Go to file
t
T
.devcontainer
RelatorioCAP.csv
app_marketing.py
requirements.txt
app-marketing
/
app_marketing.py
in
main

Edit

Preview
Indent mode

Spaces
Indent size

4
Line wrap mode

No wrap
Editing app_marketing.py file contents
  1
  2
  3
  4
  5
  6
  7
  8
  9
 10
 11
 12
 13
 14
 15
 16
 17
 18
 19
 20
 21
 22
 23
 24
 25
 26
 27
 28
 29
 30
 31
 32
 33
 34
 35
 36
import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuração da Página
st.set_page_config(page_title="Controle CAP - Marketing", layout="wide", initial_sidebar_state="expanded")

# --- Barra Lateral para Navegação e Orçamento ---
st.sidebar.title("Navegação")
pagina = st.sidebar.radio("Selecione a Página", ["Dashboard Principal", "Análise de Custos Detalhada"])
st.sidebar.divider()
# O orçamento estipulado de 450 mil já vem como padrão, mas pode ser ajustado no próprio app.
orcamento_mensal = st.sidebar.number_input("Orçamento Mensal Estipulado (R$)", value=450000.0, step=1000.0)

# 2. Carregamento e Tratamento dos Dados
@st.cache_data
def load_data(file_path):
    try:
        df = pd.read_csv(file_path, encoding='utf-16-le', sep=';', skiprows=1, on_bad_lines='skip', engine='python')
        for col in ['Valor documento', 'Valor pago']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace('R$', '', regex=False).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).astype(float)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo: {e}")
        return pd.DataFrame()

df = load_data('RelatorioCAP.csv')

if not df.empty:
    total_doc = df['Valor documento'].sum()
    
    # --- Lógica de Alerta de Orçamento ---
    if total_doc > orcamento_mensal:
        st.error(f"⚠️ ALERTA: O orçamento estipulado de R$ {orcamento_mensal:,.2f} foi ultrapassado! Total lançado: R$ {total_doc:,.2f}")
    else:
Use Control + Shift + m to toggle the tab key moving focus. Alternatively, use esc then tab to move to the next interactive element on the page.

