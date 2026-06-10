from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from salesforge.config import DB_PATH, ai_settings
from salesforge.content_engine import CONTENT_TYPES, generate_content, save_content, schema_markup
from salesforge.database import (
    add_company,
    execute,
    fetch_all,
    fetch_one,
    init_db,
    log_workflow,
    utc_now,
)
from salesforge.demo_data import create_mock_scraped_leads, seed_demo_data
from salesforge.outreach import build_sequence, generate_outreach, get_primary_contact, log_outreach
from salesforge.proposal import PACKAGES, create_pdf, generate_proposal_text, save_proposal_record
from salesforge.scoring import build_gap_analysis, score_company
from salesforge.utils import dataframe_to_csv_bytes, make_qr_png, money, pct

st.set_page_config(
    page_title="SalesForge AI ERP",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db(DB_PATH)
seed_demo_data()


# ----------------------------- UI FOUNDATION -----------------------------

def inject_css() -> None:
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
            html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
            .block-container { padding-top: 1.6rem; padding-bottom: 3rem; }
            .hero {
                padding: 28px 30px;
                border-radius: 28px;
                background: radial-gradient(circle at top left, rgba(124,58,237,.55), transparent 32%),
                            linear-gradient(135deg, #0f172a 0%, #111827 45%, #1e1b4b 100%);
                border: 1px solid rgba(255,255,255,.12);
                box-shadow: 0 30px 80px rgba(0,0,0,.36);
                margin-bottom: 1.1rem;
            }
            .hero h1 { margin: 0; font-size: 2.6rem; line-height: 1.05; font-weight: 850; letter-spacing: -0.06em; }
            .hero p { color: rgba(248,250,252,.78); font-size: 1.02rem; margin-top: 10px; max-width: 900px; }
            .pill { display:inline-flex; align-items:center; gap:.35rem; padding:.35rem .68rem; border-radius:999px; background:rgba(124,58,237,.18); border:1px solid rgba(167,139,250,.35); color:#ddd6fe; font-size:.78rem; margin-right:.35rem; }
            .metric-card {
                padding: 19px 18px; border-radius: 22px;
                background: linear-gradient(180deg, rgba(17,24,39,.96), rgba(15,23,42,.86));
                border: 1px solid rgba(148,163,184,.18);
                box-shadow: 0 18px 50px rgba(0,0,0,.23);
            }
            .metric-label { color:#94a3b8; font-size:.82rem; font-weight:600; text-transform:uppercase; letter-spacing:.07em; }
            .metric-value { font-size:2rem; font-weight:850; color:#f8fafc; letter-spacing:-.04em; margin-top:3px; }
            .metric-note { color:#a7f3d0; font-size:.82rem; margin-top:3px; }
            .section-title { font-size:1.35rem; font-weight:800; margin: 1.2rem 0 .65rem; letter-spacing:-.03em; }
            .lead-card {
                padding: 14px 14px; border-radius: 18px; margin-bottom: 12px;
                background: rgba(15,23,42,.78); border:1px solid rgba(148,163,184,.17);
            }
            .hot { color:#fecaca; background:rgba(220,38,38,.16); border:1px solid rgba(248,113,113,.22); }
            .warm { color:#fed7aa; background:rgba(234,88,12,.14); border:1px solid rgba(251,146,60,.22); }
            .cold { color:#bfdbfe; background:rgba(37,99,235,.14); border:1px solid rgba(96,165,250,.22); }
            .badge { display:inline-block; padding:.18rem .48rem; border-radius:999px; font-weight:700; font-size:.72rem; }
            .muted { color:#94a3b8; }
            .stButton>button { border-radius: 14px; font-weight:700; border:1px solid rgba(167,139,250,.35); }
            div[data-testid="stSidebar"] { background: linear-gradient(180deg, #060812 0%, #111827 100%); }
            div[data-testid="stDataFrame"] { border-radius: 18px; overflow:hidden; }
            textarea { font-family: 'Inter', sans-serif !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str, pills: list[str] | None = None) -> None:
    pill_html = "".join(f"<span class='pill'>{p}</span>" for p in (pills or []))
    st.markdown(
        f"""
        <div class="hero">
            <div>{pill_html}</div>
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, note: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def score_badge(label: str) -> str:
    cls = {"HOT": "hot", "WARM": "warm", "COLD": "cold"}.get(str(label).upper(), "cold")
    return f"<span class='badge {cls}'>{label}</span>"


def load_companies() -> pd.DataFrame:
    rows = fetch_all("SELECT * FROM companies WHERE deleted_at IS NULL ORDER BY score_value DESC, updated_at DESC")
    return pd.DataFrame(rows)


def load_deals() -> pd.DataFrame:
    return pd.DataFrame(fetch_all("SELECT d.*, c.name AS company_name, c.lead_score FROM deals d JOIN companies c ON c.id=d.company_id WHERE c.deleted_at IS NULL ORDER BY d.updated_at DESC"))


def company_options() -> dict[str, int]:
    rows = fetch_all("SELECT id, name, industry, country FROM companies WHERE deleted_at IS NULL ORDER BY name")
    return {f"{r['name']} — {r['industry']} / {r['country']}": int(r["id"]) for r in rows}


def selected_company(label: str = "Select lead/company") -> dict[str, Any] | None:
    options = company_options()
    if not options:
        st.warning("No companies in the CRM yet. Add leads first.")
        return None
    key = st.selectbox(label, list(options.keys()))
    return fetch_one("SELECT * FROM companies WHERE id=?", (options[key],))


def recent_logs(limit: int = 12) -> pd.DataFrame:
    return pd.DataFrame(fetch_all("SELECT module, action, status, message, created_at FROM workflow_logs ORDER BY id DESC LIMIT ?", (limit,)))


inject_css()

with st.sidebar:
    st.markdown("### ⚡ SalesForge AI ERP")
    st.caption("Streamlit Cloud Edition")
    nav = st.radio(
        "Navigation",
        [
            "Command Center",
            "Lead Discovery",
            "AI Scoring",
            "Pipeline CRM",
            "Outreach",
            "Proposal Studio",
            "Content + SEO/GEO/AEO",
            "Exhibition Manager",
            "Analytics",
            "Daily Automation",
            "Settings",
        ],
        label_visibility="collapsed",
    )
    st.divider()
    ai = ai_settings()
    st.caption("AI Router")
    st.success("OpenRouter live") if ai.enabled else st.info("Demo AI fallback")
    st.caption(f"Database: `{DB_PATH.name}`")


# ----------------------------- PAGES -----------------------------

def page_command_center() -> None:
    hero(
        "SalesForge AI ERP",
        "A centralized sales and marketing command center for lead discovery, AI qualification, outreach, proposals, content, exhibitions, and daily operations.",
        ["Find Leads", "Qualify", "Generate Content", "Close Sales", "Retain Clients"],
    )
    companies = load_companies()
    deals = load_deals()
    total_leads = len(companies)
    hot = int((companies["lead_score"] == "HOT").sum()) if not companies.empty else 0
    pipeline_value = float(deals["value"].sum()) if not deals.empty else 0
    won_value = float(deals.loc[deals["stage"] == "CLOSED_WON", "value"].sum()) if not deals.empty else 0
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Total Leads", str(total_leads), "+ demo database ready")
    with c2:
        metric_card("Hot Leads", f"{hot}", pct(hot / total_leads * 100 if total_leads else 0))
    with c3:
        metric_card("Pipeline Value", money(pipeline_value), "open + active deals")
    with c4:
        metric_card("Closed Revenue", money(won_value), "demo / tracked won")

    st.markdown("<div class='section-title'>Executive View</div>", unsafe_allow_html=True)
    col_a, col_b = st.columns([1.2, 1])
    with col_a:
        if not companies.empty:
            chart = companies.groupby(["industry", "lead_score"]).size().reset_index(name="count")
            fig = px.bar(chart, x="industry", y="count", color="lead_score", title="Lead Score by Industry", height=390)
            fig.update_layout(margin=dict(l=10, r=10, t=45, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
    with col_b:
        if not deals.empty:
            pie = deals.groupby("stage")["value"].sum().reset_index()
            fig = px.pie(pie, names="stage", values="value", title="Pipeline Value by Stage", hole=.52, height=390)
            fig.update_layout(margin=dict(l=10, r=10, t=45, b=10), paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("<div class='section-title'>Top Priority Leads</div>", unsafe_allow_html=True)
    top_cols = ["id", "name", "industry", "country", "city", "lead_score", "score_value", "status", "score_reason"]
    st.dataframe(companies[top_cols].head(12), use_container_width=True, hide_index=True)

    st.download_button(
        "Export Leads CSV",
        dataframe_to_csv_bytes(companies),
        file_name="salesforge_leads_export.csv",
        mime="text/csv",
    )


def page_lead_discovery() -> None:
    hero(
        "Lead Discovery Engine",
        "Generate, import, and qualify leads from priority industries. Streamlit mode uses demo-safe generation and CSV import; production browser workers can connect through the integration hooks.",
        ["Playwright-ready", "CSV import", "CRM writeback"],
    )
    industries = ["Hotel", "Restaurant", "Clinic", "Ecommerce", "Construction", "Travel Agency", "Salon", "Real Estate"]
    countries = ["Saudi Arabia", "UAE", "Pakistan", "Qatar", "Bahrain", "Kuwait", "United Kingdom", "Estonia"]
    col1, col2, col3, col4 = st.columns([1, 1, 1, .8])
    with col1:
        industry = st.selectbox("Industry", industries)
    with col2:
        country = st.selectbox("Country", countries)
    with col3:
        city = st.text_input("City", "Riyadh" if country == "Saudi Arabia" else "Dubai")
    with col4:
        count = st.number_input("Lead count", min_value=1, max_value=50, value=10)
    keywords = st.text_input("Keywords", value=f"{industry.lower()}, marketing, SEO, WhatsApp leads")
    if st.button("Run Lead Scrape / Demo Discovery", type="primary"):
        ids = create_mock_scraped_leads(industry, country, city, int(count), "Streamlit Demo Discovery")
        st.success(f"Created {len(ids)} CRM leads. Open AI Scoring to deep-analyze them.")

    st.markdown("<div class='section-title'>Import Exhibition / Directory CSV</div>", unsafe_allow_html=True)
    uploaded = st.file_uploader("Upload CSV with columns: name, website, industry, country, city, email, phone", type=["csv"])
    if uploaded is not None:
        df = pd.read_csv(uploaded)
        st.dataframe(df.head(20), use_container_width=True)
        if st.button("Import CSV Leads"):
            created = 0
            for _, row in df.iterrows():
                if not str(row.get("name", "")).strip():
                    continue
                add_company(
                    {
                        "name": row.get("name"),
                        "website": row.get("website"),
                        "industry": row.get("industry", industry),
                        "country": row.get("country", country),
                        "city": row.get("city", city),
                        "source": "CSV Import",
                        "contact": {
                            "full_name": row.get("contact", "Decision Maker"),
                            "role": row.get("role", "Decision Maker"),
                            "email": row.get("email"),
                            "phone": row.get("phone"),
                            "whatsapp": row.get("whatsapp", row.get("phone")),
                        },
                    }
                )
                created += 1
            log_workflow("LEAD_DISCOVERY", "CSV_IMPORT", "SUCCESS", f"Imported {created} leads from CSV")
            st.success(f"Imported {created} leads.")

    st.markdown("<div class='section-title'>Current Lead Table</div>", unsafe_allow_html=True)
    companies = load_companies()
    st.dataframe(companies[["id", "name", "industry", "country", "city", "source", "lead_score", "score_value", "status"]], use_container_width=True, hide_index=True)


def page_ai_scoring() -> None:
    hero(
        "AI Lead Scoring & Qualification",
        "Analyze website, SEO, social authority, review profile, Arabic GEO/AEO gaps, and conversion opportunities. Uses OpenRouter when configured, otherwise deterministic demo scoring.",
        ["HOT/WARM/COLD", "Content Gap", "Keyword Gap", "Next Best Action"],
    )
    company = selected_company()
    if not company:
        return
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        metric_card("Current Score", f"{company['lead_score']} {company['score_value']}", company.get("status", ""))
    with col2:
        metric_card("Market", f"{company.get('city') or '-'}", company.get("country", ""))
    with col3:
        metric_card("Industry", company.get("industry", "-"), company.get("source", ""))

    if st.button("Deep Analyze Lead", type="primary"):
        with st.spinner("Running AI qualification..."):
            result = score_company(company)
        st.success(f"Scored as {result['score']} ({result['score_value']}) using {result['model']}.")
        st.json(result)
        company = fetch_one("SELECT * FROM companies WHERE id=?", (company["id"],)) or company

    st.markdown("<div class='section-title'>Gap Analysis</div>", unsafe_allow_html=True)
    gap = build_gap_analysis(company)
    a, b, c = st.columns(3)
    with a:
        st.text_area("Content Gap Analysis", gap["content_gap"], height=260)
    with b:
        st.text_area("Keyword Gap Analysis", gap["keyword_gap"], height=260)
    with c:
        st.text_area("Schema / AEO Gap", gap["schema_gap"], height=260)
    st.text_area("Recommended Sales Strategy", gap["recommendations"], height=170)

    audits = pd.DataFrame(fetch_all("SELECT score, content_gap, keyword_gap, recommendations, created_at FROM seo_audits WHERE company_id=? ORDER BY id DESC LIMIT 5", (company["id"],)))
    if not audits.empty:
        st.markdown("<div class='section-title'>Audit History</div>", unsafe_allow_html=True)
        st.dataframe(audits, use_container_width=True, hide_index=True)


def page_pipeline() -> None:
    hero(
        "CRM + Sales Pipeline",
        "A practical Kanban-style pipeline with lead status, value, probability, notes, meetings, and next actions.",
        ["New", "Qualified", "Contacted", "Proposal", "Negotiation", "Won/Lost"],
    )
    deals = load_deals()
    stages = ["NEW", "QUALIFIED", "CONTACTED", "PROPOSAL_SENT", "NEGOTIATION", "CLOSED_WON", "CLOSED_LOST"]
    cols = st.columns(len(stages))
    for i, stage in enumerate(stages):
        with cols[i]:
            value = deals.loc[deals["stage"] == stage, "value"].sum() if not deals.empty else 0
            st.markdown(f"**{stage.replace('_', ' ')}**  ")
            st.caption(money(value))
            subset = deals[deals["stage"] == stage].head(5) if not deals.empty else pd.DataFrame()
            for _, row in subset.iterrows():
                st.markdown(
                    f"""
                    <div class='lead-card'>
                        <b>{row['company_name']}</b><br/>
                        {score_badge(row['lead_score'])}<br/>
                        <span class='muted'>{money(row['value'], row['currency'])} · {row['probability']}%</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.markdown("<div class='section-title'>Update Deal Stage</div>", unsafe_allow_html=True)
    company = selected_company("Select deal/company to update")
    if company:
        deal = fetch_one("SELECT * FROM deals WHERE company_id=? ORDER BY id DESC LIMIT 1", (company["id"],))
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            new_stage = st.selectbox("Stage", stages, index=stages.index(deal["stage"]) if deal and deal["stage"] in stages else 0)
        with c2:
            value = st.number_input("Deal value USD", min_value=0.0, value=float(deal["value"] if deal else 5000), step=500.0)
        with c3:
            probability = st.slider("Probability", 0, 100, int(deal["probability"] if deal else 10))
        if st.button("Save Pipeline Update", type="primary"):
            execute("UPDATE deals SET stage=?, value=?, probability=?, updated_at=? WHERE company_id=?", (new_stage, value, probability, utc_now(), company["id"]))
            execute("UPDATE companies SET status=?, updated_at=? WHERE id=?", (new_stage, utc_now(), company["id"]))
            log_workflow("PIPELINE", "UPDATE_STAGE", "SUCCESS", f"Moved {company['name']} to {new_stage}")
            st.success("Pipeline updated.")

        note = st.text_area("Add note / call summary")
        if st.button("Save Note") and note.strip():
            execute("INSERT INTO notes(company_id, note, created_at) VALUES(?,?,?)", (company["id"], note.strip(), utc_now()))
            st.success("Note saved.")


def page_outreach() -> None:
    hero(
        "AI Sales Pitch & Outreach",
        "Generate personalized email, WhatsApp, and LinkedIn messages, then log the communication and queue follow-up steps.",
        ["Email", "WhatsApp", "LinkedIn", "Follow-up Timeline"],
    )
    company = selected_company()
    if not company:
        return
    contact = get_primary_contact(int(company["id"]))
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        channel = st.selectbox("Channel", ["Email", "WhatsApp", "LinkedIn"])
    with c2:
        offer = st.selectbox("Offer", ["free marketing audit", "free SEO/GEO/AEO gap report", "20-minute strategy call", "proposal review"])
    with c3:
        subject = st.text_input("Subject", f"Increase Qualified Leads for {company['name']}")
    if st.button("Generate Personalized Outreach", type="primary"):
        st.session_state["outreach_text"] = generate_outreach(company, channel, offer)
    text = st.text_area("Message", st.session_state.get("outreach_text", ""), height=320)
    if st.button("Log as Sent / Queue in CRM") and text.strip():
        log_outreach(int(company["id"]), int(contact["id"]) if contact else None, channel, subject, text, ai_generated=True)
        st.success("Outreach logged and lead marked as CONTACTED.")

    st.markdown("<div class='section-title'>Follow-up Sequence</div>", unsafe_allow_html=True)
    seq = pd.DataFrame(build_sequence(int(company["id"])))
    st.dataframe(seq, use_container_width=True, hide_index=True)
    if st.button("Create Follow-up Tasks"):
        for idx, item in enumerate(build_sequence(int(company["id"]))):
            due = (datetime.utcnow() + timedelta(days=[1, 3, 5, 7, 10, 14][idx])).isoformat() + "Z"
            execute("INSERT INTO tasks(company_id, title, due_at, priority, status, created_at) VALUES(?,?,?,?,?,?)", (company["id"], f"{item['day']} - {item['action']} via {item['channel']}", due, "HIGH", "OPEN", utc_now()))
        log_workflow("FOLLOW_UP", "CREATE_SEQUENCE", "SUCCESS", f"Created follow-up sequence for {company['name']}")
        st.success("Follow-up task sequence created.")

    comms = pd.DataFrame(fetch_all("SELECT channel, subject, content, sent_at FROM communications WHERE company_id=? ORDER BY id DESC", (company["id"],)))
    if not comms.empty:
        st.markdown("<div class='section-title'>Communication History</div>", unsafe_allow_html=True)
        st.dataframe(comms, use_container_width=True, hide_index=True)


def page_proposal() -> None:
    hero(
        "Proposal Studio",
        "Generate branded PDF proposals with package comparisons, SEO/GEO/AEO strategy, ROI logic, and next steps.",
        ["PDF", "Package Pricing", "ROI Estimate", "Version History"],
    )
    company = selected_company()
    if not company:
        return
    deal = fetch_one("SELECT * FROM deals WHERE company_id=? ORDER BY id DESC LIMIT 1", (company["id"],))
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        package = st.selectbox("Package", list(PACKAGES.keys()), index=1)
    with col2:
        price = st.number_input("Total value USD", value=float(PACKAGES[package]["price"]), min_value=0.0, step=500.0)
    with col3:
        st.metric("Timeline", PACKAGES[package]["duration"])
    if st.button("Generate Proposal Draft", type="primary"):
        with st.spinner("Drafting proposal..."):
            st.session_state["proposal_text"] = generate_proposal_text(company, package)
    text = st.text_area("Proposal content", st.session_state.get("proposal_text", ""), height=420)
    if text.strip():
        pdf_bytes = create_pdf(company, package, text)
        filename = f"salesforge_proposal_{company['id']}_{package.lower()}.pdf"
        st.download_button("Download PDF Proposal", pdf_bytes, file_name=filename, mime="application/pdf")
        if st.button("Save Proposal Record"):
            save_proposal_record(int(company["id"]), int(deal["id"]) if deal else None, package, float(price), text, filename)
            st.success("Proposal saved and pipeline moved to PROPOSAL_SENT.")

    proposals = pd.DataFrame(fetch_all("SELECT package, total_value, currency, status, version, pdf_filename, created_at FROM proposals WHERE company_id=? ORDER BY id DESC", (company["id"],)))
    if not proposals.empty:
        st.markdown("<div class='section-title'>Version History</div>", unsafe_allow_html=True)
        st.dataframe(proposals, use_container_width=True, hide_index=True)


def page_content() -> None:
    hero(
        "AI Content + SEO/GEO/AEO Engine",
        "Create blogs, social posts, ad copy, video scripts, FAQ schema, Arabic GEO/AEO plans, and content/keyword gap analyses.",
        ["Content Gap", "Keyword Gap", "Schema", "AI Search"],
    )
    options = {"No specific lead": None} | company_options()
    company_label = st.selectbox("Attach to company", list(options.keys()))
    company = fetch_one("SELECT * FROM companies WHERE id=?", (options[company_label],)) if options[company_label] else None
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        ctype = st.selectbox("Content type", CONTENT_TYPES)
    with col2:
        tone = st.selectbox("Tone", ["corporate", "premium", "direct-response", "educational", "Arabic-friendly English"])
    with col3:
        title = st.text_input("Title", "90-day growth plan for qualified leads")
    topic = st.text_area("Brief / topic", "Create content that identifies content gaps, keyword gaps, FAQ/AEO opportunities, and sales CTA.", height=100)
    if st.button("Generate Content", type="primary"):
        with st.spinner("Creating content strategy..."):
            st.session_state["content_output"] = generate_content(company, ctype, topic, tone)
    text = st.text_area("Generated content", st.session_state.get("content_output", ""), height=420)
    kw_text = st.text_input("SEO keywords", "local SEO, GEO optimization, AI search visibility, WhatsApp leads")
    if st.button("Save Content Piece") and text.strip():
        save_content(int(company["id"]) if company else None, ctype, title, text, [k.strip() for k in kw_text.split(",") if k.strip()])
        st.success("Content saved.")

    if company:
        st.markdown("<div class='section-title'>Ready Schema Markup</div>", unsafe_allow_html=True)
        st.code(schema_markup(company), language="json")

    rows = pd.DataFrame(fetch_all("SELECT id, type, title, published, scheduled_at, created_at FROM content_pieces ORDER BY id DESC LIMIT 20"))
    if not rows.empty:
        st.markdown("<div class='section-title'>Recent Content Library</div>", unsafe_allow_html=True)
        st.dataframe(rows, use_container_width=True, hide_index=True)


def page_exhibitions() -> None:
    hero(
        "Exhibition Manager",
        "Track events, generate booth QR codes, import attendee lists, and trigger CRM follow-up sequences.",
        ["GITEX", "ATM", "QR Capture", "Auto Follow-up"],
    )
    events = pd.DataFrame(fetch_all("SELECT * FROM exhibitions ORDER BY start_date"))
    st.dataframe(events[["id", "name", "location", "start_date", "end_date", "booth_status", "leads_captured", "follow_up_status"]], use_container_width=True, hide_index=True)
    event_options = {f"{r['name']} — {r['location']}": int(r["id"]) for _, r in events.iterrows()} if not events.empty else {}
    if event_options:
        event_label = st.selectbox("Select exhibition", list(event_options.keys()))
        event_id = event_options[event_label]
        event = fetch_one("SELECT * FROM exhibitions WHERE id=?", (event_id,))
        qr_data = event.get("qr_code_data") or f"salesforge://exhibition/{event_id}"
        qr_bytes = make_qr_png(qr_data)
        c1, c2 = st.columns([.7, 1.3])
        with c1:
            st.image(qr_bytes, caption="Booth lead capture QR", width=220)
            st.download_button("Download QR PNG", qr_bytes, file_name=f"exhibition_{event_id}_qr.png", mime="image/png")
        with c2:
            st.info("Use this QR on booth material. In production, point it to a form URL that writes into ExhibitionLead and creates a CRM lead.")
            attendee = st.text_input("Attendee name")
            email = st.text_input("Email")
            phone = st.text_input("Phone / WhatsApp")
            interest = st.text_input("Interest", "SEO/GEO/AEO growth proposal")
            if st.button("Capture Exhibition Lead") and attendee.strip():
                company_id = add_company(
                    {
                        "name": f"{attendee} Exhibition Lead",
                        "industry": "Exhibition Lead",
                        "country": event["location"].split(",")[-1].strip() if event else "Unknown",
                        "city": event["location"].split(",")[0].strip() if event else "Unknown",
                        "source": event["name"],
                        "lead_score": "WARM",
                        "score_value": 60,
                        "contact": {"full_name": attendee, "email": email, "phone": phone, "whatsapp": phone, "role": "Event Attendee"},
                    }
                )
                execute("INSERT INTO exhibition_leads(exhibition_id, company_id, attendee_name, email, phone, interest, created_at) VALUES(?,?,?,?,?,?,?)", (event_id, company_id, attendee, email, phone, interest, utc_now()))
                execute("UPDATE exhibitions SET leads_captured=leads_captured+1 WHERE id=?", (event_id,))
                log_workflow("EXHIBITION", "CAPTURE_LEAD", "SUCCESS", f"Captured {attendee} at {event['name']}")
                st.success("Exhibition lead captured and added to CRM.")


def page_analytics() -> None:
    hero(
        "Analytics Dashboard",
        "Monitor ROI, pipeline movement, lead sources, conversion rates, channel activity, and content production.",
        ["ROI", "Pipeline", "Sources", "Channel Performance"],
    )
    companies = load_companies()
    deals = load_deals()
    comms = pd.DataFrame(fetch_all("SELECT * FROM communications ORDER BY sent_at DESC"))
    col1, col2, col3, col4 = st.columns(4)
    conversion = 0
    if not deals.empty:
        conversion = len(deals[deals["stage"] == "CLOSED_WON"]) / max(1, len(deals)) * 100
    with col1:
        metric_card("Conversion Rate", pct(conversion), "closed won / deals")
    with col2:
        metric_card("Avg Score", f"{companies['score_value'].mean():.0f}" if not companies.empty else "0", "lead quality")
    with col3:
        metric_card("Meetings Booked", str(len(fetch_all("SELECT id FROM meetings"))), "tracked")
    with col4:
        metric_card("Messages Sent", str(len(comms)), "logged outreach")

    a, b = st.columns(2)
    with a:
        if not companies.empty:
            source = companies.groupby("source").size().reset_index(name="leads")
            fig = px.bar(source, x="source", y="leads", title="Leads by Source", height=390)
            fig.update_layout(margin=dict(l=10, r=10, t=45, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
    with b:
        if not comms.empty:
            ch = comms.groupby("channel").size().reset_index(name="messages")
            fig = px.pie(ch, names="channel", values="messages", title="Outreach by Channel", hole=.5, height=390)
            fig.update_layout(margin=dict(l=10, r=10, t=45, b=10), paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No outreach logged yet. Generate outreach to populate channel analytics.")

    logs = recent_logs(25)
    st.markdown("<div class='section-title'>Workflow Log</div>", unsafe_allow_html=True)
    st.dataframe(logs, use_container_width=True, hide_index=True)


def execute_daily_operations() -> list[dict[str, str]]:
    steps = [
        ("06:00", "AI reports, SEO plans, social posts, ad copy, outreach campaigns generated"),
        ("09:00", "Priority lead discovery generated and CRM updated"),
        ("11:00", "AI qualification and CRM updates completed"),
        ("14:00", "Sales outreach queue populated"),
        ("17:00", "Client reporting and KPI refresh completed"),
        ("20:00", "Social publishing queue prepared"),
    ]
    result: list[dict[str, str]] = []
    for time_label, msg in steps:
        log_workflow("DAILY_AUTOMATION", time_label, "SUCCESS", msg)
        result.append({"time": time_label, "status": "SUCCESS", "message": msg})
    return result


def page_daily_automation() -> None:
    hero(
        "Daily Automation Flow",
        "Execute the 6 AM director workflow: reports, lead discovery, qualification, outreach, client reporting, and social publishing preparation.",
        ["6 AM", "9 AM", "11 AM", "2 PM", "5 PM", "8 PM"],
    )
    if st.button("Execute Daily Operations", type="primary"):
        rows = execute_daily_operations()
        st.success("Daily automation flow executed in demo mode.")
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.markdown("<div class='section-title'>Recent Execution Log</div>", unsafe_allow_html=True)
    st.dataframe(recent_logs(50), use_container_width=True, hide_index=True)


def page_settings() -> None:
    hero(
        "Settings + Integration Center",
        "Manage API-key readiness, demo mode, exports, reset data, and production integration guidance.",
        ["OpenRouter", "WhatsApp", "Email", "Social APIs", "Demo Mode"],
    )
    ai = ai_settings()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("AI Router")
        st.write("Live AI enabled:" , "✅ Yes" if ai.enabled else "❌ No, using deterministic demo fallback")
        st.code(
            """# Streamlit Cloud Secrets
OPENROUTER_API_KEY = "sk-or-..."
OPENROUTER_MODEL_SCORING = "google/gemini-flash-1.5"
OPENROUTER_MODEL_CREATIVE = "anthropic/claude-3.5-sonnet"
OPENROUTER_MODEL_FAST = "openai/gpt-4o-mini""",
            language="toml",
        )
    with c2:
        st.subheader("Production Notes")
        st.markdown(
            """
            - Streamlit Cloud edition is optimized for dashboard + CRM + AI workflows.
            - Run Playwright, Redis/BullMQ, n8n, WhatsApp and social posting workers outside Streamlit.
            - Connect them with webhooks using `integrations/webhook_contracts.md`.
            - Use an external database for long-term multi-user production persistence.
            """
        )
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Reset Demo Database"):
            seed_demo_data(force=True)
            st.success("Demo data reset.")
    with col2:
        companies = load_companies()
        st.download_button("Download CRM CSV", dataframe_to_csv_bytes(companies), file_name="salesforge_crm.csv", mime="text/csv")
    with col3:
        st.metric("DB file", DB_PATH.name)

    st.markdown("<div class='section-title'>System Tables</div>", unsafe_allow_html=True)
    stats = []
    for table in ["companies", "contacts", "deals", "communications", "proposals", "content_pieces", "exhibitions", "workflow_logs"]:
        row = fetch_one(f"SELECT COUNT(*) AS total FROM {table}")
        stats.append({"table": table, "records": row["total"] if row else 0})
    st.dataframe(pd.DataFrame(stats), use_container_width=True, hide_index=True)


PAGES = {
    "Command Center": page_command_center,
    "Lead Discovery": page_lead_discovery,
    "AI Scoring": page_ai_scoring,
    "Pipeline CRM": page_pipeline,
    "Outreach": page_outreach,
    "Proposal Studio": page_proposal,
    "Content + SEO/GEO/AEO": page_content,
    "Exhibition Manager": page_exhibitions,
    "Analytics": page_analytics,
    "Daily Automation": page_daily_automation,
    "Settings": page_settings,
}

PAGES[nav]()

st.caption("SalesForge AI ERP Streamlit Cloud Edition · Built for demo, proposal, and early operational use. Connect external workers for production-scale scraping, queues, and posting.")
