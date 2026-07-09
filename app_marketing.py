import streamlit as st
import pandas as pd
import plotly.express as px
import datetime

# 1. Configuração da Página
st.set_page_config(page_title="Controle CAP - Marketing", layout="wide", initial_sidebar_state="expanded")

# Dicionários e Constantes
MESES_NOMES = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}
STATUS_ORIGINAIS = ["A PAGAR", "BAIXA AUTOMÁTICA", "BAIXA MANUAL"]

# --- Barra Lateral ---
st.sidebar.title("Navegação")
pagina = st.sidebar.radio("Selecione a Página", [
    "Dashboard Principal", 
    "Análise de Custos Detalhada", 
    "Gestão de Pagamentos (Baixas)",
    "Relatório Analítico (Mensal/Anual)", 
    "Adicionar / Importar Dados" 
])
st.sidebar.divider()
st.sidebar.markdown("### Configuração Geral")
orcamento_padrao = st.sidebar.number_input("Orçamento Padrão (R$)", value=450000.0, step=1000.0, help="Este valor será usado caso o mês não tenha um orçamento congelado.")

# 2. Inicialização de Memória e Dados
@st.cache_data
def carregar_e_tratar_csv(file):
    try:
        df = pd.read_csv(file, encoding='utf-16-le', sep=';', skiprows=1, on_bad_lines='skip', engine='python')
        for col in ['Valor documento', 'Valor pago']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace('R$', '', regex=False).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).astype(float)
        
        if 'Situação pagamento documento' in df.columns: df['Situação pagamento documento'] = df['Situação pagamento documento'].fillna('A PAGAR')
        if 'Código documento' in df.columns: df['Código documento'] = df['Código documento'].astype(str)
        if 'Data vencimento' in df.columns:
            data_dt = pd.to_datetime(df['Data vencimento'], format='%d/%m/%Y', errors='coerce')
            df['Ano'] = data_dt.dt.year.fillna(datetime.datetime.now().year).astype(int)
            df['Mês'] = data_dt.dt.month.fillna(datetime.datetime.now().month).astype(int)
        return df
    except Exception as e:
        return pd.DataFrame()

# Banco de Dados de Lançamentos
if 'df_dados' not in st.session_state: st.session_state['df_dados'] = carregar_e_tratar_csv('RelatorioCAP.csv')
# Cofre de Orçamentos Congelados (Guarda os orçamentos definidos para cada mês)
if 'orcamentos_congelados' not in st.session_state: st.session_state['orcamentos_congelados'] = {}

df = st.session_state['df_dados']

def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

if not df.empty:
    
    # ==========================================
    # PÁGINA 1: DASHBOARD PRINCIPAL
    # ==========================================
    if pagina == "Dashboard Principal":
        st.title("📊 Dashboard Principal - Setor de Marketing")
        st.markdown("### Selecione o Período de Análise")
        col_ano, col_mes = st.columns(2)
        
        anos_disponiveis = sorted(df['Ano'].dropna().unique().tolist())
        if not anos_disponiveis: anos_disponiveis = [datetime.datetime.now().year]
        ano_selecionado = col_ano.selectbox("Ano de Referência", anos_disponiveis, index=len(anos_disponiveis)-1)
        
        meses_disponiveis = sorted(df[df['Ano'] == ano_selecionado]['Mês'].dropna().unique().tolist())
        meses_opcoes = [MESES_NOMES.get(m, str(m)) for m in meses_disponiveis]
        if not meses_opcoes: meses_opcoes = [MESES_NOMES[datetime.datetime.now().month]]
        mes_selecionado_nome = col_mes.selectbox("Mês de Referência", meses_opcoes)
        
        mes_selecionado = [k for k, v in MESES_NOMES.items() if v == mes_selecionado_nome][0]
        
        # Recupera o orçamento congelado para este mês (se não houver, usa o padrão da barra lateral)
        chave_mes = f"{ano_selecionado}-{mes_selecionado}"
        orcamento_vigente = st.session_state['orcamentos_congelados'].get(chave_mes, orcamento_padrao)
        
        df_mes = df[(df['Ano'] == ano_selecionado) & (df['Mês'] == mes_selecionado)]
        total_doc_mes = df_mes['Valor documento'].sum()
        total_pago_mes = df_mes['Valor pago'].sum()
        saldo_pendente_mes = total_doc_mes - total_pago_mes
        
        st.divider()
        
        # Alerta Dinâmico integrado ao Orçamento Congelado
        if total_doc_mes > orcamento_vigente:
            st.error(f"⚠️ ALERTA DE ORÇAMENTO: Em {mes_selecionado_nome}/{ano_selecionado}, o limite de {formatar_moeda(orcamento_vigente)} foi ultrapassado! Total lançado: {formatar_moeda(total_doc_mes)}")
        else:
            st.success(f"✅ Orçamento sob controle em {mes_selecionado_nome}/{ano_selecionado}. Disponível: {formatar_moeda(orcamento_vigente - total_doc_mes)}")
            
        st.header(f"Resumo Financeiro ({mes_selecionado_nome}/{ano_selecionado})")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Lançado (Mês)", formatar_moeda(total_doc_mes))
        c2.metric("Total Pago (Mês)", formatar_moeda(total_pago_mes))
        c3.metric("Saldo Pendente (Mês)", formatar_moeda(saldo_pendente_mes))

        st.subheader("Distribuição de Gastos por Plano de Contas")
        if not df_mes.empty:
            df_agrupado = df_mes.groupby('PlanoConta')['Valor documento'].sum().reset_index()
            fig = px.bar(df_agrupado.sort_values(by='Valor documento', ascending=False), x='PlanoConta', y='Valor documento', text_auto='.2s', color='PlanoConta')
            fig.update_layout(showlegend=False, yaxis_title="Valor (R$)")
            st.plotly_chart(fig, use_container_width=True)

    # ==========================================
    # PÁGINA 2: ANÁLISE DE CUSTOS DETALHADA
    # ==========================================
    elif pagina == "Análise de Custos Detalhada":
        st.title("🔎 Análise de Custos Detalhada")
        
        st.subheader("📈 Evolução Mensal de Custos (Todos os Períodos)")
        df_temporal = df.groupby(['Ano', 'Mês'])['Valor documento'].sum().reset_index()
        df_temporal = df_temporal.sort_values(by=['Ano', 'Mês'])
        df_temporal['Período'] = df_temporal['Mês'].map(MESES_NOMES).astype(str) + "/" + df_temporal['Ano'].astype(str)
        
        fig_linha = px.bar(df_temporal, x='Período', y='Valor documento', text_auto='.2s', title="Custo Total Lançado por Mês")
        st.plotly_chart(fig_linha, use_container_width=True)
        
        st.divider()
        st.subheader("🧩 Representatividade por Categoria (Global)")
        total_doc_global = df['Valor documento'].sum()
        df_custos = df.groupby('PlanoConta')['Valor documento'].sum().reset_index().sort_values(by='Valor documento', ascending=False)
        df_custos['% do Orçamento Padrão'] = (df_custos['Valor documento'] / orcamento_padrao) * 100
        df_custos['% do Total Gasto'] = (df_custos['Valor documento'] / total_doc_global) * 100
        
        col_grafico, col_tabela = st.columns([1, 1.2])
        with col_grafico:
            st.plotly_chart(px.pie(df_custos, values='Valor documento', names='PlanoConta', title='Divisão dos Gastos'), use_container_width=True)
        with col_tabela:
            df_display = df_custos.copy()
            df_display['Valor documento'] = df_display['Valor documento'].apply(formatar_moeda)
            df_display['% do Orçamento Padrão'] = df_display['% do Orçamento Padrão'].apply(lambda x: f"{x:.2f}%")
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
        if 'Valor documento' in df_exibicao.columns: df_exibicao['Valor Visual'] = df_exibicao['Valor documento'].apply(formatar_moeda)
        colunas_disponiveis = [c for c in colunas_exibicao if c in df_exibicao.columns]
        
        with st.form("form_edicao"):
            df_editado = st.data_editor(
                df_exibicao[colunas_disponiveis],
                column_config={"Situação pagamento documento": st.column_config.SelectboxColumn("Situação", options=STATUS_ORIGINAIS, required=True)},
                disabled=["Código documento", "Fornecedor", "PlanoConta", "Data vencimento", "Valor Visual"],
                use_container_width=True, hide_index=True, height=400
            )
            if st.form_submit_button("💾 Salvar Alterações e Recalcular"):
                df['Situação pagamento documento'] = df_editado['Situação pagamento documento']
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
        st.title("📅 Relatório Analítico e Orçamentário")
        
        col_filtro1, col_filtro2, col_filtro3 = st.columns(3)
        anos_disponiveis = sorted(df['Ano'].dropna().unique().tolist())
        ano_selecionado = col_filtro1.selectbox("Selecione o Ano", ["Todos"] + anos_disponiveis)
        
        meses_disponiveis = sorted(df['Mês'].dropna().unique().tolist())
        mes_selecionado_nome = col_filtro2.selectbox("Selecione o Mês", ["Todos"] + [MESES_NOMES.get(m, str(m)) for m in meses_disponiveis])
        
        situacoes_selecionadas = col_filtro3.multiselect("Filtre por Situação:", options=STATUS_ORIGINAIS, default=STATUS_ORIGINAIS)
        
        # --- PAINEL DE CONGELAMENTO DE ORÇAMENTO (Aparece só se escolher um mês específico) ---
        if ano_selecionado != "Todos" and mes_selecionado_nome != "Todos":
            mes_selecionado = [k for k, v in MESES_NOMES.items() if v == mes_selecionado_nome][0]
            chave_atual = f"{ano_selecionado}-{mes_selecionado}"
            
            # Lógica para encontrar o mês anterior
            if mes_selecionado == 1:
                mes_ant, ano_ant = 12, ano_selecionado - 1
            else:
                mes_ant, ano_ant = mes_selecionado - 1, ano_selecionado
                
            chave_anterior = f"{ano_ant}-{mes_ant}"
            
            orc_atual_salvo = st.session_state['orcamentos_congelados'].get(chave_atual, orcamento_padrao)
            orc_ant_salvo = st.session_state['orcamentos_congelados'].get(chave_anterior, "Não Definido")
            
            st.divider()
            st.markdown(f"### 🔒 Controle de Orçamento de {mes_selecionado_nome}/{ano_selecionado}")
            c_orc1, c_orc2, c_orc3 = st.columns([1.5, 1, 1.5])
            
            with c_orc1:
                novo_orc = st.number_input("Estipular / Alterar Estimativa Deste Mês (R$)", value=float(orc_atual_salvo))
            with c_orc2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("❄️ Congelar Orçamento"):
                    st.session_state['orcamentos_congelados'][chave_atual] = novo_orc
                    st.success("Orçamento congelado com sucesso!")
                    st.rerun()
            with c_orc3:
                valor_ant_texto = formatar_moeda(orc_ant_salvo) if isinstance(orc_ant_salvo, float) else orc_ant_salvo
                st.metric(f"Estimativa Congelada no Mês Anterior ({MESES_NOMES[mes_ant]}/{ano_ant})", valor_ant_texto)
                
        # Lógica de Filtragem Analítica
        df_filtrado = df.copy()
        if ano_selecionado != "Todos": df_filtrado = df_filtrado[df_filtrado['Ano'] == ano_selecionado]
        if mes_selecionado_nome != "Todos": df_filtrado = df_filtrado[df_filtrado['Mês'] == mes_selecionado]
        df_filtrado = df_filtrado[df_filtrado['Situação pagamento documento'].isin(situacoes_selecionadas)] if situacoes_selecionadas else df_filtrado.iloc[0:0] 
            
        st.divider()
        st.subheader(f"Resultados do Período Filtrado ({len(df_filtrado)} lançamentos)")
        c1, c2, c3 = st.columns(3)
        c1.metric("Valor Total Lançado", formatar_moeda(df_filtrado['Valor documento'].sum()))
        c2.metric("Valor Efetivamente Pago", formatar_moeda(df_filtrado['Valor pago'].sum()))
        c3.metric("Saldo Pendente", formatar_moeda(df_filtrado['Valor documento'].sum() - df_filtrado['Valor pago'].sum()))
        
        st.markdown("### 📋 Dados Analíticos Detalhados")
        df_exibicao_analitico = df_filtrado.copy()
        df_exibicao_analitico['Valor documento'] = df_exibicao_analitico['Valor documento'].apply(formatar_moeda)
        df_exibicao_analitico['Valor pago'] = df_exibicao_analitico['Valor pago'].apply(formatar_moeda)
        colunas_exibir = [c for c in ['Código documento', 'Fornecedor', 'PlanoConta', 'Data vencimento', 'Valor documento', 'Valor pago', 'Situação pagamento documento'] if c in df_exibicao_analitico.columns]
        st.dataframe(df_exibicao_analitico[colunas_exibir], use_container_width=True, hide_index=True)

    # ==========================================
    # PÁGINA 5: ADICIONAR / IMPORTAR DADOS
    # ==========================================
    elif pagina == "Adicionar / Importar Dados":
        st.title("➕ Alimentar Sistema")
        # (O código de importação permanece igual ao anterior)
        st.subheader("1. Importação Automática (Planilha CSV)")
        arquivo_upload = st.file_uploader("Arraste ou escolha o arquivo CSV", type=['csv'])
        if arquivo_upload is not None:
            df_novo = carregar_e_tratar_csv(arquivo_upload)
            if not df_novo.empty:
                df_filtrado = df_novo[~df_novo['Código documento'].isin(df['Código documento'].tolist())]
                if len(df_filtrado) > 0:
                    st.success(f"✅ Encontrados {len(df_filtrado)} novos lançamentos!")
                    if st.button("Integrar Novos Lançamentos"):
                        st.session_state['df_dados'] = pd.concat([df, df_filtrado], ignore_index=True)
                        st.rerun()
                else: st.info("Nenhum lançamento novo encontrado.")

        st.divider()
        st.subheader("2. Inclusão Manual (Lançamento Avulso)")
        with st.form("form_manual"):
            col_a, col_b = st.columns(2)
            codigo = col_a.text_input("Código do Documento", value=f"MANUAL-{int(datetime.datetime.now().timestamp())}")
            fornecedor = col_b.text_input("Fornecedor")
            col_c, col_d = st.columns(2)
            plano_conta = col_c.selectbox("Plano de Contas", df['PlanoConta'].dropna().unique().tolist() if 'PlanoConta' in df.columns else [])
            valor_novo = col_d.number_input("Valor da Despesa (R$)", min_value=0.0, format="%.2f")
            col_e, col_f = st.columns(2)
            data_venc = col_e.date_input("Data de Vencimento")
            situacao = col_f.selectbox("Situação", STATUS_ORIGINAIS)
            if st.form_submit_button("Registrar Lançamento Avulso") and fornecedor != "" and valor_novo > 0 and codigo not in df['Código documento'].values:
                novo_registro = pd.DataFrame([{'Código documento': codigo, 'Fornecedor': fornecedor, 'PlanoConta': plano_conta, 'Valor documento': valor_novo, 'Valor pago': valor_novo if situacao in ["BAIXA AUTOMÁTICA", "BAIXA MANUAL"] else 0.0, 'Data vencimento': data_venc.strftime('%d/%m/%Y'), 'Situação pagamento documento': situacao, 'Ano': data_venc.year, 'Mês': data_venc.month}])
                st.session_state['df_dados'] = pd.concat([df, novo_registro], ignore_index=True)
                st.success("Lançamento inserido!")
