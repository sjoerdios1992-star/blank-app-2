import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection

# -------------------- PAGINA INSTELLINGEN --------------------
st.set_page_config(
    page_title="Callie NL - Performance Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Callie NL — Performance Dashboard & YoY Trends")
st.caption("Data rechtstreeks uit Google Sheets met Year-over-Year (364 dagen) dagelijkse vergelijking.")

# -------------------- DATA OPHALEN EN OMZETTEN --------------------
SHEET_URL = "https://docs.google.com/spreadsheets/d/1GLAGMkVx5DMXylG0bbdvkzuqTd8IVfDANhcRrAX6LFU/edit?usp=sharing"

def clean_number(val):
    """
    Converteert Nederlandse/Europese getalnotaties (met . voor duizendtallen en , voor decimalen)
    naar een float die Python kan begrijpen.
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
    
    # Kantel de tabel om: Datums worden rijen, KPI's worden kolommen
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
        
    return df_transposed.sort_values('Datum')

try:
    df = load_and_transform_data()

    # -------------------- SIDEBAR FILTERS --------------------
    st.sidebar.header("📅 Periode Selectie")
    min_date = df['Datum'].min().date()
    max_date = df['Datum'].max().date()

    start_date, end_date = st.sidebar.date_input(
        "Selecteer huidige periode:",
        value=[min_date, max_date],
        min_value=min_date,
        max_value=max_date
    )

    # Filter huidige periode
    current_df = df[(df['Datum'].dt.date >= start_date) & (df['Datum'].dt.date <= end_date)].copy()

    # -------------------- YOY MATCHING (364 DAGEN VERSCHUIVING) --------------------
    # 52 weken * 7 dagen = 364 dagen (zorgt dat weekdagen exact gelijk lopen, bijv. Maandag vs Maandag)
    YOY_OFFSET = pd.Timedelta(days=364)
    
    current_df['Datum_Vorig_Jaar'] = current_df['Datum'] - YOY_OFFSET
    
    # Koppel de data van vorig jaar aan de huidige datums
    merged_df = pd.merge(
        current_df,
        df[['Datum', 'GA4 SEO销售额', 'GA4 网站总销售额', 'SEO流量', '网站总流量']],
        left_on='Datum_Vorig_Jaar',
        right_on='Datum',
        how='left',
        suffixes=('', '_LY')
    )

    # -------------------- KPI SAMENVATTING (MEEST RECENTE DATUM) --------------------
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

    # -------------------- GRAFIEKEN OVER TIJD (YOY VERGELIJKING) --------------------
    st.subheader("📈 YoY Vergelijking per Dag (Dit Jaar vs Vorig Jaar)")

    tab1, tab2, tab3 = st.tabs(["💰 Omzet YoY", "📈 Verkeer YoY", "🔍 SEO Status"])

    with tab1:
        # Omzet Vergelijking Grafiek
        fig_sales_yoy = go.Figure()
        
        # Dit Jaar
        fig_sales_yoy.add_trace(go.Scatter(
            x=merged_df['Datum'],
            y=merged_df['GA4 SEO销售额'],
            mode='lines+markers',
            name='SEO Omzet Dit Jaar',
            line=dict(color='#1f77b4', width=3)
        ))
        
        # Vorig Jaar (Gekoppeld op dezelfde dag)
        fig_sales_yoy.add_trace(go.Scatter(
            x=merged_df['Datum'],
            y=merged_df['GA4 SEO销售额_LY'],
            mode='lines+markers',
            name='SEO Omzet Vorig Jaar (364d geleden)',
            line=dict(color='#aec7e8', width=2, dash='dash')
        ))

        fig_sales_yoy.update_layout(
            title="GA4 SEO Omzet: Dit Jaar vs Vorig Jaar (Per Dag)",
            xaxis_title="Datum (Huidige Periode)",
            yaxis_title="Omzet (€)",
            hovermode="x unified"
        )
        st.plotly_chart(fig_sales_yoy, use_container_width=True)

    with tab2:
        # Verkeersvergelijking Grafiek
        fig_traffic_yoy = go.Figure()
        
        # Dit Jaar
        fig_traffic_yoy.add_trace(go.Scatter(
            x=merged_df['Datum'],
            y=merged_df['SEO流量'],
            mode='lines+markers',
            name='SEO Verkeer Dit Jaar',
            line=dict(color='#2ca02c', width=3)
        ))
        
        # Vorig Jaar
        fig_traffic_yoy.add_trace(go.Scatter(
            x=merged_df['Datum'],
            y=merged_df['SEO流量_LY'],
            mode='lines+markers',
            name='SEO Verkeer Vorig Jaar (364d geleden)',
            line=dict(color='#98df8a', width=2, dash='dash')
        ))

        fig_traffic_yoy.update_layout(
            title="SEO Verkeer: Dit Jaar vs Vorig Jaar (Per Dag)",
            xaxis_title="Datum (Huidige Periode)",
            yaxis_title="Aantal Bezoekers",
            hovermode="x unified"
        )
        st.plotly_chart(fig_traffic_yoy, use_container_width=True)

    with tab3:
        col_a, col_b = st.columns(2)
        with col_a:
            fig_index = px.line(
                current_df,
                x="Datum",
                y=["收录", "Blog 收录"],
                title="Geïndexeerde Pagina's (收录)",
                markers=True
            )
            st.plotly_chart(fig_index, use_container_width=True)
            
        with col_b:
            fig_backlinks = px.line(
                current_df,
                x="Datum",
                y=["外链", "外链域名广度"],
                title="Backlinks & Domain Breadth (外链)",
                markers=True
            )
            st.plotly_chart(fig_backlinks, use_container_width=True)

except Exception as e:
    st.error("Er is een fout opgetreden bij het inlezen van de Google Sheet.")
    st.write(f"Technisch detail: {e}")
