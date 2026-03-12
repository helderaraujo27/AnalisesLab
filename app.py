import streamlit as st
import pandas as pd
import plotly.express as px

# 1. CONFIGURAÇÃO E IDENTIDADE DO MYHEALTHGUIDE
st.set_page_config(page_title="MyHealthGuide", layout="wide", page_icon="🛡️")

# O teu link do Google Sheets já formatado para exportação
URL_SHEET = "https://docs.google.com/spreadsheets/d/1RZU1XouQThGgE8LEQZxt_gvsJrJqD64yxhRq7bWBp-M/export?format=xlsx"

st.sidebar.title("🛡️ MyHealthGuide")
membro_ativo = st.sidebar.selectbox("Selecionar Utilizador:", ["Hélder", "Andreia", "Beatriz", "Carolina"])

@st.cache_data(ttl=300) # Atualiza os dados a cada 5 minutos
def carregar_dados_nuvem(url):
    try:
        # Lemos diretamente do Google Sheets
        df = pd.read_excel(url, sheet_name="Tabela Geral", engine='openpyxl')
        
        # Ajuste de cabeçalho automático
        if 'Análise' not in [str(c).strip() for c in df.columns]:
            for i, row in df.iterrows():
                if "Análise" in [str(v).strip() for v in row.values]:
                    df.columns = [str(c).strip() for c in df.iloc[i]]
                    df = df.iloc[i+1:].reset_index(drop=True)
                    break
        df.columns = [str(c).strip() for c in df.columns]

        biblio = pd.read_excel(url, sheet_name="Relações", engine='openpyxl')
        if 'Análise' not in [str(c).strip() for c in biblio.columns]:
            for i, row in biblio.iterrows():
                if "Análise" in [str(v).strip() for v in row.values]:
                    biblio.columns = [str(c).strip() for c in biblio.iloc[i]]
                    biblio = biblio.iloc[i+1:].reset_index(drop=True)
                    break
        biblio.columns = [str(c).strip() for c in biblio.columns]
        
        return df, biblio, None
    except Exception as e:
        return None, None, f"Erro ao ligar ao Google Sheets: {e}"

# EXECUÇÃO DA LEITURA
df_total, df_biblio, erro = carregar_dados_nuvem(URL_SHEET)

if erro:
    st.error(f"⚠️ {erro}")
    st.info("Verifica se o Google Sheet tem as abas 'Tabela Geral' e 'Relações' com os nomes exatos.")
else:
    # FILTRO POR MEMBRO (Hélder, Andreia, etc)
    if 'Membro' in df_total.columns:
        df_membro = df_total[df_total['Membro'].astype(str).str.contains(membro_ativo, na=False, case=False)].copy()
    else:
        df_membro = df_total.copy()
    
    # Conversão de dados
    df_membro['Data'] = pd.to_datetime(df_membro['Data'], errors='coerce')
    df_membro['Valor'] = pd.to_numeric(df_membro['Valor'], errors='coerce')

    st.title(f"Guia de Saúde: {membro_ativo}")

    # MÉTRICAS TOTAIS
    c1, c2, c3 = st.columns(3)
    c1.metric("Registos", len(df_membro))
    c2.metric("Biomarcadores", df_membro['Análise'].nunique())
    
    res_str = df_membro.get('Resultado', pd.Series([])).astype(str).str.lower()
    num_alertas = len(df_membro[res_str.str.contains('anormal|baixo|alto|fora|🚨', na=False)])
    c3.metric("Alertas", num_alertas, delta_color="inverse")

    tab_geral, tab_hist, tab_enc = st.tabs(["📋 Histórico Geral", "📈 Evolução", "📚 Dicionário"])

    with tab_geral:
        def marcar_estado(res):
            r = str(res).lower()
            if any(x in r for x in ['anormal', 'baixo', 'alto', 'fora']): return "🔴 Alerta"
            if any(x in r for x in ['normal', 'dentro', 'ok']): return "🟢 Normal"
            return "⚪ Info"

        df_view = df_membro.copy()
        df_view.insert(0, 'Estado', df_view.get('Resultado', '').apply(marcar_estado))
        st.dataframe(df_view.sort_values('Data', ascending=False), use_container_width=True)

    with tab_hist:
        lista = sorted([str(a).strip() for a in df_membro['Análise'].unique() if str(a) != 'nan'])
        if lista:
            sel = st.selectbox("Escolha o marcador para ver o gráfico:", lista)
            df_p = df_membro[df_membro['Análise'] == sel].dropna(subset=['Data', 'Valor']).sort_values('Data')
            if not df_p.empty:
                st.plotly_chart(px.line(df_p, x='Data', y='Valor', markers=True, title=f"Evolução: {sel}"), use_container_width=True)

    with tab_enc:
        st.subheader("Dicionário MyHealthGuide")
        pesquisa = st.text_input("🔍 O que quer saber? (ex: Colesterol, Ferro...)", "").lower()
        if df_biblio is not None:
            for _, row in df_biblio.iterrows():
                titulo = str(row.get('Análise', row.iloc[3] if len(row) > 3 else "Marcador"))
                def_txt = str(row.iloc[-1])
                if titulo != 'nan' and (pesquisa in titulo.lower() or pesquisa in def_txt.lower()):
                    with st.expander(f"📖 {titulo}"):
                        st.write(def_txt)
