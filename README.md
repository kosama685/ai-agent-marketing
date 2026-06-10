# SalesForge AI ERP — Streamlit Cloud Edition

A beautiful, deployable Streamlit CRM/ERP MVP for sales and marketing operations. It is built from the uploaded Sales + Marketing AI ERP brief and adapted for easy live deployment on Streamlit Community Cloud.

## What this app does

SalesForge AI ERP centralizes the daily sales workflow:

1. Find leads
2. Qualify leads with AI
3. Generate content and SEO/GEO/AEO plans
4. Create outreach and follow-up sequences
5. Generate PDF proposals
6. Track exhibitions and QR leads
7. Monitor pipeline analytics and workflow logs

## Important architecture note

The original brief describes a large production stack with Next.js, PostgreSQL, Prisma, BullMQ, Redis, n8n, Playwright, WhatsApp APIs, social APIs, and Docker/Hetzner deployment. This ZIP is the Streamlit Cloud version, so it packages the same operational concept into a Python dashboard that can run live on streamlit.app.

For production scraping, messaging, background queues, and social posting, use the integration contracts in `integrations/` and run those workers outside Streamlit.

## Included modules

- Command Center dashboard
- Lead Discovery with demo generation and CSV import
- AI Lead Scoring with OpenRouter or demo fallback
- Content gap, keyword gap, schema gap, GEO/AEO analysis
- Pipeline CRM with stage updates
- Outreach generator for email, WhatsApp, and LinkedIn
- Follow-up sequence task creation
- Proposal Studio with branded PDF download
- Content + SEO/GEO/AEO Engine
- Exhibition Manager with QR code generation
- Analytics dashboard
- Daily Automation execution log
- Settings and integration center

## Folder structure

```text
salesforge_streamlit/
├── app.py
├── requirements.txt
├── README.md
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml.example
├── salesforge/
│   ├── __init__.py
│   ├── ai_router.py
│   ├── config.py
│   ├── content_engine.py
│   ├── database.py
│   ├── demo_data.py
│   ├── outreach.py
│   ├── proposal.py
│   ├── scoring.py
│   └── utils.py
├── integrations/
│   ├── README.md
│   ├── webhook_contracts.md
│   └── playwright_scraper_stub.py
├── docs/
│   └── ARCHITECTURE.md
└── sample_data/
    └── leads_import_sample.csv
```

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

The SQLite database `salesforge.db` is created automatically on first run and seeded with 56 demo leads.

## Enable OpenRouter AI

The app works without API keys using deterministic demo fallbacks. To enable live AI:

1. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` for local development.
2. Add your key:

```toml
OPENROUTER_API_KEY = "sk-or-your-key"
OPENROUTER_MODEL_SCORING = "google/gemini-flash-1.5"
OPENROUTER_MODEL_CREATIVE = "anthropic/claude-3.5-sonnet"
OPENROUTER_MODEL_FAST = "openai/gpt-4o-mini"
```

3. Restart Streamlit.

## Deploy live on Streamlit Community Cloud

1. Unzip this project.
2. Create a GitHub repository and upload all files.
3. Go to Streamlit Community Cloud.
4. Create a new app from your GitHub repo.
5. Set the main file path to `app.py`.
6. In app settings, add secrets if you want live OpenRouter AI.
7. Deploy.

## CSV import format

Use `sample_data/leads_import_sample.csv` as a template.

Required or recommended columns:

```text
name, website, industry, country, city, contact, role, email, phone, whatsapp
```

## Production integration plan

For a full enterprise production stack:

- Move SQLite to PostgreSQL/Supabase.
- Put Playwright scraping on a separate worker VM.
- Add Redis + BullMQ or Celery/RQ for durable queues.
- Host n8n separately and trigger it via webhooks.
- Connect official WhatsApp Business API or Twilio.
- Connect Resend/SendGrid for email.
- Connect Meta/LinkedIn/X/TikTok APIs for publishing.
- Add authentication and row-level permissions before real client use.

## Security notes

- Never commit `.streamlit/secrets.toml`.
- Do not place API keys directly in source code.
- Only scrape sources you are authorized to access.
- Use official APIs where possible.
- Treat the included demo data as fictional sample data.

## Reset demo data

Open the app, go to `Settings`, and click `Reset Demo Database`.

## License

Internal/custom project template. Adapt as needed for your business.
