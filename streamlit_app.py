import streamlit as st
import pandas as pd
import numpy as np
import datetime
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection

# -------------------- PAGE CONFIGURATION --------------------
st.set_page_config(
    page_title="Callie NL - Performance Dashboard",
    page_icon="📊",
    layout="wide"
)

# -------------------- CUSTOM CSS STYLING --------------------
st.markdown("""
<style>
    [data-testid="stMetric"] {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 16px 20px;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        min-height: 140px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    [data-testid="stMetricLabel"] p {
        font-size: 0.95rem !important;
        font-weight: 600;
        color: #343a40;
        white-space: normal !important;
        overflow-wrap: break-word !important;
        line-height: 1.35 !important;
    }
    [data-testid="stMetricValue"] div {
        font-size: 1.65rem !important;
        font-weight: 700;
        white-space: nowrap !important;
    }
    [data-testid="stMetricDelta"] {
        white-space: normal !important;
        overflow-wrap: break-word !important;
        font-size: 0.85rem !important;
    }
    .kpi-header {
        margin-top: 5px;
        margin-bottom: 18px;
        font-weight: 700;
        color: #212529;
    }
    .period-box {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 15px;
        border: 1px solid #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)

# -------------------- AUTHENTICATION FUNCTION --------------------
def check_password():
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

if not check_password():
    st.stop()

# -------------------- LOGOUT BUTTON IN SIDEBAR --------------------
if st.sidebar.button("🔒 Log out"):
    st.session_state["authenticated"] = False
    st.rerun()

# -------------------- DASHBOARD TITLE --------------------
st.title("📊 Callie NL — Performance Dashboard")
st.caption("Performance insights & YoY trends with granular date control (Day / Week / Month / Quarter / Year).")

# -------------------- DATA URLS --------------------
SHEET_URL_MAIN = "https://docs.google.com/spreadsheets/d/1GLAGMkVx5DMXylG0bbdvkzuqTd8IVfDANhcRrAX6LFU/edit?usp=sharing"
SHEET_URL_GSC = "https://docs.google.com/spreadsheets/d/1Qna6ZiJ3tlZzz9U2yL-qTwon3MFGOwRKFXmZGUIcXZ4/edit?gid=0#gid=0"

# -------------------- HELPER FUNCTIONS --------------------
def clean_number(val, is_pct=False):
    if pd.isna(val):
        return np.nan
    s_raw = str(val).strip()
    if not s_raw or s_raw.lower() in ['nan', 'none', '-', 'null', '']:
        return np.nan

    has_pct_symbol = '%' in s_raw
    s = s_raw.replace('$', '').replace('€', '').replace('%', '').strip().replace(',', '')
    if not s:
        return np.nan

    try:
        num = float(s)
        if is_pct:
            if not has_pct_symbol and 0 < abs(num) <= 1.0:
                num = num * 100
        return num
    except ValueError:
        return np.nan

def parse_single_date(val):
    if pd.isna(val):
        return pd.NaT
    if isinstance(val, (pd.Timestamp, datetime.datetime, datetime.date)):
        return pd.to_datetime(val)
    
    s = str(val).strip()
    if not s or s.lower() in ['nan', 'nat', 'none', '-', '']:
        return pd.NaT

    try:
        parts = s.replace('-', '/').split('/')
        if len(parts) == 3 and len(parts[0]) == 4:
            return pd.Timestamp(year=int(parts[0]), month=int(parts[1]), day=int(parts[2]))
    except Exception:
        pass

    try:
        return pd.to_datetime(s, errors='coerce')
    except Exception:
        return pd.NaT

def format_kpi_delta(diff, ly_val, is_currency=False, is_pct=False, is_rank=False):
    if is_pct:
        return f"{diff:+.2f}% pt vs 去年"
    
    pct_change = (diff / ly_val * 100) if (ly_val is not None and ly_val != 0) else 0.0
    if is_currency:
        return f"{diff:+,.2f} ({pct_change:+.2f}%) vs 去年"
    elif is_rank:
        return f"{diff:+.1f} pts vs 去年"
    else:
        return f"{int(diff):+,} ({pct_change:+.2f}%) vs 去年"

# -------------------- LOAD SHEET 1 (MAIN DASHBOARD) --------------------
@st.cache_data(ttl=60)
def load_and_transform_main_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    raw_df = conn.read(spreadsheet=SHEET_URL_MAIN, skiprows=87, nrows=19, header=None)
    
    if raw_df is None or raw_df.empty:
        return pd.DataFrame(), []

    date_row_idx = 0
    for idx in range(len(raw_df)):
        sample_row = raw_df.iloc[idx, 1:].dropna().head(10)
        parsed_test = [parse_single_date(x) for x in sample_row]
        valid_count = sum(1 for d in parsed_test if pd.notna(d) and d.year >= 2020)
        if valid_count >= 3:
            date_row_idx = idx
            break

    metrics_names = [str(m).strip() if pd.notna(m) else f"Metric_{i}" for i, m in enumerate(raw_df.iloc[:, 0].tolist())]
    data_matrix = raw_df.iloc[:, 1:]
    
    df_transposed = data_matrix.T.reset_index(drop=True)
    df_transposed.columns = metrics_names
    
    datum_col = df_transposed.columns[date_row_idx]
    df_transposed['Datum'] = df_transposed[datum_col].apply(parse_single_date)
    df_transposed = df_transposed.dropna(subset=['Datum'])
    df_transposed = df_transposed[df_transposed['Datum'].dt.year >= 2020]
    
    numeric_cols = [str(c) for c in df_transposed.columns if str(c) not in [datum_col, 'Datum', 'Datum_Raw', '网站要事记']]
    for col in numeric_cols:
        is_pct_col = any(k in col for k in ['率', '占比', 'Rate', 'Share', 'Percentage', '%'])
        df_transposed[col] = df_transposed[col].apply(lambda v: clean_number(v, is_pct=is_pct_col))
        
    return df_transposed.sort_values('Datum'), numeric_cols

# -------------------- LOAD SHEET 2 (GSC WEEKLY DATA) --------------------
@st.cache_data(ttl=60)
def load_gsc_weekly_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        raw_gsc = conn.read(spreadsheet=SHEET_URL_GSC)
        if raw_gsc is None or raw_gsc.empty:
            return pd.DataFrame(), []

        df_gsc = raw_gsc.copy()
        date_col_name = None
        for col in df_gsc.columns:
            if any(k in str(col).lower() for k in ['date', 'datum', 'week', '日期', '时间']):
                date_col_name = col
                break
        
        if date_col_name is None:
            for col in df_gsc.columns:
                parsed_sample = df_gsc[col].dropna().head(5).apply(parse_single_date)
                if parsed_sample.notna().sum() >= 3:
                    date_col_name = col
                    break

        if date_col_name:
            df_gsc['Datum'] = df_gsc[date_col_name].apply(parse_single_date)
            df_gsc = df_gsc.dropna(subset=['Datum']).sort_values('Datum')
        else:
            df_gsc['Datum'] = pd.date_range(end=pd.Timestamp.now(), periods=len(df_gsc), freq='D')

        gsc_numeric_cols = []
        for col in df_gsc.columns:
            if col not in ['Datum', date_col_name]:
                col_name_str = str(col).strip()
                is_pct = any(k in col_name_str.lower() for k in ['%', 'ctr', 'rate', '率', '占比'])
                converted = df_gsc[col].apply(lambda v: clean_number(v, is_pct=is_pct))
                if converted.notna().sum() > 0:
                    df_gsc[col] = converted
                    gsc_numeric_cols.append(col)

        return df_gsc.sort_values('Datum'), gsc_numeric_cols
    except Exception:
        return pd.DataFrame(), []

def create_yoy_chart(df_merged, col, title, y_label, freq_code, color_current="#1f77b4", color_ly="#aec7e8"):
    fig = go.Figure()
    is_percentage = "(%)" in y_label or "Percentage" in y_label or "Share" in y_label or any(k in col for k in ['率', '占比', '%'])
    is_rank = "排名" in col or "Position" in col or "Rank" in col
    is_currency = ("($)" in y_label or "Revenue" in title) and not is_percentage

    if is_percentage:
        hover_template = "%{y:.2f}%"
    elif is_currency:
        hover_template = "%{y:$,.2f}"
    elif is_rank:
        hover_template = "%{y:.1f}"
    else:
        hover_template = "%{y:,.0f}"

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
            rangemode="tozero" if not is_rank else "normal",
            autorange=True if not is_rank else "reversed",
            ticksuffix="%" if is_percentage else ""
        ),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="white", font_size=13),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=50, b=20),
        height=380
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
    df, numeric_cols = load_and_transform_main_data()
    df_gsc, gsc_numeric_cols = load_gsc_weekly_data()

    if df.empty:
        st.error("No valid date rows found in the main sheet.")
        st.stop()

    # -------------------- SIDEBAR CONTROLS --------------------
    st.sidebar.header("📅 Date & Granularity Selector")
    
    granularity = st.sidebar.selectbox(
        "Frequency / Grouping (按时间聚合):",
        ["Daily (日)", "Weekly (周)", "Monthly (月)", "Quarterly (季)", "Yearly (年)"]
    )

    df_valid_dates = df.dropna(how='all', subset=numeric_cols)
    max_data_date = df_valid_dates['Datum'].max().date() if not df_valid_dates.empty else df['Datum'].max().date()
    min_date = df['Datum'].min().date()

    # Standaard datumselectie: Vandaag - 2 dagen (eergisteren) & 30 dagen terug
    today_date = pd.Timestamp.now().date()
    target_end = today_date - pd.Timedelta(days=2)
    default_end = min(target_end, max_data_date)
    if default_end < min_date:
        default_end = max_data_date

    default_start = max(default_end - pd.Timedelta(days=30), min_date)

    col_s1, col_s2 = st.sidebar.columns(2)
    with col_s1:
        start_date = st.date_input("Start Date:", value=default_start, min_value=min_date, max_value=max_data_date)
    with col_s2:
        end_date = st.date_input("End Date:", value=default_end, min_value=min_date, max_value=max_data_date)

    if start_date > end_date:
        st.sidebar.error("⚠️ Start Date cannot be after End Date.")
        start_date, end_date = end_date, start_date

    # -------------------- YOY MATCHING MAIN SHEET --------------------
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

    all_metrics_cols = [c for c in filtered_daily.columns if c not in ['Datum', 'Datum_Vorig_Jaar', 'Datum_Raw', '网站要事记']]
    agg_rules = {}
    for col in all_metrics_cols:
        col_str = str(col)
        if any(k in col_str for k in ['率', '占比', 'Share', 'Rate', '收录', '外链', '%']):
            agg_rules[col] = 'mean'
        else:
            agg_rules[col] = lambda s: s.sum(min_count=1)

    if freq_code != "D":
        active_agg_rules = {k: v for k, v in agg_rules.items() if k in filtered_daily.columns}
        merged_df = filtered_daily.set_index('Datum').groupby(pd.Grouper(freq=freq_code)).agg(active_agg_rules).reset_index()
    else:
        merged_df = filtered_daily.copy()

    # Superset Total Revenue identificatie
    superset_tot_col = None
    for c in ["Superset 网站总销售额", "Superset 总销售额", "Superset销售额"]:
        if c in df.columns:
            superset_tot_col = c
            break

    if superset_tot_col is None:
        for c in df.columns:
            if "superset" in str(c).lower() and "总销售额" in str(c):
                superset_tot_col = c
                break

    if "Superset SEO销售额" in merged_df.columns and superset_tot_col and superset_tot_col in merged_df.columns:
        merged_df['Superset_Share_Calculated'] = np.where(
            merged_df[superset_tot_col] > 0,
            (merged_df['Superset SEO销售额'] / merged_df[superset_tot_col]) * 100,
            np.nan
        )
    if "Superset SEO销售额_LY" in merged_df.columns and f"{superset_tot_col}_LY" in merged_df.columns:
        merged_df['Superset_Share_Calculated_LY'] = np.where(
            merged_df[f"{superset_tot_col}_LY"] > 0,
            (merged_df['Superset SEO销售额_LY'] / merged_df[f"{superset_tot_col}_LY"]) * 100,
            np.nan
        )

    # -------------------- YOY MATCHING GSC SHEET --------------------
    if not df_gsc.empty:
        df_gsc_daily = df_gsc.copy()
        df_gsc_daily['Datum_Vorig_Jaar'] = df_gsc_daily['Datum'] - YOY_OFFSET
        gsc_cols_to_merge = [c for c in gsc_numeric_cols if c in df_gsc_daily.columns]

        gsc_daily_merged = pd.merge(
            df_gsc_daily,
            df_gsc_daily[['Datum'] + gsc_cols_to_merge],
            left_on='Datum_Vorig_Jaar',
            right_on='Datum',
            how='left',
            suffixes=('', '_LY')
        )

        filtered_gsc_daily = gsc_daily_merged[(gsc_daily_merged['Datum'].dt.date >= filter_start) & (gsc_daily_merged['Datum'].dt.date <= end_date)].copy()

        # Alleen regels opstellen voor kolommen die daadwerkelijk bestaan in filtered_gsc_daily
        gsc_agg_rules = {}
        for col in filtered_gsc_daily.columns:
            if col not in ['Datum', 'Datum_Vorig_Jaar']:
                col_str = str(col)
                if any(k in col_str.lower() for k in ['排名', 'position', 'rank', 'ctr', '率', '占比', '%']):
                    gsc_agg_rules[col] = 'mean'
                else:
                    gsc_agg_rules[col] = lambda s: s.sum(min_count=1)

        if freq_code != "D" and not filtered_gsc_daily.empty:
            merged_gsc_df = filtered_gsc_daily.set_index('Datum').groupby(pd.Grouper(freq=freq_code)).agg(gsc_agg_rules).reset_index()
        else:
            merged_gsc_df = filtered_gsc_daily.copy()
    else:
        merged_gsc_df = pd.DataFrame()
        filtered_gsc_daily = pd.DataFrame()

    # -------------------- PERIOD DISPLAY STRING --------------------
    start_str = start_date.strftime('%d-%m-%Y')
    end_str = end_date.strftime('%d-%m-%Y')
    period_title = f"({start_str} to {end_str}) — 今年 vs 去年 [{granularity}]"

    # -------------------- TABS --------------------
    tab1, tab2, tab3, tab4 = st.tabs([
        "💰 Revenue Metrics", 
        "📈 Traffic Metrics", 
        "🔍 SEO & Backlink Status",
        "📊 SEO weekly data GSC"
    ])

    # ==================== TAB 1: REVENUE METRICS ====================
    with tab1:
        st.markdown(f"<h4 class='kpi-header'>📌 Revenue Period Summary {period_title}</h4>", unsafe_allow_html=True)
        
        c_ga4_seo = filtered_daily['GA4 SEO销售额'].sum(skipna=True) if 'GA4 SEO销售额' in filtered_daily.columns else 0
        ly_ga4_seo = filtered_daily['GA4 SEO销售额_LY'].sum(skipna=True) if 'GA4 SEO销售额_LY' in filtered_daily.columns else 0

        c_ss_seo = filtered_daily['Superset SEO销售额'].sum(skipna=True) if 'Superset SEO销售额' in filtered_daily.columns else 0
        ly_ss_seo = filtered_daily['Superset SEO销售额_LY'].sum(skipna=True) if 'Superset SEO销售额_LY' in filtered_daily.columns else 0

        c_ss_tot = filtered_daily[superset_tot_col].sum(skipna=True) if superset_tot_col and superset_tot_col in filtered_daily.columns else 0
        ly_ss_tot = filtered_daily[f"{superset_tot_col}_LY"].sum(skipna=True) if superset_tot_col and f"{superset_tot_col}_LY" in filtered_daily.columns else 0

        c_ga4_tot = filtered_daily['GA4 网站总销售额'].sum(skipna=True) if 'GA4 网站总销售额' in filtered_daily.columns else 0
        ly_ga4_tot = filtered_daily['GA4 网站总销售额_LY'].sum(skipna=True) if 'GA4 网站总销售额_LY' in filtered_daily.columns else 0

        c_share = (c_ss_seo / c_ss_tot * 100) if c_ss_tot > 0 else 0
        ly_share = (ly_ss_seo / ly_ss_tot * 100) if ly_ss_tot > 0 else 0

        c_ai_rev = filtered_daily['AI Assistant 销售额'].sum(skipna=True) if 'AI Assistant 销售额' in filtered_daily.columns else 0
        ly_ai_rev = filtered_daily['AI Assistant 销售额_LY'].sum(skipna=True) if 'AI Assistant 销售额_LY' in filtered_daily.columns else 0

        r1_c1, r1_c2, r1_c3 = st.columns(3)
        with r1_c1:
            st.metric("GA4 SEO Revenue (GA4 SEO销售额)", f"${c_ga4_seo:,.2f}", format_kpi_delta(c_ga4_seo - ly_ga4_seo, ly_ga4_seo, is_currency=True))
            st.caption(f"去年: ${ly_ga4_seo:,.2f}")
        with r1_c2:
            st.metric("Superset SEO Revenue (Superset SEO销售额)", f"${c_ss_seo:,.2f}", format_kpi_delta(c_ss_seo - ly_ss_seo, ly_ss_seo, is_currency=True))
            st.caption(f"去年: ${ly_ss_seo:,.2f}")
        with r1_c3:
            label_ss_title = f"Total Website Revenue ({superset_tot_col})" if superset_tot_col else "Total Website Revenue (Superset 总销售额)"
            st.metric(label_ss_title, f"${c_ss_tot:,.2f}", format_kpi_delta(c_ss_tot - ly_ss_tot, ly_ss_tot, is_currency=True))
            st.caption(f"去年: ${ly_ss_tot:,.2f}")

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        r2_c1, r2_c2, r2_c3 = st.columns(3)
        with r2_c1:
            st.metric("GA4 Total Revenue (GA4 网站总销售额)", f"${c_ga4_tot:,.2f}", format_kpi_delta(c_ga4_tot - ly_ga4_tot, ly_ga4_tot, is_currency=True))
            st.caption(f"去年: ${ly_ga4_tot:,.2f}")
        with r2_c2:
            st.metric("Superset SEO Share (Superset SEO销售额占比)", f"{c_share:.2f}%", format_kpi_delta(c_share - ly_share, ly_share, is_pct=True))
            st.caption(f"去年: {ly_share:.2f}%")
        with r2_c3:
            st.metric("AI Assistant Revenue (AI Assistant 销售额)", f"${c_ai_rev:,.2f}", format_kpi_delta(c_ai_rev - ly_ai_rev, ly_ai_rev, is_currency=True))
            st.caption(f"去年: ${ly_ai_rev:,.2f}")

        st.markdown("---")
        col_a, col_b = st.columns(2)
        with col_a:
            st.plotly_chart(create_yoy_chart(merged_df, "GA4 SEO销售额", "GA4 SEO Revenue (GA4 SEO销售额)", "Revenue ($)", freq_code, "#1f77b4"), use_container_width=True)
            if superset_tot_col and superset_tot_col in merged_df.columns:
                st.plotly_chart(create_yoy_chart(merged_df, superset_tot_col, f"Total Website Revenue ({superset_tot_col})", "Revenue ($)", freq_code, "#2ca02c"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "Superset_Share_Calculated", "Superset SEO Revenue Share (Superset SEO销售额占比)", "Percentage (%)", freq_code, "#9467bd"), use_container_width=True)
        with col_b:
            st.plotly_chart(create_yoy_chart(merged_df, "Superset SEO销售额", "Superset SEO Revenue (Superset SEO销售额)", "Revenue ($)", freq_code, "#ff7f0e"), use_container_width=True)
            if "GA4 网站总销售额" in merged_df.columns:
                st.plotly_chart(create_yoy_chart(merged_df, "GA4 网站总销售额", "GA4 Total Website Revenue (GA4 网站总销售额)", "Revenue ($)", freq_code, "#17becf"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "AI Assistant 销售额", "AI Assistant Revenue (AI Assistant 销售额)", "Revenue ($)", freq_code, "#d62728"), use_container_width=True)

    # ==================== TAB 2: TRAFFIC METRICS ====================
    with tab2:
        st.markdown(f"<h4 class='kpi-header'>📌 Traffic Period Summary {period_title}</h4>", unsafe_allow_html=True)
        
        c_seo_tr = filtered_daily['SEO流量'].sum(skipna=True) if 'SEO流量' in filtered_daily.columns else 0
        ly_seo_tr = filtered_daily['SEO流量_LY'].sum(skipna=True) if 'SEO流量_LY' in filtered_daily.columns else 0

        c_internal_tr = filtered_daily['SEO 站内流量'].sum(skipna=True) if 'SEO 站内流量' in filtered_daily.columns else 0
        ly_internal_tr = filtered_daily['SEO 站内流量_LY'].sum(skipna=True) if 'SEO 站内流量_LY' in filtered_daily.columns else 0

        c_blog_tr = filtered_daily['SEO Blog流量'].sum(skipna=True) if 'SEO Blog流量' in filtered_daily.columns else 0
        ly_blog_tr = filtered_daily['SEO Blog流量_LY'].sum(skipna=True) if 'SEO Blog流量_LY' in filtered_daily.columns else 0

        c_tot_tr = filtered_daily['网站总流量'].sum(skipna=True) if '网站总流量' in filtered_daily.columns else 0
        ly_tot_tr = filtered_daily['网站总流量_LY'].sum(skipna=True) if '网站总流量_LY' in filtered_daily.columns else 0

        c_bounce = filtered_daily['跳出率'].mean(skipna=True) if '跳出率' in filtered_daily.columns else 0
        ly_bounce = filtered_daily['跳出率_LY'].mean(skipna=True) if '跳出率_LY' in filtered_daily.columns else 0

        c_ai_tr = filtered_daily['AI Assistant 流量'].sum(skipna=True) if 'AI Assistant 流量' in filtered_daily.columns else 0
        ly_ai_tr = filtered_daily['AI Assistant 流量_LY'].sum(skipna=True) if 'AI Assistant 流量_LY' in filtered_daily.columns else 0

        t1_c1, t1_c2, t1_c3 = st.columns(3)
        with t1_c1:
            st.metric("Total SEO Traffic (SEO流量)", f"{int(c_seo_tr):,}", format_kpi_delta(c_seo_tr - ly_seo_tr, ly_seo_tr))
            st.caption(f"去年: {int(ly_seo_tr):,}")
        with t1_c2:
            st.metric("Internal SEO Traffic (SEO 站内流量)", f"{int(c_internal_tr):,}", format_kpi_delta(c_internal_tr - ly_internal_tr, ly_internal_tr))
            st.caption(f"去年: {int(ly_internal_tr):,}")
        with t1_c3:
            st.metric("Blog Traffic (SEO Blog流量)", f"{int(c_blog_tr):,}", format_kpi_delta(c_blog_tr - ly_blog_tr, ly_blog_tr))
            st.caption(f"去年: {int(ly_blog_tr):,}")

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        t2_c1, t2_c2, t2_c3 = st.columns(3)
        with t2_c1:
            st.metric("Total Website Traffic (网站总流量)", f"{int(c_tot_tr):,}", format_kpi_delta(c_tot_tr - ly_tot_tr, ly_tot_tr))
            st.caption(f"去年: {int(ly_tot_tr):,}")
        with t2_c2:
            diff_bounce = c_bounce - ly_bounce
            st.metric("Bounce Rate (跳出率 - Avg)", f"{c_bounce:.1f}%", f"{diff_bounce:+.1f}% pt vs 去年", delta_color="inverse")
            st.caption(f"去年: {ly_bounce:.1f}%")
        with t2_c3:
            st.metric("AI Assistant Traffic (AI Assistant 流量)", f"{int(c_ai_tr):,}", format_kpi_delta(c_ai_tr - ly_ai_tr, ly_ai_tr))
            st.caption(f"去年: {int(ly_ai_tr):,}")

        st.markdown("---")
        col_a, col_b = st.columns(2)
        with col_a:
            st.plotly_chart(create_yoy_chart(merged_df, "SEO流量", "Total SEO Traffic (SEO流量)", "Visitors", freq_code, "#1f77b4"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "SEO Blog流量", "SEO Blog Traffic (SEO Blog流量)", "Visitors", freq_code, "#2ca02c"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "AI Assistant 流量", "AI Assistant Traffic (AI Assistant 流量)", "Visitors", freq_code, "#9467bd"), use_container_width=True)
        with col_b:
            st.plotly_chart(create_yoy_chart(merged_df, "SEO 站内流量", "Internal SEO Traffic (SEO 站内流量)", "Visitors", freq_code, "#ff7f0e"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "网站总流量", "Total Website Traffic (网站总流量)", "Visitors", freq_code, "#d62728"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "跳出率", "Bounce Rate (跳出率)", "Percentage (%)", freq_code, "#8c564b"), use_container_width=True)

    # ==================== TAB 3: SEO STATUS & BACKLINKS ====================
    with tab3:
        st.markdown(f"<h4 class='kpi-header'>📌 SEO & Backlink Status (Latest Snapshot vs 去年)</h4>", unsafe_allow_html=True)
        
        last_row = filtered_daily.dropna(subset=['Datum']).tail(1)
        if not last_row.empty:
            c_idx = last_row['收录'].values[0] if '收录' in last_row else np.nan
            ly_idx = last_row['收录_LY'].values[0] if '收录_LY' in last_row else np.nan

            c_blog_idx = last_row['Blog 收录'].values[0] if 'Blog 收录' in last_row else np.nan
            ly_blog_idx = last_row['Blog 收录_LY'].values[0] if 'Blog 收录_LY' in last_row else np.nan

            c_links = last_row['外链'].values[0] if '外链' in last_row else np.nan
            ly_links = last_row['外链_LY'].values[0] if '外链_LY' in last_row else np.nan

            c_domains = last_row['外链域名广度'].values[0] if '外链域名广度' in last_row else np.nan
            ly_domains = last_row['外链域名广度_LY'].values[0] if '外链域名广度_LY' in last_row else np.nan
        else:
            c_idx = ly_idx = c_blog_idx = ly_blog_idx = c_links = ly_links = c_domains = ly_domains = np.nan

        s1_c1, s1_c2 = st.columns(2)
        with s1_c1:
            val_str = f"{int(c_idx):,}" if pd.notna(c_idx) else "—"
            delta_str = format_kpi_delta(c_idx - ly_idx, ly_idx) if pd.notna(c_idx) and pd.notna(ly_idx) else None
            st.metric("Total Indexed Pages (收录)", val_str, delta_str)
            st.caption(f"去年: {int(ly_idx):,}" if pd.notna(ly_idx) else "去年: —")
        with s1_c2:
            val_str = f"{int(c_blog_idx):,}" if pd.notna(c_blog_idx) else "—"
            delta_str = format_kpi_delta(c_blog_idx - ly_blog_idx, ly_blog_idx) if pd.notna(c_blog_idx) and pd.notna(ly_blog_idx) else None
            st.metric("Blog Indexed Pages (Blog 收录)", val_str, delta_str)
            st.caption(f"去年: {int(ly_blog_idx):,}" if pd.notna(ly_blog_idx) else "去年: —")

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        s2_c1, s2_c2 = st.columns(2)
        with s2_c1:
            val_str = f"{int(c_links):,}" if pd.notna(c_links) else "—"
            delta_str = format_kpi_delta(c_links - ly_links, ly_links) if pd.notna(c_links) and pd.notna(ly_links) else None
            st.metric("Total Backlinks (外链)", val_str, delta_str)
            st.caption(f"去年: {int(ly_links):,}" if pd.notna(ly_links) else "去年: —")
        with s2_c2:
            val_str = f"{int(c_domains):,}" if pd.notna(c_domains) else "—"
            delta_str = format_kpi_delta(c_domains - ly_domains, ly_domains) if pd.notna(c_domains) and pd.notna(ly_domains) else None
            st.metric("Referring Domains / Breadth (外链域名广度)", val_str, delta_str)
            st.caption(f"去年: {int(ly_domains):,}" if pd.notna(ly_domains) else "去年: —")

        st.markdown("---")
        col_a, col_b = st.columns(2)
        with col_a:
            st.plotly_chart(create_yoy_chart(merged_df, "收录", "Indexed Pages (收录)", "Pages Count", freq_code, "#1f77b4"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "外链", "Total Backlinks (外链)", "Backlinks Count", freq_code, "#2ca02c"), use_container_width=True)
        with col_b:
            st.plotly_chart(create_yoy_chart(merged_df, "Blog 收录", "Indexed Blog Pages (Blog 收录)", "Blogs Count", freq_code, "#ff7f0e"), use_container_width=True)
            st.plotly_chart(create_yoy_chart(merged_df, "外链域名广度", "Referring Domains / Breadth (外链域名广度)", "Domains Count", freq_code, "#d62728"), use_container_width=True)

    # ==================== TAB 4: GSC WEEKLY DATA ====================
    with tab4:
        st.markdown(f"<h4 class='kpi-header'>📌 GSC Period Summary {period_title}</h4>", unsafe_allow_html=True)
        
        if df_gsc.empty or filtered_gsc_daily.empty:
            st.warning("No GSC data available for this range.")
        else:
            num_metrics = len(gsc_numeric_cols)
            cols_per_row = 3 if num_metrics >= 3 else 2
            
            for row_start in range(0, num_metrics, cols_per_row):
                row_metrics = gsc_numeric_cols[row_start : row_start + cols_per_row]
                row_cols = st.columns(len(row_metrics))
                
                for col_idx, col_name in enumerate(row_metrics):
                    is_pct = any(k in str(col_name).lower() for k in ['%', 'ctr', 'rate', '率', '占比'])
                    is_pos = any(k in str(col_name).lower() for k in ['排名', 'position', 'rank'])
                    
                    c_val = filtered_gsc_daily[col_name].mean(skipna=True) if (is_pct or is_pos) else filtered_gsc_daily[col_name].sum(skipna=True)
                    
                    ly_col = f"{col_name}_LY"
                    has_ly = ly_col in filtered_gsc_daily.columns and filtered_gsc_daily[ly_col].notna().any()
                    
                    if has_ly:
                        ly_val = filtered_gsc_daily[ly_col].mean(skipna=True) if (is_pct or is_pos) else filtered_gsc_daily[ly_col].sum(skipna=True)
                    else:
                        ly_val = None

                    with row_cols[col_idx]:
                        if is_pct:
                            v_str = f"{c_val:.2f}%" if pd.notna(c_val) else "—"
                            d_str = format_kpi_delta(c_val - ly_val, ly_val, is_pct=True) if ly_val is not None else None
                            st.metric(str(col_name), v_str, d_str)
                            st.caption(f"去年: {ly_val:.2f}%" if ly_val is not None else "去年: —")
                        elif is_pos:
                            v_str = f"{c_val:.1f}" if pd.notna(c_val) else "—"
                            d_str = f"{(c_val - ly_val):+.1f} pts vs 去年" if ly_val is not None else None
                            st.metric(str(col_name), v_str, d_str, delta_color="inverse")
                            st.caption(f"去年: {ly_val:.1f}" if ly_val is not None else "去年: —")
                        else:
                            v_str = f"{int(c_val):,}" if pd.notna(c_val) else "—"
                            d_str = format_kpi_delta(c_val - ly_val, ly_val) if ly_val is not None else None
                            st.metric(str(col_name), v_str, d_str)
                            st.caption(f"去年: {int(ly_val):,}" if ly_val is not None else "去年: —")
                
                st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

            st.markdown("---")
            if gsc_numeric_cols:
                cols_per_row = 2
                chart_cols = st.columns(cols_per_row)
                colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#17becf", "#bcbd22", "#e377c2", "#7f7f7f"]
                
                for idx, col_name in enumerate(gsc_numeric_cols):
                    c_idx = idx % cols_per_row
                    with chart_cols[c_idx]:
                        is_pct = any(k in str(col_name).lower() for k in ['%', 'ctr', 'rate', '率', '占比'])
                        is_pos = any(k in str(col_name).lower() for k in ['排名', 'position', 'rank'])
                        
                        y_label = "Percentage (%)" if is_pct else ("Average Position" if is_pos else "Count / Total")
                        st.plotly_chart(
                            create_yoy_chart(
                                merged_gsc_df, 
                                col_name, 
                                f"{col_name} (今年 vs 去年)", 
                                y_label, 
                                freq_code, 
                                color_current=colors[idx % len(colors)],
                                color_ly="#d3d3d3"
                            ), 
                            use_container_width=True
                        )

            # -------------------- NIEUWE GETRANSFOMEERDE VERGELIJKINGSTABEL (DATA OVERVIEW) --------------------
            st.markdown("---")
            st.subheader("📋 Data Overview — Period Comparison & Breakdown")
            st.caption("Vergelijk twee periodes vrijelijk met elkaar. De waarden/metrieken staan op de Y-as, de berekende totalen/gemiddelden en losse weekkolommen op de X-as.")

            min_gsc_date = df_gsc['Datum'].min().date()
            max_gsc_date = df_gsc['Datum'].max().date()

            pa_start = max(start_date, min_gsc_date)
            pa_end = min(end_date, max_gsc_date)

            pb_start_calc = pa_start - pd.Timedelta(days=364)
            pb_end_calc = pa_end - pd.Timedelta(days=364)
            pb_start = max(pb_start_calc, min_gsc_date)
            pb_end = min(max(pb_end_calc, min_gsc_date), max_gsc_date)

            with st.container():
                st.markdown("<div class='period-box'>", unsafe_allow_html=True)
                p_col1, p_col2 = st.columns(2)
                with p_col1:
                    st.markdown("**🔵 Periode A (今年 / Basisperiode):**")
                    pa_c1, pa_c2 = st.columns(2)
                    with pa_c1:
                        sel_pa_start = st.date_input("Start A:", value=pa_start, min_value=min_gsc_date, max_value=max_gsc_date, key="gsc_pa_start")
                    with pa_c2:
                        sel_pa_end = st.date_input("Eind A:", value=pa_end, min_value=min_gsc_date, max_value=max_gsc_date, key="gsc_pa_end")
                with p_col2:
                    st.markdown("**⚪ Periode B (去年 / Vergelijkingsperiode):**")
                    pb_c1, pb_c2 = st.columns(2)
                    with pb_c1:
                        sel_pb_start = st.date_input("Start B:", value=pb_start, min_value=min_gsc_date, max_value=max_gsc_date, key="gsc_pb_start")
                    with pb_c2:
                        sel_pb_end = st.date_input("Eind B:", value=pb_end, min_value=min_gsc_date, max_value=max_gsc_date, key="gsc_pb_end")
                st.markdown("</div>", unsafe_allow_html=True)

            if sel_pa_start > sel_pa_end:
                st.error("⚠️ Start A kan niet na Eind A liggen.")
            elif sel_pb_start > sel_pb_end:
                st.error("⚠️ Start B kan niet na Eind B liggen.")
            else:
                df_pa = df_gsc[(df_gsc['Datum'].dt.date >= sel_pa_start) & (df_gsc['Datum'].dt.date <= sel_pa_end)].sort_values('Datum')
                df_pb = df_gsc[(df_gsc['Datum'].dt.date >= sel_pb_start) & (df_gsc['Datum'].dt.date <= sel_pb_end)].sort_values('Datum')

                # Aggregatie per frequentie voor de kolommen van Periode A
                if freq_code != "D" and not df_pa.empty:
                    df_pa_breakdown_rules = {k: v for k, v in gsc_agg_rules.items() if k in df_pa.columns}
                    df_pa_breakdown = df_pa.set_index('Datum').groupby(pd.Grouper(freq=freq_code)).agg(df_pa_breakdown_rules).reset_index()
                else:
                    df_pa_breakdown = df_pa.copy()

                comparison_rows = []
                for metric in gsc_numeric_cols:
                    is_pct = any(k in str(metric).lower() for k in ['%', 'ctr', 'rate', '率', '占比'])
                    is_pos = any(k in str(metric).lower() for k in ['排名', 'position', 'rank'])

                    # Aggregatie Periode A
                    if not df_pa.empty and metric in df_pa.columns:
                        val_a = df_pa[metric].mean(skipna=True) if (is_pct or is_pos) else df_pa[metric].sum(skipna=True)
                    else:
                        val_a = np.nan

                    # Aggregatie Periode B
                    if not df_pb.empty and metric in df_pb.columns:
                        val_b = df_pb[metric].mean(skipna=True) if (is_pct or is_pos) else df_pb[metric].sum(skipna=True)
                    else:
                        val_b = np.nan

                    # Verschil & Groei
                    if pd.notna(val_a) and pd.notna(val_b):
                        diff_val = val_a - val_b
                        if is_pct:
                            growth_str = f"{diff_val:+.2f}% pt"
                        elif val_b != 0:
                            pct_gr = (diff_val / val_b) * 100
                            growth_str = f"{pct_gr:+.2f}%"
                        else:
                            growth_str = "—"
                    else:
                        diff_val = np.nan
                        growth_str = "—"

                    # Waarden formatteren
                    if is_pct:
                        str_a = f"{val_a:.2f}%" if pd.notna(val_a) else "—"
                        str_b = f"{val_b:.2f}%" if pd.notna(val_b) else "—"
                        str_diff = f"{diff_val:+.2f}% pt" if pd.notna(diff_val) else "—"
                    elif is_pos:
                        str_a = f"{val_a:.1f}" if pd.notna(val_a) else "—"
                        str_b = f"{val_b:.1f}" if pd.notna(val_b) else "—"
                        str_diff = f"{diff_val:+.1f}" if pd.notna(diff_val) else "—"
                    else:
                        str_a = f"{int(val_a):,}" if pd.notna(val_a) else "—"
                        str_b = f"{int(val_b):,}" if pd.notna(val_b) else "—"
                        str_diff = f"{int(diff_val):+,}" if pd.notna(diff_val) else "—"

                    row_dict = {
                        "Metric (指标)": str(metric),
                        f"Totaal Periode A ({sel_pa_start.strftime('%d/%m')} - {sel_pa_end.strftime('%d/%m/%y')})": str_a,
                        f"Totaal Periode B ({sel_pb_start.strftime('%d/%m')} - {sel_pb_end.strftime('%d/%m/%y')})": str_b,
                        "Verschil (Diff)": str_diff,
                        "Groei (% Change)": growth_str
                    }

                    # Voeg de afzonderlijke week-/dagkolommen van Periode A toe
                    if not df_pa_breakdown.empty:
                        for _, p_row in df_pa_breakdown.iterrows():
                            d_val = p_row['Datum']
                            col_header = d_val.strftime('%d-%m-%Y') if pd.notna(d_val) else "Datum"
                            val_detail = p_row[metric] if metric in p_row else np.nan
                            
                            if pd.isna(val_detail):
                                formatted_detail = "—"
                            elif is_pct:
                                formatted_detail = f"{val_detail:.2f}%"
                            elif is_pos:
                                formatted_detail = f"{val_detail:.1f}"
                            else:
                                formatted_detail = f"{int(val_detail):,}"

                            row_dict[col_header] = formatted_detail

                    comparison_rows.append(row_dict)

                df_comparison_table = pd.DataFrame(comparison_rows)
                st.dataframe(df_comparison_table, use_container_width=True, hide_index=True)

except Exception as e:
    st.error("An error occurred while reading the Google Sheets.")
    st.write(f"Technical details: {e}")
