import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection

# -------------------- PAGE CONFIGURATION --------------------
st.set_page_config(
    page_title="Callie NL - Performance Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Callie NL — Performance Dashboard (Individual YoY Trends)")
st.caption("All metrics individually compared against the exact same day last year (364 days offset).")

# -------------------- DATA FETCHING & TRANSFORMATION --------------------
SHEET_URL = "https://docs.google.com/spreadsheets/d/1GLAGMkVx5DMXylG0bbdvkzuqTd8IVfDANhcRrAX6LFU/edit?usp=sharing"

def clean_number(val):
    """
    Parses US style formatted numbers like '$8,783.07' or '8,783' into correct floats.
    """
    if pd.isna(val):
        return 0.0
    
    # Clean currency and percentage signs
    s = str(val).replace('$', '').replace('€', '').replace('%', '').strip()
    
    if not s or s.lower() == 'nan':
        return 0.0

    # US Format: Commas are thousands separators -> remove them entirely
    s = s.replace(',', '')

    try:
        return float(s)
    except ValueError:
        return 0.0

@st.cache_data(ttl=60)
def load_and_transform_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Read row range for Callie NL (Row 88 to 106)
    raw_df = conn.read(
        spreadsheet=SHEET_URL,
        skiprows=87,
        nrows=19,
        header=None
    )
    
    metrics_names = raw_df.iloc[:, 0].tolist()
    data_matrix = raw_df.iloc[:, 1:]
    
    # Transpose matrix: Dates become rows, KPIs become columns
    df_transposed = data_matrix.T
    df_transposed.columns = metrics_names
    
    # Process date column
    df_transposed = df_transposed.rename(columns={df_transposed.columns[0]: "Datum_Raw"})
    df_transposed['Datum'] = pd.to_datetime(df_transposed['Datum_Raw'], errors='coerce')
    df_transposed = df_transposed.dropna(subset=['Datum'])
    
    # Clean numeric columns
    numeric_cols = [c for c in df_transposed.columns if c not in ['Datum_Raw', 'Datum', '网站要事记']]
    for col in numeric_cols:
        df_transposed[col] = df_transposed[col].apply(clean_number)
        
    return df_transposed.sort_values('Datum'), numeric_cols

def create_yoy_chart(df_merged, col, title, y_label, color_current="#1f77b4", color_ly="#aec7e8"):
    """
    Creates an individual YoY chart with y-axis baseline set to 0.
    """
    fig = go.Figure()

    # Bepaal de hover-opmaak op basis van het type metriek
    if "($)" in y_label or "Revenue" in title:
        hover_template = "%{y:$,.2f}"
    elif "(%)" in y_label or "Percentage" in y_label:
        hover_template = "%{y:.2f}%"
    else:
        hover_template = "%{y:,.0f}"

    # Current Year (今年)
    if col in df_merged.columns:
        fig.add_trace(go.Scatter(
            x=df_merged['Datum'],
            y=df_merged[col],
            mode='lines+markers',
            name='今年',
            line=dict(color=color_current, width=3),
            hovertemplate=hover_template
        ))
    
    # Last Year (去年 - 364 days offset)
    col_ly = f"{col}_LY"
    if col_ly in df_merged.columns:
        fig.add_trace(go.Scatter(
            x=df_merged['Datum'],
            y=df_merged[col_ly],
            mode='lines+markers',
            name='去年',
            line=dict(color=color_ly, width=2, dash='dash'),
            hovertemplate=hover_template
        ))

    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title=y_label,
        yaxis=dict(rangemode="tozero"),  # Dwingt de Y-as om bij 0 te beginnen!
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="white",
            font_size=13
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=20, r=20, t=50, b=20),
        height=400
    )
    # Formatteer de datum in het hovervenster als DD-MM-YYYY
    fig.update_xaxes(hoverformat="%d-%m-%Y")
    
    return fig

try:
    df, numeric_cols = load_and_transform_data()

    # -------------------- DEFAULT DATE RANGE SETTINGS --------------------
    # Today - 2 days (end date) & Today - 32 days (start date)
    today = pd.Timestamp.now().normalize()
    min_date = df['Datum'].min().date()
    max_date = df['Datum'].max().date()

    default_end = min(today.date() - pd.Timedelta(days=2), max_date)
    if default_end < min_date:
        default_end = max_date
        
    default_start = max(default_end - pd.Timedelta(days=30), min_date)

    st.sidebar.header("📅 Date Range Selector")
    start_date, end_date = st.sidebar.date_input(
        "Select Date Range:",
        value=[default_start, default_end],
        min_value=min_date,
        max_value=max_date
    )

    # Filter current period
    current_df = df[(df['Datum'].dt.date >= start_date) & (df['Datum'].dt.date <= end_date)].copy()

    # -------------------- YOY MATCHING FOR ALL METRICS --------------------
    # 52 weeks * 7 days = 364 days (aligns exact weekday last year)
    YOY_OFFSET = pd.Timedelta(days=364)
    current_df['Datum_Vorig_Jaar'] = current_df['Datum'] - YOY_OFFSET
    
    # Merge Last Year data for ALL numeric columns
    cols_to_merge = [c for c in numeric_cols if c in df.columns]
    merged_df = pd.merge(
        current_df,
        df[['Datum'] + cols_to_merge],
        left_on='Datum_Vorig_Jaar',
        right_on='Datum',
        how='left',
        suffixes=('', '_LY')
    )

    # -------------------- KPI SUMMARY (LATEST SELECTED DATE) --------------------
    latest = current_df.iloc[-1] if not current_df.empty else df.iloc[-1]
    
    st.subheader(f"📌 Status Overview ({latest['Datum'].strftime('%d-%m-%Y')})")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("GA4 SEO Revenue (GA4 SEO销售额)", f"$ {latest.get('GA4 SEO销售额', 0):,.2f}")
        st.caption(f"Superset SEO Revenue (Superset SEO销售额): $ {latest.get('Superset SEO销售额', 0):,.2f}")
    with col2:
        st.metric("Total Website Revenue (GA4 网站总销售额)", f"$ {latest.get('GA4 网站总销售额', 0):,.2f}")
        st.caption(f"Superset Share (Superset 总销售额占比情况): {latest.get('Superset 总销售额占比情况', 0)}%")
    with col3:
        st.metric("Total SEO Traffic (SEO流量)", f"{int(latest.get('SEO流量', 0)):,}")
        st.caption(f"Blog Traffic (SEO Blog流量): {int(latest.get('SEO Blog流量', 0)):,}")
    with col4:
        st.metric("AI Assistant Traffic (AI Assistant 流量)", f"{int(latest.get('AI Assistant 流量', 0)):,}")
        st.caption(f"AI Revenue (AI Assistant 销售额): $ {latest.get('AI Assistant 销售额', 0):,.2f}")

    st.markdown("---")

    # -------------------- INDIVIDUAL CHARTS BY TAB --------------------
    st.subheader("📈 Individual YoY Performance Charts")

    tab1, tab2, tab3 = st.tabs(["💰 Revenue Metrics", "📈 Traffic Metrics", "🔍 SEO & Backlink Status"])

    # TAB 1: REVENUE METRICS
    with tab1:
        col_a, col_b = st.columns(2)
        with col_a:
            st.plotly_chart(create_yoy_chart(merged_df, "GA4 SEO销售额", "GA4 SEO Revenue (GA4 SEO销售额)", "Revenue ($)", "#1f77b4"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "GA4 网站总销售额", "Total Website Revenue (GA4 网站总销售额)", "Revenue ($)", "#2ca02c"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "Superset 总销售额占比情况", "Superset Revenue Share (Superset 总销售额占比情况)", "Percentage (%)", "#9467bd"), use_container_width=True)
        with col_b:
            st.plotly_chart(create_yoy_chart(merged_df, "Superset SEO销售额", "Superset SEO Revenue (Superset SEO销售额)", "Revenue ($)", "#ff7f0e"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "AI Assistant 销售额", "AI Assistant Revenue (AI Assistant 销售额)", "Revenue ($)", "#d62728"), use_container_width=True)

    # TAB 2: TRAFFIC METRICS
    with tab2:
        col_a, col_b = st.columns(2)
        with col_a:
            st.plotly_chart(create_yoy_chart(merged_df, "SEO流量", "Total SEO Traffic (SEO流量)", "Visitors", "#1f77b4"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "SEO Blog流量", "SEO Blog Traffic (SEO Blog流量)", "Visitors", "#2ca02c"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "AI Assistant 流量", "AI Assistant Traffic (AI Assistant 流量)", "Visitors", "#9467bd"), use_container_width=True)
        with col_b:
            st.plotly_chart(create_yoy_chart(merged_df, "SEO 站内流量", "Internal SEO Traffic (SEO 站内流量)", "Visitors", "#ff7f0e"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "网站总流量", "Total Website Traffic (网站总流量)", "Visitors", "#d62728"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "跳出率", "Bounce Rate (跳出率)", "Percentage (%)", "#8c564b"), use_container_width=True)

    # TAB 3: SEO STATUS & BACKLINKS
    with tab3:
        col_a, col_b = st.columns(2)
        with col_a:
            st.plotly_chart(create_yoy_chart(merged_df, "收录", "Indexed Pages (收录)", "Pages Count", "#1f77b4"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "外链", "Total Backlinks (外链)", "Backlinks Count", "#2ca02c"), use_container_width=True)
        with col_b:
            st.plotly_chart(create_yoy_chart(merged_df, "Blog 收录", "Indexed Blog Pages (Blog 收录)", "Blogs Count", "#ff7f0e"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "外链域名广度", "Referring Domains / Breadth (外链域名广度)", "Domains Count", "#d62728"), use_container_width=True)

except Exception as e:
    st.error("An error occurred while reading the Google Sheet.")
    st.write(f"Technical details: {e}")
