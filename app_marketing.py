import streamlit as st
import pandas as pd
import plotly.express as px
import datetime

# 1. Configuração da Página
st.set_page_config(page_title="Controle CAP - Marketing", layout="wide", initial_sidebar_state="expanded")

# --- Barra Lateral para Navegação e Orçamento ---
st.sidebar.title("Navegação")
pagina = st.sidebar.radio("Selecione a Página", [
    "Dashboard Principal", 
    "Análise de Custos Detalhada", 
    "Gestão de Pagamentos (Baixas)",
    "Relatório Analítico (Mensal/Anual)", 
    "Adicionar / Importar Dados" 
])
st.sidebar.divider()
orcamento_mensal = st.sidebar.number_input("Orçamento Mensal Estipulado (R$)", value=450000.0, step=1000.0)

# Status Reais Extraídos da sua Planilha
STATUS_ORIGINAIS = ["A PAGAR", "BAIXA AUTOMÁTICA", "BAIXA MANUAL"]

# 2. Função de Carregamento e Tratamento
@st.cache_data
def carregar_e_tratar_csv(file):
    try:
        df = pd.read_csv(file, encoding='utf-16-le', sep=';', skiprows=1, on_bad_lines='skip', engine='python')
            
        for col in ['Valor documento', 'Valor pago']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace('R$', '', regex=False)\
                                             .str.replace('.', '', regex=False)\
                                             .str.replace(',', '.', regex=False)\
                                             .astype(float)
        
        if 'Situação pagamento documento' in df.columns:
            # Se vier vazio, assume que é "A PAGAR"
            df['Situação pagamento documento'] = df['Situação pagamento documento'].fillna('A PAGAR')
            
        if 'Código documento' in df.columns:
            df['Código documento'] = df['Código documento'].astype(str)
            
        if 'Data vencimento' in df.columns:
            data_dt = pd.to_datetime(df['Data vencimento'], format='%d/%m/%Y', errors='coerce')
            df['Ano'] = data_dt.dt.year.fillna(datetime.datetime.now().year).astype(int)
            df['Mês'] = data_dt.dt.month.fillna(datetime.datetime.now().month).astype(int)
            
        return df
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
        return pd.DataFrame()

# 3. Inicialização do Banco de Dados em Memória (Session State)
if 'df_dados' not in st.session_state:
    st.session_state['df_dados'] = carregar_e_tratar_csv('RelatorioCAP.csv')

df = st.session_state['df_dados']

if not df.empty:
    
    # Trava de Segurança Geral (Garante que Ano e Mês existam caso venham de cache antigo)
    if 'Ano' not in df.columns or 'Mês' not in df.columns:
        if 'Data vencimento' in df.columns:
            data_dt = pd.to_datetime(df['Data vencimento'], format='%d/%m/%Y', errors='coerce')
            df['Ano'] = data_dt.dt.year.fillna(datetime.datetime.now().year).astype(int)
            df['Mês'] = data_dt.dt.month.fillna(datetime.datetime.now().month).astype(int)
            st.session_state['df_dados'] = df

    total_doc = df['Valor documento'].sum()
    total_pago = df['Valor pago'].sum()
    saldo_pendente = total_doc - total_pago
    
    def formatar_moeda(valor):
        return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

    # ==========================================
    # PÁGINA 1: DASHBOARD PRINCIPAL
    # ==========================================
    if pagina == "Dashboard Principal":
        st.title("📊 Dashboard Principal - Setor de Marketing")
        
        if total_doc > orcamento_mensal:
            st.error(f"⚠️ ALERTA: O orçamento estipulado de {formatar_moeda(orcamento_mensal)} foi ultrapassado! Total lançado: {formatar_moeda(total_doc)}")
        else:
            st.success(f"✅ Orçamento sob controle. Disponível: {formatar_moeda(orcamento_mensal - total_doc)}")
            
        st.header("Resumo Financeiro (Geral)")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Lançado", formatar_moeda(total_doc))
        col2.metric("Total Pago", formatar_moeda(total_pago))
        col3.metric("Saldo Pendente", formatar_moeda(saldo_pendente))

        st.subheader("Distribuição de Gastos por Plano de Contas")
        df_agrupado = df.groupby('PlanoConta')['Valor documento'].sum().reset_index()
        df_agrupado = df_agrupado.sort_values(by='Valor documento', ascending=False)
        fig = px.bar(df_agrupado, x='PlanoConta', y='Valor documento', text_auto='.2s', color='PlanoConta')
        fig.update_layout(showlegend=False, yaxis_title="Valor (R$)")
        st.plotly_chart(fig, use_container_width=True)

    # ==========================================
    # PÁGINA 2: ANÁLISE DE CUSTOS DETALHADA
    # ==========================================
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
            df_display['Valor documento'] = df_display['Valor documento'].apply(formatar_moeda)
            df_display['% do Orçamento'] = df_display['% do Orçamento'].apply(lambda x: f"{x:.2f}%")
            df_display['% do Total Gasto'] = df_display['% do Total Gasto'].apply(lambda x: f"{x:.2f}%")
            st.dataframe(df_display, use_container_width=True, hide_index=True)

    # ==========================================
    # PÁGINA 3: GESTÃO DE PAGAMENTOS
    # ==========================================
    elif pagina == "Gestão de Pagamentos (Baixas)":
        st.title("💸 Gestão de Pagamentos")
        st.markdown("Altere a **Situação** (dê dois cliques na célula).")
        
        colunas_exibicao = ['Código documento', 'Fornecedor', 'PlanoConta', 'Data vencimento', 'Valor Visual', 'Situação pagamento documento']
        
        df_exibicao = df.copy()
        if 'Valor documento' in df_exibicao.columns:
            df_exibicao['Valor Visual'] = df_exibicao['Valor documento'].apply(formatar_moeda)
        
        colunas_disponiveis = [c for c in colunas_exibicao if c in df_exibicao.columns]
        
        with st.form("form_edicao"):
            df_editado = st.data_editor(
                df_exibicao[colunas_disponiveis],
                column_config={
                    "Situação pagamento documento": st.column_config.SelectboxColumn("Situação", options=STATUS_ORIGINAIS, required=True),
                    "Valor Visual": st.column_config.TextColumn("Valor do Título") 
                },
                disabled=["Código documento", "Fornecedor", "PlanoConta", "Data vencimento", "Valor Visual"],
                use_container_width=True, hide_index=True, height=400
            )
            salvar = st.form_submit_button("💾 Salvar Alterações e Recalcular")
            
            if salvar:
                df['Situação pagamento documento'] = df_editado['Situação pagamento documento']
                
                # Regra: Se for BAIXA AUTOMÁTICA ou BAIXA MANUAL, conta como pago.
                pagos_mask = df['Situação pagamento documento'].isin(["BAIXA AUTOMÁTICA", "BAIXA MANUAL"])
                df.loc[pagos_mask, 'Valor pago'] = df['Valor documento']
                df.loc[~pagos_mask, 'Valor pago'] = 0.0
                
                st.session_state['df_dados'] = df
                st.success("✅ Atualização concluída!")
                st.rerun()

        st.divider()
        st.subheader("Exportar Dados Consolidados")
        csv_export = df.drop(columns=['Ano', 'Mês', 'Valor Visual'], errors='ignore').to_csv(sep=';', index=False, encoding='utf-16-le').encode('utf-16-le')
        st.download_button("📥 Baixar Planilha Atualizada", data=csv_export, file_name='RelatorioCAP_Atualizado.csv', mime='text/csv')

    # ==========================================
    # PÁGINA 4: RELATÓRIO ANALÍTICO
    # ==========================================
    elif pagina == "Relatório Analítico (Mensal/Anual)":
        st.title("📅 Relatório Analítico de Lançamentos")
        st.markdown("Filtre os dados por período para avaliar as contas e visualizar as informações completas.")
        
        meses_nomes = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}
        
        col_filtro1, col_filtro2, col_filtro3 = st.columns(3)
        
        anos_disponiveis = sorted(df['Ano'].dropna().unique().tolist())
        ano_selecionado = col_filtro1.selectbox("Selecione o Ano", ["Todos"] + anos_disponiveis)
        
        meses_disponiveis = sorted(df['Mês'].dropna().unique().tolist())
        meses_opcoes = ["Todos"] + [meses_nomes.get(m, str(m)) for m in meses_disponiveis]
        mes_selecionado = col_filtro2.selectbox("Selecione o Mês", meses_opcoes)
        
        # Filtro com os status exatos da planilha
        filtros_situacao = ["Todos os Lançamentos"] + STATUS_ORIGINAIS
        situacao_selecionada = col_filtro3.selectbox("Filtro de Situação", filtros_situacao)
        
        df_filtrado = df.copy()
        
        if ano_selecionado != "Todos":
            df_filtrado = df_filtrado[df_filtrado['Ano'] == ano_selecionado]
            
        if mes_selecionado != "Todos":
            mes_numero = [k for k, v in meses_nomes.items() if v == mes_selecionado][0]
            df_filtrado = df_filtrado[df_filtrado['Mês'] == mes_numero]
            
        if situacao_selecionada != "Todos os Lançamentos":
            df_filtrado = df_filtrado[df_filtrado['Situação pagamento documento'] == situacao_selecionada]
            
        st.divider()
        st.subheader(f"Resultados do Período ({len(df_filtrado)} lançamentos encontrados)")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Valor Total Lançado", formatar_moeda(df_filtrado['Valor documento'].sum()))
        c2.metric("Valor Efetivamente Pago", formatar_moeda(df_filtrado['Valor pago'].sum()))
        c3.metric("Saldo Pendente", formatar_moeda(df_filtrado['Valor documento'].sum() - df_filtrado['Valor pago'].sum()))
        
        st.markdown("### 📋 Dados Analíticos Detalhados")
        df_exibicao_analitico = df_filtrado.copy()
        df_exibicao_analitico['Valor documento'] = df_exibicao_analitico['Valor documento'].apply(formatar_moeda)
        df_exibicao_analitico['Valor pago'] = df_exibicao_analitico['Valor pago'].apply(formatar_moeda)
        
        colunas_analiticas = ['Código documento', 'Fornecedor', 'PlanoConta', 'Data vencimento', 'Valor documento', 'Valor pago', 'Situação pagamento documento']
        colunas_exibir = [c for c in colunas_analiticas if c in df_exibicao_analitico.columns]
        
        st.dataframe(df_exibicao_analitico[colunas_exibir], use_container_width=True, hide_index=True)

    # ==========================================
    # PÁGINA 5: ADICIONAR / IMPORTAR DADOS
    # ==========================================
    elif pagina == "Adicionar / Importar Dados":
        st.title("➕ Alimentar Sistema")
        
        st.subheader("1. Importação Automática (Planilha CSV)")
        arquivo_upload = st.file_uploader("Arraste ou escolha o arquivo CSV", type=['csv'])
        
        if arquivo_upload is not None:
            df_novo = carregar_e_tratar_csv(arquivo_upload)
            if not df_novo.empty:
                codigos_existentes = df['Código documento'].tolist()
                df_filtrado = df_novo[~df_novo['Código documento'].isin(codigos_existentes)]
                
                qtd_novos = len(df_filtrado)
                if qtd_novos > 0:
                    st.success(f"✅ Foram encontrados {qtd_novos} novos lançamentos! Clique abaixo para integrar.")
                    if st.button("Integrar Novos Lançamentos ao Sistema"):
                        df = pd.concat([df, df_filtrado], ignore_index=True)
                        st.session_state['df_dados'] = df
                        st.success("Banco de dados atualizado! Vá para o Dashboard para ver os números.")
                        st.rerun()
                else:
                    st.info("ℹ️ Nenhum lançamento novo encontrado. Todos os registros já estão no sistema.")

        st.divider()
        st.subheader("2. Inclusão Manual (Lançamento Avulso)")
        with st.form("form_manual"):
            col_a, col_b = st.columns(2)
            codigo = col_a.text_input("Código do Documento (Único)", value=f"MANUAL-{int(datetime.datetime.now().timestamp())}")
            fornecedor = col_b.text_input("Fornecedor / Favorecido")
            
            col_c, col_d = st.columns(2)
            lista_contas = df['PlanoConta'].dropna().unique().tolist() if 'PlanoConta' in df.columns else []
            plano_conta = col_c.selectbox("Plano de Contas", lista_contas)
            valor_novo = col_d.number_input("Valor da Despesa (R$)", min_value=0.0, format="%.2f")
            
            col_e, col_f = st.columns(2)
            data_venc = col_e.date_input("Data de Vencimento")
            situacao = col_f.selectbox("Situação", STATUS_ORIGINAIS)
            
            salvar_manual = st.form_submit_button("Registrar Lançamento Avulso")
            
            if salvar_manual:
                if fornecedor == "" or valor_novo <= 0:
                    st.warning("Preencha o fornecedor e um valor válido.")
                elif codigo in df['Código documento'].values:
                    st.error("Esse Código de Documento já existe no sistema!")
                else:
                    novo_registro = pd.DataFrame([{
                        'Código documento': codigo,
                        'Fornecedor': fornecedor,
                        'PlanoConta': plano_conta,
                        'Valor documento': valor_novo,
                        'Valor pago': valor_novo if situacao in ["BAIXA AUTOMÁTICA", "BAIXA MANUAL"] else 0.0,
                        'Data vencimento': data_venc.strftime('%d/%m/%Y'),
                        'Situação pagamento documento': situacao,
                        'Ano': data_venc.year,
                        'Mês': data_venc.month
                    }])
                    df = pd.concat([df, novo_registro], ignore_index=True)
                    st.session_state['df_dados'] = df
                    st.success(f"✅ Lançamento de {formatar_moeda(valor_novo)} inserido!")
                    
else:
    st.warning("Não foi possível carregar os dados iniciais. Verifique o arquivo RelatorioCAP.csv no repositório.")
