# Webhook Contracts

## Lead Scrape Job
POST `/lead-scrape`
```json
{
  "industry": "Hotel",
  "country": "Saudi Arabia",
  "city": "Riyadh",
  "keywords": ["boutique hotel", "restaurant"],
  "limit": 25,
  "callback_url": "https://your-streamlit-api-or-worker/result"
}
```

## WhatsApp Message Event
POST `/whatsapp-inbound`
```json
{
  "provider": "meta_or_twilio",
  "phone": "+966500000000",
  "contact_name": "Ahmed Khan",
  "message": "Can you send the proposal?",
  "timestamp": "2026-06-10T12:00:00Z"
}
```

## Social Publish Job
POST `/social-publish`
```json
{
  "platform": "linkedin",
  "content_id": 12,
  "caption": "...",
  "scheduled_at": "2026-06-10T20:00:00Z"
}
```
