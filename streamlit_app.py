import streamlit as st
import pandas as pd

# Pagina instellingen
st.set_page_config(
    page_title="Callie NL - Marketing & Sales Kanban",
    page_icon="📊",
    layout="wide"
)

# Titel en introductie
st.title("📊 Callie NL — Performance Kanban Board")
st.caption("Visueel overzicht van verkoop, bezoekers, SEO-prestaties en AI Assistant data.")

# Sidebar: Mogelijkheid om cijfers live aan te passen
st.sidebar.header("⚙️ Gegevens Invoeren / Aanpassen")
st.sidebar.write("Pas hieronder de cijfers aan om het Kanban-board direct bij te werken:")

# Aanpasbare data met standaardwaarden gebaseerd op jouw kolommen
with st.sidebar.form("metrics_form"):
    st.subheader("💰 Verkoop & Omzet")
    superset_seo_sales = st.number_input("Superset SEO 销售额 (€)", value=4500.0)
    superset_share = st.number_input("Superset 总销售额占比情况 (%)", value=25.5)
    ga4_seo_sales = st.number_input("GA4 SEO 销售额 (€)", value=4200.0)
    ga4_total_sales = st.number_input("GA4 网站总销售额 (€)", value=16500.0)
    ai_sales = st.number_input("AI Assistant 销售额 (€)", value=1250.0)

    st.subheader("📈 Traffic & Bezoekers")
    total_traffic = st.number_input("网站总流量 (Totaal)", value=35000)
    seo_traffic = st.number_input("SEO 流量", value=12500)
    seo_internal_traffic = st.number_input("SEO 站内流量", value=8900)
    seo_blog_traffic = st.number_input("SEO Blog 流量", value=3600)
    ai_traffic = st.number_input("AI Assistant 流量", value=1400)
    bounce_rate = st.number_input("跳出率 Bounce Rate (%)", value=42.3)

    st.subheader("🔍 SEO Status & Backlinks")
    index_total = st.number_input("收录 (Geïndexeerd totaal)", value=450)
    index_blog = st.number_input("Blog 收录 (Geïndexeerde blogs)", value=120)
    backlinks = st.number_input("外链 (Backlinks)", value=1850)
    referring_domains = st.number_input("外链域名广度 (Domein breedte)", value=310)

    submitted = st.form_submit_button("Opslaan & Bijwerken")

# -------------------- KANBAN BOARD INDELING --------------------

col1, col2, col3 = st.columns(3)

# KOLOM 1: VERKOOP & OMZET (Sales)
with col1:
    st.subheader("💰 Verkoop & Omzet")
    st.markdown("---")
    
    with st.container(border=True):
        st.markdown("**Superset SEO 销售额**")
        st.metric(label="SEO Omzet (Superset)", value=f"€ {superset_seo_sales:,.2f}")
        st.caption(f"Aandeel van totaal: **{superset_share}%**")

    with st.container(border=True):
        st.markdown("**GA4 SEO 销售额**")
        st.metric(label="SEO Omzet (GA4)", value=f"€ {ga4_seo_sales:,.2f}")

    with st.container(border=True):
        st.markdown("**GA4 网站总销售额**")
        st.metric(label="Totale Omzet Website", value=f"€ {ga4_total_sales:,.2f}")

    with st.container(border=True):
        st.markdown("**AI Assistant 销售额**")
        st.metric(label="AI Assistant Omzet", value=f"€ {ai_sales:,.2f}")

# KOLOM 2: TRAFFIC & BEZOEKERS (Verkeer)
with col2:
    st.subheader("📈 Traffic & Bezoekers")
    st.markdown("---")
    
    with st.container(border=True):
        st.markdown("**网站总流量**")
        st.metric(label="Totaal Websiteverkeer", value=f"{total_traffic:,}")

    with st.container(border=True):
        st.markdown("**SEO 流量 & Verdeling**")
        st.metric(label="Totaal SEO Verkeer", value=f"{seo_traffic:,}")
        st.write(f"• 站内流量 (Intern): **{seo_internal_traffic:,}**")
        st.write(f"• Blog 流量: **{seo_blog_traffic:,}**")

    with st.container(border=True):
        st.markdown("**AI Assistant 流量**")
        st.metric(label="AI Verkeer", value=f"{ai_traffic:,}")

    with st.container(border=True):
        st.markdown("**跳出率 (Bounce Rate)**")
        st.metric(label="Bounce Rate", value=f"{bounce_rate}%")

# KOLOM 3: SEO STATUS & BACKLINKS (Autoriteit)
with col3:
    st.subheader("🔍 SEO & Backlink Status")
    st.markdown("---")
    
    with st.container(border=True):
        st.markdown("**收录情况 (Indexering)**")
        st.metric(label="Totale Pagina's Geïndexeerd", value=f"{index_total}")
        st.caption(f"Waarvan Blogs (Blog 收录): **{index_blog}**")

    with st.container(border=True):
        st.markdown("**外链数据 (Backlinks)**")
        st.metric(label="Totaal Aantal Backlinks", value=f"{backlinks:,}")

    with st.container(border=True):
        st.markdown("**外链域名广度 (Domein Breedte)**")
        st.metric(label="Verwijzende Domeinen", value=f"{referring_domains:,}")

st.markdown("---")
st.info("💡 **Tip:** Aan de linkerkant (in het zijmenu) kun je de getallen direct aanpassen en opslaan.")
