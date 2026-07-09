import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuração da Página
st.set_page_config(page_title="Controle CAP - Marketing", layout="wide")
st.title("📊 Controle de Despesas - Setor de Marketing")

# 2. Carregamento e Tratamento dos Dados
@st.cache_data
def load_data(file_path):
    try:
        # A leitura considera o formato exportado (UTF-16 e separador ponto e vírgula)
        df = pd.read_csv(file_path, encoding='utf-16-le', sep=';', skiprows=1, on_bad_lines='skip', engine='python')
        
        # Tratamento de valores financeiros para cálculos precisos
        for col in ['Valor documento', 'Valor pago']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace('R$', '', regex=False)\
                                             .str.replace('.', '', regex=False)\
                                             .str.replace(',', '.', regex=False)\
                                             .astype(float)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo: {e}")
        return pd.DataFrame()

df = load_data('RelatorioCAP.csv')

if not df.empty:
    # 3. Painel de Indicadores (KPIs)
    st.header("1. Resumo Financeiro (Mês Atual)")
    
    total_doc = df['Valor documento'].sum()
    total_pago = df['Valor pago'].sum()
    saldo_pendente = total_doc - total_pago
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Lançado (R$)", f"{total_doc:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
    col2.metric("Total Pago (R$)", f"{total_pago:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
    col3.metric("Saldo Pendente (R$)", f"{saldo_pendente:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

    # 4. Análise Gráfica Dinâmica
    st.subheader("Distribuição de Gastos por Plano de Contas")
    df_agrupado = df.groupby('PlanoConta')['Valor documento'].sum().reset_index()
    df_agrupado = df_agrupado.sort_values(by='Valor documento', ascending=False)
    
    fig = px.bar(df_agrupado, x='PlanoConta', y='Valor documento', 
                 text_auto='.2s', color='PlanoConta',
                 labels={'Valor documento': 'Valor Total (R$)', 'PlanoConta': 'Categoria'})
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # 5. Formulário de Lançamentos Futuros
    st.header("2. Registro de Lançamentos Futuros (Provisão)")
    st.markdown("Preencha os dados abaixo para provisionar um novo gasto no fluxo de caixa.")
    
    with st.form("form_provisao"):
        col_a, col_b = st.columns(2)
        fornecedor = col_a.text_input("Fornecedor / Favorecido")
        
        # Puxa as categorias diretamente da planilha para manter o padrão
        lista_contas = df['PlanoConta'].dropna().unique().tolist()
        plano_conta = col_b.selectbox("Plano de Contas", lista_contas)
        
        col_c, col_d = st.columns(2)
        valor_previsto = col_c.number_input("Valor Previsto (R$)", min_value=0.0, format="%.2f")
        data_vencimento = col_d.date_input("Data de Vencimento")
        
        descricao = st.text_area("Descrição / Motivo da Despesa")
        
        submitted = st.form_submit_button("Registrar Provisão")
        
        if submitted:
            if fornecedor == "" or valor_previsto <= 0:
                st.warning("Por favor, preencha o fornecedor e um valor válido.")
            else:
                st.success(f"✅ Provisão para {fornecedor} no valor de R$ {valor_previsto:,.2f} registrada para {data_vencimento.strftime('%d/%m/%Y')}!")
else:
    st.warning("Não foi possível carregar os dados. Verifique o arquivo RelatorioCAP.csv.")
