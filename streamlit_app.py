import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# -------------------- PAGINA INSTELLINGEN --------------------
st.set_page_config(
    page_title="Callie NL - Performance Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Callie NL — Performance Dashboard & Trends")
st.caption("Data rechtstreeks uit Google Sheets (gefilterd op de Callie NL sectie).")

# -------------------- DATA OPHALEN EN OMZETTEN --------------------
SHEET_URL = "https://docs.google.com/spreadsheets/d/1GLAGMkVx5DMXylG0bbdvkzuqTd8IVfDANhcRrAX6LFU/edit?usp=sharing"

@st.cache_data(ttl=60)
def load_and_transform_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # We lezen de exacte rij-range van Callie NL uit (Rij 88 t/m 106)
    # Geen header meegeven omdat de metrics verticaal staan
    raw_df = conn.read(
        spreadsheet=SHEET_URL,
        skiprows=87,
        nrows=19,
        header=None
    )
    
    # Kolom 0 bevat de KPI-namen (Superset SEO销售额, etc.)
    # Kolom 1 en verder bevatten de datums en de cijfers
    metrics_names = raw_df.iloc[:, 0].tolist()
    
    # Filter lege namen eruit
    data_matrix = raw_df.iloc[:, 1:]
    
    # Kantel de tabel om (Transponeren): Datums worden rijen, KPI's worden kolommen
    df_transposed = data_matrix.T
    
    # Stel de kolomnamen in op basis van de Chinese KPI-titels uit kolom A
    df_transposed.columns = metrics_names
    
    # Maak een nette datumkolom van de eerste datumpunt
    # De eerste rij van onze selectie bevat de datums
    df_transposed = df_transposed.rename(columns={df_transposed.columns[0]: "Datum_Raw"})
    
    # Zet de datumkolom om naar echt datumformaat (fouten negeren bij lege kolommen)
    df_transposed['Datum'] = pd.to_datetime(df_transposed['Datum_Raw'], errors='coerce')
    
    # Verwijder rijen waar geen geldige datum in staat
    df_transposed = df_transposed.dropna(subset=['Datum'])
    
    # Zet alle numerieke kolommen om van tekst naar getallen
    numeric_cols = [c for c in df_transposed.columns if c not in ['Datum_Raw', 'Datum', '网站要事记']]
    for col in numeric_cols:
        # Verwijder eventuele valuta-tekens (€, %, komma's) en zet om naar float
        df_transposed[col] = (
            df_transposed[col]
            .astype(str)
            .str.replace('€', '', regex=False)
            .str.replace('%', '', regex=False)
            .str.replace(',', '', regex=False)
            .str.strip()
        )
        df_transposed[col] = pd.to_numeric(df_transposed[col], errors='coerce').fillna(0)
        
    return df_transposed.sort_values('Datum')

try:
    df = load_and_transform_data()

    # -------------------- SIDEBAR FILTERS --------------------
    st.sidebar.header("📅 Periode Selectie")
    min_date = df['Datum'].min().date()
    max_date = df['Datum'].max().date()

    start_date, end_date = st.sidebar.date_input(
        "Datumbereik:",
        value=[min_date, max_date],
        min_value=min_date,
        max_value=max_date
    )

    # Filter op datumbereik
    filtered_df = df[(df['Datum'].dt.date >= start_date) & (df['Datum'].dt.date <= end_date)]

    # -------------------- KPI SAMENVATTING (LAATSTE DATUM) --------------------
    latest = filtered_df.iloc[-1] if not filtered_df.empty else df.iloc[-1]
    
    st.subheader(f"📌 Status op {latest['Datum'].strftime('%d-%m-%Y')}")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("GA4 SEO Omzet (销售额)", f"€ {latest.get('GA4 SEO销售额', 0):,.2f}")
        st.caption(f"Superset Omzet: € {latest.get('Superset SEO销售额', 0):,.2f}")
    with col2:
        st.metric("Totale Omzet Website", f"€ {latest.get('GA4 网站总销售额', 0):,.2f}")
        st.caption(f"Superset Aandeel: {latest.get('Superset 总销售额占比情况', 0)}%")
    with col3:
        st.metric("SEO Verkeer (流量)", f"{int(latest.get('SEO流量', 0)):,}")
        st.caption(f"Blog Verkeer: {int(latest.get('SEO Blog流量', 0)):,}")
    with col4:
        st.metric("AI Assistant Verkeer", f"{int(latest.get('AI Assistant 流量', 0)):,}")
        st.caption(f"AI Omzet: € {latest.get('AI Assistant 销售额', 0):,.2f}")

    st.markdown("---")

    # -------------------- GRAFIEKEN OVER TIJD --------------------
    st.subheader("📈 Trends & Verloop over Tijd")

    tab1, tab2, tab3 = st.tabs(["💰 Omzet Trends", "📈 Verkeer & Traffic", "🔍 SEO Status"])

    with tab1:
        fig_sales = px.line(
            filtered_df,
            x="Datum",
            y=["GA4 SEO销售额", "Superset SEO销售额", "GA4 网站总销售额", "AI Assistant 销售额"],
            title="Omzetontwikkeling (€)",
            markers=True
        )
        fig_sales.update_layout(hovermode="x unified")
        st.plotly_chart(fig_sales, use_container_width=True)

    with tab2:
        fig_traffic = px.line(
            filtered_df,
            x="Datum",
            y=["SEO流量", "SEO 站内流量", "SEO Blog流量", "网站总流量", "AI Assistant 流量"],
            title="Verkeersontwikkeling (Aantal Bezoekers)",
            markers=True
        )
        fig_traffic.update_layout(hovermode="x unified")
        st.plotly_chart(fig_traffic, use_container_width=True)

    with tab3:
        col_a, col_b = st.columns(2)
        with col_a:
            fig_index = px.line(
                filtered_df,
                x="Datum",
                y=["收录", "Blog 收录"],
                title="Geïndexeerde Pagina's (收录)",
                markers=True
            )
            st.plotly_chart(fig_index, use_container_width=True)
            
        with col_b:
            fig_backlinks = px.line(
                filtered_df,
                x="Datum",
                y=["外链", "外链域名广度"],
                title="Backlinks & Domain Breadth (外链)",
                markers=True
            )
            st.plotly_chart(fig_backlinks, use_container_width=True)

    # -------------------- BELANGRIJKE GEBEURTENISSEN --------------------
    if '网站要事记' in filtered_df.columns:
        st.markdown("---")
        st.subheader("📝 网站要事记 (Website Notities & Logboek)")
        notes_df = filtered_df[filtered_df['网站要事记'].astype(str).str.len() > 1][['Datum', '网站要事记']]
        if not notes_df.empty:
            for idx, row in notes_df.iterrows():
                st.info(f"**{row['Datum'].strftime('%d-%m-%Y')}**: {row['网站要事记']}")
        else:
            st.write("Geen notities gevonden in de geselecteerde periode.")

except Exception as e:
    st.error("Er is een fout opgetreden bij het inlezen van de Google Sheet.")
    st.write(f"Technisch detail: {e}")
