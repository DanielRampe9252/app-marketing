import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuração da Página
st.set_page_config(page_title="Controle CAP - Marketing", layout="wide", initial_sidebar_state="expanded")

# --- Barra Lateral para Navegação e Orçamento ---
st.sidebar.title("Navegação")
pagina = st.sidebar.radio("Selecione a Página", [
    "Dashboard Principal", 
    "Análise de Custos Detalhada", 
    "Gestão de Pagamentos (Baixas)" # Nova página adicionada
])
st.sidebar.divider()
orcamento_mensal = st.sidebar.number_input("Orçamento Mensal Estipulado (R$)", value=450000.0, step=1000.0)

# 2. Carregamento e Tratamento dos Dados (Inicial)
@st.cache_data
def load_data(file_path):
    try:
        df = pd.read_csv(file_path, encoding='utf-16-le', sep=';', skiprows=1, on_bad_lines='skip', engine='python')
        
        # Tratamento financeiro
        for col in ['Valor documento', 'Valor pago']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace('R$', '', regex=False).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).astype(float)
        
        # Garantir que a coluna de Situação não fique vazia
        if 'Situação pagamento documento' in df.columns:
            df['Situação pagamento documento'] = df['Situação pagamento documento'].fillna('Em Aberto')
            
        return df
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo: {e}")
        return pd.DataFrame()

# 3. Memória do Aplicativo (Session State)
# Isso permite que o app lembre das suas edições de status enquanto ele estiver aberto
if 'df_dados' not in st.session_state:
    st.session_state['df_dados'] = load_data('RelatorioCAP.csv')

df = st.session_state['df_dados']

if not df.empty:
    total_doc = df['Valor documento'].sum()
    total_pago = df['Valor pago'].sum()
    saldo_pendente = total_doc - total_pago
    
    # --- PÁGINA 1: DASHBOARD PRINCIPAL ---
    if pagina == "Dashboard Principal":
        st.title("📊 Dashboard Principal - Setor de Marketing")
        
        # Alerta de Orçamento
        if total_doc > orcamento_mensal:
            st.error(f"⚠️ ALERTA: O orçamento estipulado de R$ {orcamento_mensal:,.2f} foi ultrapassado! Total lançado: R$ {total_doc:,.2f}")
        else:
            st.success(f"✅ Orçamento sob controle. Disponível: R$ {(orcamento_mensal - total_doc):,.2f}")
            
        st.header("Resumo Financeiro (Mês Atual)")
        
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

    # --- PÁGINA 2: ANÁLISE DE CUSTOS DETALHADA ---
    elif pagina == "Análise de Custos Detalhada":
        st.title("🔎 Análise de Custos Detalhada")
        df_custos = df.groupby('PlanoConta')['Valor documento'].sum().reset_index()
        df_custos = df_custos.sort_values(by='Valor documento', ascending=False)
        df_custos['% do Orçamento'] = (df_custos['Valor documento'] / orcamento_mensal) * 100
        df_custos['% do Total Gasto'] = (df_custos['Valor documento'] / total_doc) * 100
        
        col_grafico, col_tabela = st.columns([1, 1.2])
        with col_grafico:
            fig_pie = px.pie(df_custos, values='Valor documento', names='PlanoConta', title='Divisão dos Gastos (Proporção)')
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_tabela:
            st.subheader("Tabela de Custos")
            df_display = df_custos.copy()
            df_display['Valor documento'] = df_display['Valor documento'].apply(lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
            df_display['% do Orçamento'] = df_display['% do Orçamento'].apply(lambda x: f"{x:.2f}%")
            df_display['% do Total Gasto'] = df_display['% do Total Gasto'].apply(lambda x: f"{x:.2f}%")
            st.dataframe(df_display, use_container_width=True, hide_index=True)

    # --- PÁGINA 3: GESTÃO DE PAGAMENTOS (BAIXAS) ---
    elif pagina == "Gestão de Pagamentos (Baixas)":
        st.title("💸 Gestão de Pagamentos (Baixa de Títulos)")
        st.markdown("Altere a situação na coluna **Situação pagamento documento** (dê dois cliques na célula). Quando marcar como 'Pago', o sistema calculará o valor automaticamente.")
        
        # Colunas que serão exibidas na tela de edição
        colunas_exibicao = ['Código documento', 'Fornecedor', 'PlanoConta', 'Data vencimento', 'Valor documento', 'Situação pagamento documento']
        colunas_disponiveis = [c for c in colunas_exibicao if c in df.columns]
        
        with st.form("form_edicao"):
            # Editor de Dados Interativo (Estilo Excel)
            df_editado = st.data_editor(
                df[colunas_disponiveis],
                column_config={
                    "Situação pagamento documento": st.column_config.SelectboxColumn(
                        "Situação pagamento documento",
                        options=["Em Aberto", "Pago", "Cancelado", "Atrasado"],
                        required=True
                    ),
                    "Valor documento": st.column_config.NumberColumn("Valor (R$)", format="%.2f")
                },
                disabled=["Código documento", "Fornecedor", "PlanoConta", "Data vencimento", "Valor documento"],
                use_container_width=True,
                hide_index=True,
                height=400
            )
            
            salvar = st.form_submit_button("💾 Salvar Alterações e Recalcular")
            
            if salvar:
                # Atualiza os status no dataframe principal
                df['Situação pagamento documento'] = df_editado['Situação pagamento documento']
                
                # Regra de Negócio: Se estiver "Pago", o "Valor pago" recebe o valor total do documento. Senão, fica zero.
                df.loc[df['Situação pagamento documento'] == 'Pago', 'Valor pago'] = df['Valor documento']
                df.loc[df['Situação pagamento documento'] != 'Pago', 'Valor pago'] = 0.0
                
                # Salva na memória do aplicativo
                st.session_state['df_dados'] = df
                st.success("✅ Atualização concluída! Os totais do Dashboard Principal foram recalculados.")
                st.rerun() # Recarrega a tela para atualizar os dados visuais

        st.divider()
        st.subheader("Exportar Dados")
        st.markdown("Baixe a planilha com os status atualizados para salvar em seu computador.")
        
        # Converter o dataframe de volta para CSV (formato original UTF-16 com separador ponto e vírgula)
        csv_export = df.to_csv(sep=';', index=False, encoding='utf-16-le').encode('utf-16-le')
        st.download_button(
            label="📥 Baixar Planilha Atualizada",
            data=csv_export,
            file_name='RelatorioCAP_Atualizado.csv',
            mime='text/csv'
        )

else:
    st.warning("Não foi possível carregar os dados. Verifique o arquivo RelatorioCAP.csv.")
