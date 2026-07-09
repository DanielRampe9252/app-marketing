import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import json
import os
from streamlit_gsheets import GSheetsConnection

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
orcamento_padrao = st.sidebar.number_input("Orçamento Padrão (R$)", value=450000.0, step=1000.0)

# ==========================================
# 2. CONEXÃO COM O GOOGLE SHEETS
# ==========================================
try:
    url_planilha = st.secrets["spreadsheet_url"]
    
    # O pulo do gato: cria um arquivo seguro com a chave para o Google ler diretamente!
    with open("google_credentials.json", "w", encoding="utf-8") as f:
        f.write(st.secrets["google_json"])
    
    # Avisa ao sistema operacional onde a chave está
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_credentials.json"
    
    # Inicia a conexão limpa (o Google puxa a chave sozinho)
    conn = st.connection("gsheets", type=GSheetsConnection)
    
except Exception as e:
    st.error(f"Erro na configuração de credenciais. Detalhe: {e}")
    st.stop()

@st.cache_data(ttl=30)
def carregar_do_google():
    try:
        df = conn.read(spreadsheet=url_planilha)
        df = df.dropna(how="all") 
        
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
        st.error(f"Erro ao carregar dados do Google Sheets: {e}")
        return pd.DataFrame()

def salvar_no_google(df_novo):
    with st.spinner("Sincronizando com o Banco de Dados (Google Sheets)..."):
        df_salvar = df_novo.copy()
        df_salvar = df_salvar.fillna("") 
        conn.update(spreadsheet=url_planilha, data=df_salvar)
        st.cache_data.clear() 
        st.session_state['df_dados'] = df_novo

if 'df_dados' not in st.session_state: st.session_state['df_dados'] = carregar_do_google()
if 'orcamentos_congelados' not in st.session_state: st.session_state['orcamentos_congelados'] = {}

if 'dash_ano' not in st.session_state: st.session_state['dash_ano'] = datetime.datetime.now().year
if 'dash_mes_nome' not in st.session_state: st.session_state['dash_mes_nome'] = MESES_NOMES.get(datetime.datetime.now().month, 'Janeiro')

df = st.session_state['df_dados']

def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

if not df.empty:
    if 'Ano' not in df.columns or 'Mês' not in df.columns:
        if 'Data vencimento' in df.columns:
            data_dt = pd.to_datetime(df['Data vencimento'], format='%d/%m/%Y', errors='coerce')
            df['Ano'] = data_dt.dt.year.fillna(datetime.datetime.now().year).astype(int)
            df['Mês'] = data_dt.dt.month.fillna(datetime.datetime.now().month).astype(int)
            st.session_state['df_dados'] = df

    # ==========================================
    # PÁGINA 1: DASHBOARD PRINCIPAL
    # ==========================================
    if pagina == "Dashboard Principal":
        st.title("📊 Dashboard Principal - Setor de Marketing")
        col_ano, col_mes = st.columns(2)
        
        anos_disponiveis = sorted(df['Ano'].dropna().unique().tolist())
        if not anos_disponiveis: anos_disponiveis = [datetime.datetime.now().year]
        try: idx_ano = anos_disponiveis.index(st.session_state['dash_ano'])
        except ValueError: idx_ano = len(anos_disponiveis)-1
            
        ano_selecionado = col_ano.selectbox("Ano de Referência", anos_disponiveis, index=idx_ano)
        st.session_state['dash_ano'] = ano_selecionado 
        
        meses_disponiveis = sorted(df[df['Ano'] == ano_selecionado]['Mês'].dropna().unique().tolist())
        meses_opcoes = [MESES_NOMES.get(m, str(m)) for m in meses_disponiveis]
        if not meses_opcoes: meses_opcoes = [MESES_NOMES[datetime.datetime.now().month]]
        try: idx_mes = meses_opcoes.index(st.session_state['dash_mes_nome'])
        except ValueError: idx_mes = 0
            
        mes_selecionado_nome = col_mes.selectbox("Mês de Referência", meses_opcoes, index=idx_mes)
        st.session_state['dash_mes_nome'] = mes_selecionado_nome 
        mes_selecionado = [k for k, v in MESES_NOMES.items() if v == mes_selecionado_nome][0]
        
        chave_mes = f"{ano_selecionado}-{mes_selecionado}"
        orcamento_vigente = st.session_state['orcamentos_congelados'].get(chave_mes, orcamento_padrao)
        
        df_mes = df[(df['Ano'] == ano_selecionado) & (df['Mês'] == mes_selecionado)]
        total_doc_mes = df_mes['Valor documento'].sum()
        total_pago_mes = df_mes['Valor pago'].sum()
        saldo_pendente_mes = total_doc_mes - total_pago_mes
        diferenca_orcamento = total_doc_mes - orcamento_vigente
        
        st.divider()
        st.header(f"Resumo Financeiro ({mes_selecionado_nome}/{ano_selecionado})")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Lançado (Mês)", formatar_moeda(total_doc_mes))
        c2.metric("Total Pago (Mês)", formatar_moeda(total_pago_mes))
        c3.metric("Saldo Pendente (Mês)", formatar_moeda(saldo_pendente_mes))
        
        if diferenca_orcamento > 0:
            st.error(f"⚠️ ALERTA DE ORÇAMENTO: Em {mes_selecionado_nome}/{ano_selecionado}, o limite de {formatar_moeda(orcamento_vigente)} foi ultrapassado na quantia de {formatar_moeda(diferenca_orcamento)}!")
            c4.metric("🚨 Valor Ultrapassado", formatar_moeda(diferenca_orcamento))
        else:
            st.success(f"✅ Orçamento sob controle em {mes_selecionado_nome}/{ano_selecionado}.")
            c4.metric("Orçamento Disponível", formatar_moeda(abs(diferenca_orcamento)))

        st.subheader("Distribuição de Gastos")
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
        st.subheader("📈 Evolução Mensal de Custos")
        df_temporal = df.groupby(['Ano', 'Mês'])['Valor documento'].sum().reset_index().sort_values(by=['Ano', 'Mês'])
        df_temporal['Período'] = df_temporal['Mês'].map(MESES_NOMES).astype(str) + "/" + df_temporal['Ano'].astype(str)
        st.plotly_chart(px.bar(df_temporal, x='Período', y='Valor documento', text_auto='.2s'), use_container_width=True)
        
        st.divider()
        st.subheader("🧩 Representatividade Global")
        total_doc_global = df['Valor documento'].sum()
        df_custos = df.groupby('PlanoConta')['Valor documento'].sum().reset_index().sort_values(by='Valor documento', ascending=False)
        df_custos['% do Orçamento Padrão'] = (df_custos['Valor documento'] / orcamento_padrao) * 100
        df_custos['% do Total Gasto'] = (df_custos['Valor documento'] / total_doc_global) * 100
        
        col_grafico, col_tabela = st.columns([1, 1.2])
        with col_grafico:
            st.plotly_chart(px.pie(df_custos, values='Valor documento', names='PlanoConta'), use_container_width=True)
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
        st.info("💡 Qualquer alteração salva aqui será gravada imediatamente na sua planilha do Google Sheets.")
        
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
            if st.form_submit_button("💾 Salvar Alterações na Nuvem"):
                df['Situação pagamento documento'] = df_editado['Situação pagamento documento']
                pagos_mask = df['Situação pagamento documento'].isin(["BAIXA AUTOMÁTICA", "BAIXA MANUAL"])
                df.loc[pagos_mask, 'Valor pago'] = df['Valor documento']
                df.loc[~pagos_mask, 'Valor pago'] = 0.0
                salvar_no_google(df)
                st.success("✅ Banco de dados atualizado com sucesso!")
                st.rerun()

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
        
        if ano_selecionado != "Todos" and mes_selecionado_nome != "Todos":
            mes_selecionado = [k for k, v in MESES_NOMES.items() if v == mes_selecionado_nome][0]
            chave_atual = f"{ano_selecionado}-{mes_selecionado}"
            mes_ant, ano_ant = (12, ano_selecionado - 1) if mes_selecionado == 1 else (mes_selecionado - 1, ano_selecionado)
            chave_anterior = f"{ano_ant}-{mes_ant}"
            orc_atual_salvo = st.session_state['orcamentos_congelados'].get(chave_atual, orcamento_padrao)
            orc_ant_salvo = st.session_state['orcamentos_congelados'].get(chave_anterior, "Não Definido")
            
            st.divider()
            c_orc1, c_orc2, c_orc3 = st.columns([1.5, 1, 1.5])
            with c_orc1: novo_orc = st.number_input(f"Congelar Estimativa para {mes_selecionado_nome} (R$)", value=float(orc_atual_salvo))
            with c_orc2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("❄️ Congelar"):
                    st.session_state['orcamentos_congelados'][chave_atual] = novo_orc
                    st.rerun()
            with c_orc3:
                st.metric(f"Mês Anterior ({MESES_NOMES.get(mes_ant, mes_ant)})", formatar_moeda(orc_ant_salvo) if isinstance(orc_ant_salvo, float) else orc_ant_salvo)
                
        df_filtrado = df.copy()
        if ano_selecionado != "Todos": df_filtrado = df_filtrado[df_filtrado['Ano'] == ano_selecionado]
        if mes_selecionado_nome != "Todos": df_filtrado = df_filtrado[df_filtrado['Mês'] == mes_selecionado]
        df_filtrado = df_filtrado[df_filtrado['Situação pagamento documento'].isin(situacoes_selecionadas)] if situacoes_selecionadas else df_filtrado.iloc[0:0] 
            
        st.divider()
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
        st.title("➕ Alimentar Banco de Dados (Nuvem)")
        
        st.subheader("1. Importação Automática (Planilha CSV)")
        arquivo_upload = st.file_uploader("Suba um CSV para cruzar com o Banco de Dados:", type=['csv'])
        if arquivo_upload is not None:
            try:
                df_novo = pd.read_csv(arquivo_upload, encoding='utf-16-le', sep=';', skiprows=1, on_bad_lines='skip', engine='python')
                for col in ['Valor documento', 'Valor pago']:
                    if col in df_novo.columns:
                        df_novo[col] = df_novo[col].astype(str).str.replace('R$', '', regex=False).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).astype(float)
                if 'Situação pagamento documento' in df_novo.columns: df_novo['Situação pagamento documento'] = df_novo['Situação pagamento documento'].fillna('A PAGAR')
                if 'Código documento' in df_novo.columns: df_novo['Código documento'] = df_novo['Código documento'].astype(str)
                if 'Data vencimento' in df_novo.columns:
                    data_dt = pd.to_datetime(df_novo['Data vencimento'], format='%d/%m/%Y', errors='coerce')
                    df_novo['Ano'] = data_dt.dt.year.fillna(datetime.datetime.now().year).astype(int)
                    df_novo['Mês'] = data_dt.dt.month.fillna(datetime.datetime.now().month).astype(int)
            except Exception as e:
                st.error("Erro na leitura do CSV.")
                df_novo = pd.DataFrame()

            if not df_novo.empty:
                df_filtrado = df_novo[~df_novo['Código documento'].isin(df['Código documento'].tolist())]
                if len(df_filtrado) > 0:
                    st.success(f"✅ Encontrados {len(df_filtrado)} novos lançamentos!")
                    if st.button("Integrar Novos Lançamentos ao Banco de Dados"):
                        df_atualizado = pd.concat([df, df_filtrado], ignore_index=True)
                        salvar_no_google(df_atualizado)
                        st.success("Google Sheets atualizado! Os dados estão salvos permanentemente.")
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
            
            if st.form_submit_button("Salvar no Banco de Dados") and fornecedor != "" and valor_novo > 0 and codigo not in df['Código documento'].values:
                novo_registro = pd.DataFrame([{'Código documento': codigo, 'Fornecedor': fornecedor, 'PlanoConta': plano_conta, 'Valor documento': valor_novo, 'Valor pago': valor_novo if situacao in ["BAIXA AUTOMÁTICA", "BAIXA MANUAL"] else 0.0, 'Data vencimento': data_venc.strftime('%d/%m/%Y'), 'Situação pagamento documento': situacao, 'Ano': data_venc.year, 'Mês': data_venc.month}])
                df_atualizado = pd.concat([df, novo_registro], ignore_index=True)
                salvar_no_google(df_atualizado)
                st.success("Lançamento inserido e salvo no Google Sheets!")

else:
    st.info("Aguardando carregamento dos dados da Nuvem...")
