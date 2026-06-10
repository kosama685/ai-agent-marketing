# Integration Hooks

This Streamlit Cloud edition is intentionally lightweight and deployable on streamlit.app.
Production integrations that require long-running workers, browser automation, Redis, n8n, or official messaging APIs should be hosted separately and called from the Streamlit UI through webhooks/API endpoints.

Included patterns:
- `webhook_contracts.md`: payload contracts for scraping, WhatsApp, social posting, and n8n.
- `playwright_scraper_stub.py`: safe connector template for authorized sources only.
