import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection

# -------------------- PAGINA INSTELLINGEN --------------------
st.set_page_config(
    page_title="Callie NL - Performance Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Callie NL — Performance Dashboard (Individuele YoY Trends)")
st.caption("Alle metrieken individueel vergeleken met exact dezelfde dag vorig jaar (364 dagen geleden).")

# -------------------- DATA OPHALEN EN OMZETTEN --------------------
SHEET_URL = "https://docs.google.com/spreadsheets/d/1GLAGMkVx5DMXylG0bbdvkzuqTd8IVfDANhcRrAX6LFU/edit?usp=sharing"

def clean_number(val):
    """
    Converteert Nederlandse/Europese getalnotaties naar een float die Python kan begrijpen.
    """
    if pd.isna(val):
        return 0.0
    
    s = str(val).replace('€', '').replace('$', '').replace('%', '').strip()
    
    if not s or s.lower() == 'nan':
        return 0.0

    if '.' in s and ',' in s:
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s and '.' not in s:
        s = s.replace(',', '.')
    elif '.' in s and ',' not in s:
        parts = s.split('.')
        if len(parts[-1]) == 3:
            s = s.replace('.', '')

    try:
        return float(s)
    except ValueError:
        return 0.0

@st.cache_data(ttl=60)
def load_and_transform_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # We lezen de exacte rij-range van Callie NL uit (Rij 88 t/m 106)
    raw_df = conn.read(
        spreadsheet=SHEET_URL,
        skiprows=87,
        nrows=19,
        header=None
    )
    
    metrics_names = raw_df.iloc[:, 0].tolist()
    data_matrix = raw_df.iloc[:, 1:]
    
    # Transponeren (转置 - zhuǎnzhì): Datums worden rijen, KPI's worden kolommen
    df_transposed = data_matrix.T
    df_transposed.columns = metrics_names
    
    # Maak een nette datumkolom van het eerste datumpunt
    df_transposed = df_transposed.rename(columns={df_transposed.columns[0]: "Datum_Raw"})
    df_transposed['Datum'] = pd.to_datetime(df_transposed['Datum_Raw'], errors='coerce')
    df_transposed = df_transposed.dropna(subset=['Datum'])
    
    # Numerieke kolommen opschonen
    numeric_cols = [c for c in df_transposed.columns if c not in ['Datum_Raw', 'Datum', '网站要事记']]
    for col in numeric_cols:
        df_transposed[col] = df_transposed[col].apply(clean_number)
        
    return df_transposed.sort_values('Datum'), numeric_cols

def create_yoy_chart(df_merged, col, title, y_label, color_current="#1f77b4", color_ly="#aec7e8"):
    """
    Maakt een individuele YoY grafiek voor één specifieke metriek.
    """
    fig = go.Figure()
    
    # Dit Jaar
    if col in df_merged.columns:
        fig.add_trace(go.Scatter(
            x=df_merged['Datum'],
            y=df_merged[col],
            mode='lines+markers',
            name='Dit Jaar',
            line=dict(color=color_current, width=3)
        ))
    
    # Vorig Jaar (364 dagen geleden)
    col_ly = f"{col}_LY"
    if col_ly in df_merged.columns:
        fig.add_trace(go.Scatter(
            x=df_merged['Datum'],
            y=df_merged[col_ly],
            mode='lines+markers',
            name='Vorig Jaar (364d geleden)',
            line=dict(color=color_ly, width=2, dash='dash')
        ))

    fig.update_layout(
        title=title,
        xaxis_title="Datum",
        yaxis_title=y_label,
        hovermode="x unified",
        margin=dict(l=20, r=20, t=40, b=20),
        height=380
    )
    return fig

try:
    df, numeric_cols = load_and_transform_data()

    # -------------------- STANDAARD DATUMINSTELLING --------------------
    # Vandaag - 2 dagen (einddatum) & Vandaag - 9 dagen (startdatum = 1 week voor einddatum)
    today = pd.Timestamp.now().normalize()
    min_date = df['Datum'].min().date()
    max_date = df['Datum'].max().date()

    default_end = min(today.date() - pd.Timedelta(days=2), max_date)
    if default_end < min_date:
        default_end = max_date
        
    default_start = max(default_end - pd.Timedelta(days=7), min_date)

    st.sidebar.header("📅 Periode Selectie")
    start_date, end_date = st.sidebar.date_input(
        "Selecteer datum bereik:",
        value=[default_start, default_end],
        min_value=min_date,
        max_value=max_date
    )

    # Filter huidige periode
    current_df = df[(df['Datum'].dt.date >= start_date) & (df['Datum'].dt.date <= end_date)].copy()

    # -------------------- YOY MATCHING VOOR ALLE METRIEKEN --------------------
    # 52 weken * 7 dagen = 364 dagen (exact dezelfde weekdag vorig jaar)
    YOY_OFFSET = pd.Timedelta(days=364)
    current_df['Datum_Vorig_Jaar'] = current_df['Datum'] - YOY_OFFSET
    
    # Koppel Vorig Jaar data voor ALLE numerieke kolommen
    cols_to_merge = [c for c in numeric_cols if c in df.columns]
    merged_df = pd.merge(
        current_df,
        df[['Datum'] + cols_to_merge],
        left_on='Datum_Vorig_Jaar',
        right_on='Datum',
        how='left',
        suffixes=('', '_LY')
    )

    # -------------------- KPI SAMENVATTING (LAATSTE GESELECTEERDE DAG) --------------------
    latest = current_df.iloc[-1] if not current_df.empty else df.iloc[-1]
    
    st.subheader(f"📌 Status op {latest['Datum'].strftime('%d-%m-%Y')}")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("GA4 SEO Omzet", f"€ {latest.get('GA4 SEO销售额', 0):,.2f}")
        st.caption(f"Superset Omzet: € {latest.get('Superset SEO销售额', 0):,.2f}")
    with col2:
        st.metric("Totale Omzet Website", f"€ {latest.get('GA4 网站总销售额', 0):,.2f}")
        st.caption(f"Superset Aandeel: {latest.get('Superset 总销售额占比情况', 0)}%")
    with col3:
        st.metric("SEO Verkeer", f"{int(latest.get('SEO流量', 0)):,}")
        st.caption(f"Blog Verkeer: {int(latest.get('SEO Blog流量', 0)):,}")
    with col4:
        st.metric("AI Assistant Verkeer", f"{int(latest.get('AI Assistant 流量', 0)):,}")
        st.caption(f"AI Omzet: € {latest.get('AI Assistant 销售额', 0):,.2f}")

    st.markdown("---")

    # -------------------- INDIVIDUELE GRAFIEKEN PER TAB --------------------
    st.subheader("📈 Individuele YoY Grafieken (Dit Jaar vs Vorig Jaar)")

    tab1, tab2, tab3 = st.tabs(["💰 Omzet Metrics", "📈 Verkeer Metrics", "🔍 SEO & Backlink Status"])

    # TAB 1: OMZET
    with tab1:
        col_a, col_b = st.columns(2)
        with col_a:
            st.plotly_chart(create_yoy_chart(merged_df, "GA4 SEO销售额", "GA4 SEO Omzet (€)", "Omzet (€)", "#1f77b4"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "GA4 网站总销售额", "Totale Website Omzet (€)", "Omzet (€)", "#2ca02c"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "Superset 总销售额占比情况", "Superset Omzet Aandeel (%)", "Percentage (%)", "#9467bd"), use_container_width=True)
        with col_b:
            st.plotly_chart(create_yoy_chart(merged_df, "Superset SEO销售额", "Superset SEO Omzet (€)", "Omzet (€)", "#ff7f0e"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "AI Assistant 销售额", "AI Assistant Omzet (€)", "Omzet (€)", "#d62728"), use_container_width=True)

    # TAB 2: VERKEER
    with tab2:
        col_a, col_b = st.columns(2)
        with col_a:
            st.plotly_chart(create_yoy_chart(merged_df, "SEO流量", "Totaal SEO Verkeer", "Bezoekers", "#1f77b4"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "SEO Blog流量", "SEO Blog Verkeer", "Bezoekers", "#2ca02c"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "AI Assistant 流量", "AI Assistant Verkeer", "Bezoekers", "#9467bd"), use_container_width=True)
        with col_b:
            st.plotly_chart(create_yoy_chart(merged_df, "SEO 站内流量", "SEO Intern Verkeer", "Bezoekers", "#ff7f0e"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "网站总流量", "Totaal Website Verkeer", "Bezoekers", "#d62728"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "跳出率", "Bounce Rate (%)", "Percentage (%)", "#8c564b"), use_container_width=True)

    # TAB 3: SEO STATUS & BACKLINKS
    with tab3:
        col_a, col_b = st.columns(2)
        with col_a:
            st.plotly_chart(create_yoy_chart(merged_df, "收录", "Geïndexeerde Pagina's (收录)", "Aantal Pagina's", "#1f77b4"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "外链", "Totaal Backlinks (外链)", "Aantal Backlinks", "#2ca02c"), use_container_width=True)
        with col_b:
            st.plotly_chart(create_yoy_chart(merged_df, "Blog 收录", "Geïndexeerde Blogs (Blog 收录)", "Aantal Blogs", "#ff7f0e"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "外链域名广度", "Verwijzende Domeinen (外链域名广度)", "Aantal Domeinen", "#d62728"), use_container_width=True)

except Exception as e:
    st.error("Er is een fout opgetreden bij het inlezen van de Google Sheet.")
    st.write(f"Technisch detail: {e}")
