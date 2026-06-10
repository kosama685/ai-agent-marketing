# SalesForge AI ERP — Streamlit Cloud Architecture

This build translates the uploaded full-stack ERP specification into a Streamlit Cloud-ready application.

## Why Streamlit edition differs from the original stack

The source brief describes a larger production stack: Next.js, Prisma, PostgreSQL, BullMQ, Redis, Playwright, n8n, SuiteCRM, and Docker/Hetzner. Streamlit Community Cloud is optimized for Python apps, dashboards, fast prototypes, and data applications. It is not the correct place to run persistent Redis workers, Node BullMQ jobs, n8n containers, or heavy browser automation.

## Included in this ZIP

- Streamlit dashboard and CRM UI
- SQLite database with schema covering Company, Lead/Contact, Deal, Communication, Proposal, Campaign, Content, Exhibition, SEOAudit, and WorkflowLog-style records
- 56 realistic demo leads across GCC/Pakistan/UK/Estonia
- AI router with OpenRouter support and local deterministic fallback
- Lead discovery demo generator and CSV import
- AI lead scoring, content gap analysis, keyword gap analysis, and schema gap analysis
- Sales outreach generator and follow-up task timeline
- Proposal PDF generation with ReportLab
- Exhibition manager with QR code generation
- Analytics dashboard and workflow logs
- Integration contracts for production workers

## Recommended production path

1. Use this Streamlit app as the executive control center and demo/prototype.
2. Host production workers separately on Hetzner, Railway, Render, or a private VPS.
3. Move the database to managed PostgreSQL or Supabase.
4. Add real outbound providers: Resend, Meta WhatsApp Cloud API or Twilio, and social APIs.
5. Add a secure API layer for worker callbacks and authentication.
