import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection

# -------------------- PAGE CONFIGURATION --------------------
st.set_page_config(
    page_title="Callie NL - Performance Dashboard",
    page_icon="📊",
    layout="wide"
)

# -------------------- AUTHENTICATION FUNCTION --------------------
def check_password():
    """
    Inlogsysteem op basis van st.session_state.
    Controleert of gebruikersnaam 'seo' en wachtwoord 'callie' juist zijn.
    """
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.title("🔒 Login Required")
        st.caption("Please enter your credentials to access the Callie NL Performance Dashboard.")

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("login_form"):
                username_input = st.text_input("Username")
                password_input = st.text_input("Password", type="password")
                submit_button = st.form_submit_button("Login")

                if submit_button:
                    if username_input == "seo" and password_input == "callie":
                        st.session_state["authenticated"] = True
                        st.success("Access granted!")
                        st.rerun()
                    else:
                        st.error("❌ Incorrect username or password")

        return False

    return True

# Stop execution if not authenticated
if not check_password():
    st.stop()

# -------------------- LOGOUT BUTTON IN SIDEBAR --------------------
if st.sidebar.button("🔒 Log out"):
    st.session_state["authenticated"] = False
    st.rerun()

# -------------------- DASHBOARD TITLE --------------------
st.title("📊 Callie NL — Performance Dashboard (Individual YoY Trends)")
st.caption("All metrics individually compared against last year with flexible period aggregation (Day / Week / Month / Quarter / Year).")

# -------------------- DATA FETCHING & TRANSFORMATION --------------------
SHEET_URL = "https://docs.google.com/spreadsheets/d/1GLAGMkVx5DMXylG0bbdvkzuqTd8IVfDANhcRrAX6LFU/edit?usp=sharing"

def clean_number(val, is_pct=False):
    """
    Parses US style formatted numbers into correct floats.
    Leaves empty/future values as np.nan so averages and totals are calculated correctly.
    """
    if pd.isna(val):
        return np.nan
    
    s_raw = str(val).strip()
    if not s_raw or s_raw.lower() in ['nan', 'none', '-', 'null', '']:
        return np.nan

    has_pct_symbol = '%' in s_raw
    s = s_raw.replace('$', '').replace('€', '').replace('%', '').strip()

    if not s:
        return np.nan

    s = s.replace(',', '')

    try:
        num = float(s)
        if is_pct:
            if not has_pct_symbol and 0 < abs(num) <= 1.0:
                num = num * 100
        return num
    except ValueError:
        return np.nan

@st.cache_data(ttl=60)
def load_and_transform_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    raw_df = conn.read(
        spreadsheet=SHEET_URL,
        skiprows=87,
        nrows=19,
        header=None
    )
    
    metrics_names = [str(m).strip() if pd.notna(m) else f"Metric_{i}" for i, m in enumerate(raw_df.iloc[:, 0].tolist())]
    data_matrix = raw_df.iloc[:, 1:]
    
    df_transposed = data_matrix.T
    df_transposed.columns = metrics_names
    
    df_transposed = df_transposed.rename(columns={df_transposed.columns[0]: "Datum_Raw"})
    df_transposed['Datum'] = pd.to_datetime(df_transposed['Datum_Raw'], errors='coerce')
    df_transposed = df_transposed.dropna(subset=['Datum'])
    
    numeric_cols = [str(c) for c in df_transposed.columns if str(c) not in ['Datum_Raw', 'Datum', '网站要事记']]
    for col in numeric_cols:
        is_pct_col = any(k in col for k in ['率', '占比', 'Rate', 'Share', 'Percentage', '%'])
        df_transposed[col] = df_transposed[col].apply(lambda v: clean_number(v, is_pct=is_pct_col))
        
    return df_transposed.sort_values('Datum'), numeric_cols

def create_yoy_chart(df_merged, col, title, y_label, freq_code, color_current="#1f77b4", color_ly="#aec7e8"):
    """
    Creates an individual YoY chart with custom hover formatting and frequency-matched x-axis format.
    """
    fig = go.Figure()

    is_percentage = "(%)" in y_label or "Percentage" in y_label or any(k in col for k in ['率', '占比', '%'])
    is_currency = "($)" in y_label or "Revenue" in title

    if is_currency:
        hover_template = "%{y:$,.2f}"
    elif is_percentage:
        hover_template = "%{y:.2f}%"
    else:
        hover_template = "%{y:,.0f}"

    # Current Year (今年) - filter out NaNs
    if col in df_merged.columns:
        curr_series = df_merged.dropna(subset=[col])
        fig.add_trace(go.Scatter(
            x=curr_series['Datum'],
            y=curr_series[col],
            mode='lines+markers',
            name='今年',
            line=dict(color=color_current, width=3),
            hovertemplate=hover_template
        ))
    
    # Last Year (去年)
    col_ly = f"{col}_LY"
    if col_ly in df_merged.columns:
        ly_series = df_merged.dropna(subset=[col_ly])
        fig.add_trace(go.Scatter(
            x=ly_series['Datum'],
            y=ly_series[col_ly],
            mode='lines+markers',
            name='去年',
            line=dict(color=color_ly, width=2, dash='dash'),
            hovertemplate=hover_template
        ))

    fig.update_layout(
        title=title,
        xaxis_title="Date / Period",
        yaxis_title=y_label,
        yaxis=dict(
            rangemode="tozero",
            ticksuffix="%" if is_percentage else ""
        ),
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

    if freq_code == "MS":
        fig.update_xaxes(dtick="M1", tickformat="%b %Y", hoverformat="%B %Y")
    elif freq_code == "QS":
        fig.update_xaxes(dtick="M3", tickformat="Q%q %Y", hoverformat="Q%q %Y")
    elif freq_code == "YS":
        fig.update_xaxes(dtick="M12", tickformat="%Y", hoverformat="%Y")
    else:
        fig.update_xaxes(hoverformat="%d-%m-%Y")
    
    return fig

try:
    df, numeric_cols = load_and_transform_data()

    # -------------------- SIDEBAR CONTROLS --------------------
    st.sidebar.header("📅 Date & Granularity Selector")
    
    granularity = st.sidebar.selectbox(
        "Frequency / Grouping (按时间聚合):",
        ["Daily (日)", "Weekly (周)", "Monthly (月)", "Quarterly (季)", "Yearly (年)"]
    )

    # Vind de meest recente datum met echte data
    df_valid_dates = df.dropna(how='all', subset=numeric_cols)
    max_data_date = df_valid_dates['Datum'].max().date() if not df_valid_dates.empty else df['Datum'].max().date()
    min_date = df['Datum'].min().date()

    default_end = max_data_date
    default_start = max(default_end - pd.Timedelta(days=30), min_date)

    col_s1, col_s2 = st.sidebar.columns(2)
    with col_s1:
        start_date = st.date_input(
            "Start Date:",
            value=default_start,
            min_value=min_date,
            max_value=max_data_date
        )
    with col_s2:
        end_date = st.date_input(
            "End Date:",
            value=default_end,
            min_value=min_date,
            max_value=max_data_date
        )

    if start_date > end_date:
        st.sidebar.error("⚠️ Start Date cannot be after End Date.")
        start_date, end_date = end_date, start_date

    # -------------------- STAP 1: DAGELIJKSE YOY MATCHING (APPLES TO APPLES) --------------------
    df_daily = df.copy()
    YOY_OFFSET = pd.Timedelta(days=364)
    df_daily['Datum_Vorig_Jaar'] = df_daily['Datum'] - YOY_OFFSET

    cols_to_merge = [c for c in numeric_cols if c in df_daily.columns]
    daily_merged = pd.merge(
        df_daily,
        df_daily[['Datum'] + cols_to_merge],
        left_on='Datum_Vorig_Jaar',
        right_on='Datum',
        how='left',
        suffixes=('', '_LY')
    )

    freq_map = {
        "Daily (日)": "D",
        "Weekly (周)": "W-MON",
        "Monthly (月)": "MS",
        "Quarterly (季)": "QS",
        "Yearly (年)": "YS"
    }
    freq_code = freq_map[granularity]

    filter_start = start_date
    if freq_code == "MS":
        filter_start = start_date.replace(day=1)
    elif freq_code == "QS":
        month = ((start_date.month - 1) // 3) * 3 + 1
        filter_start = start_date.replace(month=month, day=1)
    elif freq_code == "YS":
        filter_start = start_date.replace(month=1, day=1)
    elif freq_code == "W-MON":
        filter_start = start_date - pd.Timedelta(days=start_date.weekday())

    filtered_daily = daily_merged[(daily_merged['Datum'].dt.date >= filter_start) & (daily_merged['Datum'].dt.date <= end_date)].copy()

    # -------------------- STAP 2: AGGREGATIE NA DE MATCHING --------------------
    all_metrics_cols = numeric_cols + [f"{c}_LY" for c in numeric_cols if f"{c}_LY" in daily_merged.columns]

    agg_rules = {}
    for col in all_metrics_cols:
        col_str = str(col)
        if any(k in col_str for k in ['率', '占比', 'Share', 'Rate', '收录', '外链', '%']):
            agg_rules[col] = 'mean'
        else:
            agg_rules[col] = lambda s: s.sum(min_count=1)

    if freq_code != "D":
        merged_df = filtered_daily.set_index('Datum').groupby(pd.Grouper(freq=freq_code)).agg(agg_rules).reset_index()
    else:
        merged_df = filtered_daily.copy()

    # -------------------- KPI SUMMARY WITH % COMPARISONS --------------------
    start_str = start_date.strftime('%d-%m-%Y')
    end_str = end_date.strftime('%d-%m-%Y')
    st.subheader(f"📌 Total Period Summary ({start_str} to {end_str}) — 今年 vs 去年 [{granularity}]")

    curr_ga4_seo = filtered_daily['GA4 SEO销售额'].sum(skipna=True) if 'GA4 SEO销售额' in filtered_daily.columns else 0
    ly_ga4_seo = filtered_daily['GA4 SEO销售额_LY'].sum(skipna=True) if 'GA4 SEO销售额_LY' in filtered_daily.columns else 0

    curr_superset_seo = filtered_daily['Superset SEO销售额'].sum(skipna=True) if 'Superset SEO销售额' in filtered_daily.columns else 0
    ly_superset_seo = filtered_daily['Superset SEO销售额_LY'].sum(skipna=True) if 'Superset SEO销售额_LY' in filtered_daily.columns else 0

    curr_total_rev = filtered_daily['GA4 网站总销售额'].sum(skipna=True) if 'GA4 网站总销售额' in filtered_daily.columns else 0
    ly_total_rev = filtered_daily['GA4 网站总销售额_LY'].sum(skipna=True) if 'GA4 网站总销售额_LY' in filtered_daily.columns else 0

    curr_superset_share = (curr_superset_seo / curr_total_rev * 100) if curr_total_rev > 0 else 0
    ly_superset_share = (ly_superset_seo / ly_total_rev * 100) if ly_total_rev > 0 else 0

    curr_seo_traffic = filtered_daily['SEO流量'].sum(skipna=True) if 'SEO流量' in filtered_daily.columns else 0
    ly_seo_traffic = filtered_daily['SEO流量_LY'].sum(skipna=True) if 'SEO流量_LY' in filtered_daily.columns else 0

    curr_blog_traffic = filtered_daily['SEO Blog流量'].sum(skipna=True) if 'SEO Blog流量' in filtered_daily.columns else 0
    ly_blog_traffic = filtered_daily['SEO Blog流量_LY'].sum(skipna=True) if 'SEO Blog流量_LY' in filtered_daily.columns else 0

    curr_ai_traffic = filtered_daily['AI Assistant 流量'].sum(skipna=True) if 'AI Assistant 流量' in filtered_daily.columns else 0
    ly_ai_traffic = filtered_daily['AI Assistant 流量_LY'].sum(skipna=True) if 'AI Assistant 流量_LY' in filtered_daily.columns else 0

    curr_ai_rev = filtered_daily['AI Assistant 销售额'].sum(skipna=True) if 'AI Assistant 销售额' in filtered_daily.columns else 0
    ly_ai_rev = filtered_daily['AI Assistant 销售额_LY'].sum(skipna=True) if 'AI Assistant 销售额_LY' in filtered_daily.columns else 0

    def format_kpi_delta(diff, ly_val, is_currency=False):
        pct_change = (diff / ly_val * 100) if ly_val > 0 else 0.0
        if is_currency:
            return f"{diff:+,.2f} ({pct_change:+.2f}%) vs 去年"
        else:
            return f"{int(diff):+,} ({pct_change:+.2f}%) vs 去年"

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        diff_seo_rev = curr_ga4_seo - ly_ga4_seo
        st.metric(
            label="GA4 SEO Revenue (GA4 SEO销售额)",
            value=f"$ {curr_ga4_seo:,.2f}",
            delta=format_kpi_delta(diff_seo_rev, ly_ga4_seo, is_currency=True)
        )
        st.caption(f"去年 (MTD): $ {ly_ga4_seo:,.2f}")

    with col2:
        diff_superset_seo = curr_superset_seo - ly_superset_seo
        st.metric(
            label="Superset SEO Revenue (Superset SEO销售额)",
            value=f"$ {curr_superset_seo:,.2f}",
            delta=format_kpi_delta(diff_superset_seo, ly_superset_seo, is_currency=True)
        )
        st.caption(f"去年 (MTD): $ {ly_superset_seo:,.2f}")

    with col3:
        diff_total_rev = curr_total_rev - ly_total_rev
        st.metric(
            label="Total Website Revenue (GA4 网站总销售额)",
            value=f"$ {curr_total_rev:,.2f}",
            delta=format_kpi_delta(diff_total_rev, ly_total_rev, is_currency=True)
        )
        st.caption(f"去年: $ {ly_total_rev:,.2f} | Share: {curr_superset_share:.2f}% (去年: {ly_superset_share:.2f}%)")

    with col4:
        diff_seo_tr = curr_seo_traffic - ly_seo_traffic
        st.metric(
            label="Total SEO Traffic (SEO流量)",
            value=f"{int(curr_seo_traffic):,}",
            delta=format_kpi_delta(diff_seo_tr, ly_seo_traffic, is_currency=False)
        )
        st.caption(f"去年: {int(ly_seo_traffic):,} | Blog: {int(curr_blog_traffic):,} (去年: {int(ly_blog_traffic):,})")

    with col5:
        diff_ai_tr = curr_ai_traffic - ly_ai_traffic
        st.metric(
            label="AI Assistant Traffic (AI Assistant 流量)",
            value=f"{int(curr_ai_traffic):,}",
            delta=format_kpi_delta(diff_ai_tr, ly_ai_traffic, is_currency=False)
        )
        st.caption(f"去年: {int(ly_ai_traffic):,} | AI Rev: $ {curr_ai_rev:,.2f} (去年: $ {ly_ai_rev:,.2f})")

    st.markdown("---")

    # -------------------- INDIVIDUAL CHARTS BY TAB --------------------
    st.subheader(f"📈 Performance Trends [{granularity}]")

    tab1, tab2, tab3 = st.tabs(["💰 Revenue Metrics", "📈 Traffic Metrics", "🔍 SEO & Backlink Status"])

    # TAB 1: REVENUE METRICS
    with tab1:
        col_a, col_b = st.columns(2)
        with col_a:
            st.plotly_chart(create_yoy_chart(merged_df, "GA4 SEO销售额", "GA4 SEO Revenue (GA4 SEO销售额)", "Revenue ($)", freq_code, "#1f77b4"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "GA4 网站总销售额", "Total Website Revenue (GA4 网站总销售额)", "Revenue ($)", freq_code, "#2ca02c"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "Superset 总销售额占比情况", "Superset Revenue Share (Superset 总销售额占比情况)", "Percentage (%)", freq_code, "#9467bd"), use_container_width=True)
        with col_b:
            st.plotly_chart(create_yoy_chart(merged_df, "Superset SEO销售额", "Superset SEO Revenue (Superset SEO销售额)", "Revenue ($)", freq_code, "#ff7f0e"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "AI Assistant 销售额", "AI Assistant Revenue (AI Assistant 销售额)", "Revenue ($)", freq_code, "#d62728"), use_container_width=True)

    # TAB 2: TRAFFIC METRICS
    with tab2:
        col_a, col_b = st.columns(2)
        with col_a:
            st.plotly_chart(create_yoy_chart(merged_df, "SEO流量", "Total SEO Traffic (SEO流量)", "Visitors", freq_code, "#1f77b4"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "SEO Blog流量", "SEO Blog Traffic (SEO Blog流量)", "Visitors", freq_code, "#2ca02c"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "AI Assistant 流量", "AI Assistant Traffic (AI Assistant 流量)", "Visitors", freq_code, "#9467bd"), use_container_width=True)
        with col_b:
            st.plotly_chart(create_yoy_chart(merged_df, "SEO 站内流量", "Internal SEO Traffic (SEO 站内流量)", "Visitors", freq_code, "#ff7f0e"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "网站总流量", "Total Website Traffic (网站总流量)", "Visitors", freq_code, "#d62728"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "跳出率", "Bounce Rate (跳出率)", "Percentage (%)", freq_code, "#8c564b"), use_container_width=True)

    # TAB 3: SEO STATUS & BACKLINKS
    with tab3:
        col_a, col_b = st.columns(2)
        with col_a:
            st.plotly_chart(create_yoy_chart(merged_df, "收录", "Indexed Pages (收录)", "Pages Count", freq_code, "#1f77b4"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "外链", "Total Backlinks (外链)", "Backlinks Count", freq_code, "#2ca02c"), use_container_width=True)
        with col_b:
            st.plotly_chart(create_yoy_chart(merged_df, "Blog 收录", "Indexed Blog Pages (Blog 收录)", "Blogs Count", freq_code, "#ff7f0e"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "外链域名广度", "Referring Domains / Breadth (外链域名广度)", "Domains Count", freq_code, "#d62728"), use_container_width=True)

except Exception as e:
    st.error("An error occurred while reading the Google Sheet.")
    st.write(f"Technical details: {e}")
