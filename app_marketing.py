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
        st.success(f"✅ Orçamento sob controle. Disponível: R$ {(orcamento_mensal - total_doc):,.2f}")
    
    # --- PÁGINA 1: DASHBOARD PRINCIPAL ---
    if pagina == "Dashboard Principal":
        st.title("📊 Dashboard Principal - Setor de Marketing")
        st.header("Resumo Financeiro (Mês Atual)")
        
        total_pago = df['Valor pago'].sum()
        saldo_pendente = total_doc - total_pago
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Lançado (R$)", f"{total_doc:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        col2.metric("Total Pago (R$)", f"{total_pago:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        col3.metric("Saldo Pendente (R$)", f"{saldo_pendente:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

        st.subheader("Distribuição de Gastos por Plano de Contas")
        df_agrupado = df.groupby('PlanoConta')['Valor documento'].sum().reset_index()
        df_agrupado = df_agrupado.sort_values(by='Valor documento', ascending=False)
        fig = px.bar(df_agrupado, x='PlanoConta', y='Valor documento', text_auto='.2s', color='PlanoConta', labels={'Valor documento': 'Valor Total (R$)'})
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        st.header("2. Registro de Lançamentos Futuros (Provisão)")
        with st.form("form_provisao"):
            col_a, col_b = st.columns(2)
            fornecedor = col_a.text_input("Fornecedor / Favorecido")
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
                    st.success(f"✅ Provisão para {fornecedor} no valor de R$ {valor_previsto:,.2f} registrada!")

    # --- PÁGINA 2: ANÁLISE DE CUSTOS DETALHADA ---
    elif pagina == "Análise de Custos Detalhada":
        st.title("🔎 Análise de Custos Detalhada")
        st.markdown("Detalhamento de cada conta e sua representatividade em relação ao orçamento estipulado.")
        
        df_custos = df.groupby('PlanoConta')['Valor documento'].sum().reset_index()
        df_custos = df_custos.sort_values(by='Valor documento', ascending=False)
        
        # Cálculos de Representatividade
        df_custos['% do Orçamento (450k)'] = (df_custos['Valor documento'] / orcamento_mensal) * 100
        df_custos['% do Total Gasto'] = (df_custos['Valor documento'] / total_doc) * 100
        
        col_grafico, col_tabela = st.columns([1, 1.2])
        
        with col_grafico:
            fig_pie = px.pie(df_custos, values='Valor documento', names='PlanoConta', title='Divisão dos Gastos (Proporção)')
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_tabela:
            st.subheader("Tabela de Custos (Detalhamento)")
            # Formatação para exibição amigável
            df_display = df_custos.copy()
            df_display['Valor documento'] = df_display['Valor documento'].apply(lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
            df_display['% do Orçamento (450k)'] = df_display['% do Orçamento (450k)'].apply(lambda x: f"{x:.2f}%")
            df_display['% do Total Gasto'] = df_display['% do Total Gasto'].apply(lambda x: f"{x:.2f}%")
            df_display.rename(columns={'Valor documento': 'Valor Total', 'PlanoConta': 'Categoria'}, inplace=True)
            
            st.dataframe(df_display, use_container_width=True, hide_index=True)
else:
    st.warning("Não foi possível carregar os dados. Verifique o arquivo RelatorioCAP.csv.")
