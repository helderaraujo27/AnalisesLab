import streamlit as st
import pandas as pd
import plotly.express as px
import os

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Saúde Araújo", layout="wide", page_icon="🔬")

# BARRA LATERAL - SELEÇÃO DE MEMBRO
st.sidebar.title("👨‍👩‍👧‍👦 Família Araújo")
membro_ativo = st.sidebar.selectbox("Selecionar Membro:", ["Hélder", "Andreia", "Beatriz", "Carolina"])

@st.cache_data
def carregar_dados_sistema():
    ficheiro = "Registo Geral de Saúde.xlsx"
    if not os.path.exists(ficheiro):
        return None, None, "Ficheiro 'Registo Geral de Saúde.xlsx' não encontrado."
    
    try:
        # CARREGAR TABELA GERAL
        df = pd.read_excel(ficheiro, sheet_name="Tabela Geral", engine='openpyxl')
        
        # Radar de cabeçalho: Procura a linha que contém a palavra 'Análise'
        if 'Análise' not in [str(c).strip() for c in df.columns]:
            for i, row in df.iterrows():
                if "Análise" in [str(v).strip() for v in row.values]:
                    df.columns = [str(c).strip() for c in df.iloc[i]]
                    df = df.iloc[i+1:].reset_index(drop=True)
                    break
        df.columns = [str(c).strip() for c in df.columns]

        # CARREGAR RELAÇÕES (ENCICLOPÉDIA)
        try:
            biblio = pd.read_excel(ficheiro, sheet_name="Relações", engine='openpyxl')
            if 'Análise' not in [str(c).strip() for c in biblio.columns]:
                for i, row in biblio.iterrows():
                    if "Análise" in [str(v).strip() for v in row.values]:
                        biblio.columns = [str(c).strip() for c in biblio.iloc[i]]
                        biblio = biblio.iloc[i+1:].reset_index(drop=True)
                        break
            biblio.columns = [str(c).strip() for c in biblio.columns]
        except:
            biblio = None
            
        return df, biblio, None
    except Exception as e:
        return None, None, f"Erro técnico: {e}"

df_total, df_biblio, erro = carregar_dados_sistema()

if erro:
    st.error(f"⚠️ {erro}")
else:
    # FILTRAGEM POR MEMBRO
    # Procura na coluna 'Membro'. Se não existir, mostra tudo.
    if 'Membro' in df_total.columns:
        df_membro = df_total[df_total['Membro'].astype(str).str.contains(membro_ativo, na=False, case=False)].copy()
    else:
        df_membro = df_total.copy()
    
    # Tratamento de dados para as vistas
    df_membro['Data'] = pd.to_datetime(df_membro['Data'], errors='coerce')
    df_membro['Valor'] = pd.to_numeric(df_membro['Valor'], errors='coerce')
    if 'Resultado' in df_membro.columns:
        df_membro['Resultado'] = df_membro['Resultado'].astype(str).str.strip()

    st.title(f"Painel de Saúde: {membro_ativo}")

    # --- MÉTRICAS ---
    c1, c2, c3 = st.columns(3)
    c1.metric("Registos Totais", len(df_membro))
    c2.metric("Marcadores Únicos", df_membro['Análise'].nunique())
    
    # Alertas (Baseados na coluna Resultado)
    res_str = df_membro['Resultado'].str.lower()
    num_alertas = len(df_membro[res_str.str.contains('anormal|baixo|alto|fora|🚨', na=False)])
    c3.metric("Alertas Detetados", num_alertas, delta_color="inverse")

    # --- ABAS PRINCIPAIS ---
    tab_geral, tab_hist, tab_enc = st.tabs(["📋 Tabela Geral", "📈 Evolução Temporal", "📚 Enciclopédia"])

    with tab_geral:
        st.subheader("Histórico Completo de Exames")
        
        def definir_bola(resultado):
            r = str(resultado).lower()
            if any(x in r for x in ['anormal', 'baixo', 'alto', 'fora']): return "🔴 Alerta"
            if any(x in r for x in ['normal', 'dentro', 'ok']): return "🟢 Normal"
            return "⚪ Info"

        df_view = df_membro.copy()
        df_view.insert(0, 'Estado', df_view['Resultado'].apply(definir_bola))
        
        st.dataframe(
            df_view.sort_values('Data', ascending=False),
            use_container_width=True,
            column_order=["Estado", "Data", "Análise", "Valor", "Unidade", "Resultado", "Min", "Max", "Laboratório"]
        )

    with tab_hist:
        analises_disponiveis = sorted([str(a).strip() for a in df_membro['Análise'].unique() if str(a) not in ['nan', 'Análise']])
        if analises_disponiveis:
            sel = st.selectbox("Escolha o biomarcador:", analises_disponiveis)
            df_plot = df_membro[df_membro['Análise'] == sel].dropna(subset=['Data', 'Valor']).sort_values('Data')
            
            if not df_plot.empty:
                fig = px.line(df_plot, x='Data', y='Valor', markers=True, title=f"Tendência de {sel}")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sem dados numéricos suficientes para gráfico.")

    with tab_enc:
        st.subheader("Biblioteca de Definições")
        if df_biblio is not None:
            pesquisa = st.text_input("🔍 Procurar na biblioteca...", "").lower()
            
            for _, row in df_biblio.iterrows():
                # Lógica robusta para o título: tenta 'Análise', se falhar tenta a 4ª coluna
                titulo = str(row.get('Análise', row.iloc[3] if len(row) > 3 else "Marcador"))
                definicao = str(row.iloc[-1]) # A definição é sempre a última coluna
                
                if titulo != 'nan' and (pesquisa in titulo.lower() or pesquisa in definicao.lower()):
                    with st.expander(f"📖 {titulo}"):
                        st.write(definicao)
                        contexto = [str(v) for v in row.values if str(v) not in [titulo, definicao, 'nan']]
                        if contexto: st.caption(f"Contexto: {' | '.join(contexto)}")