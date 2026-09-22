# CampaignIQ

> A grounded outreach workspace that connects CRM contacts with website
> intelligence to create personalized, reviewable campaign sequences.

CampaignIQ is a modular monolith for grounded, personalized campaign outreach. It derives its website intelligence foundation from EmbedIQ and keeps the product boundary intentionally small:

`CampaignIQ auth → HubSpot CRM → website intelligence → campaign generation → review → external email delivery → scheduled follow-ups`

## Repository layout

- `backend/` FastAPI, SQLAlchemy/Alembic, PostgreSQL/pgvector, Redis/Celery
- `frontend/` Next.js and Tailwind dashboard
- `Doc & prd/` locked product requirements, implementation reality, and feature history

## Intended workflow

1. Connect CampaignIQ to HubSpot and select the contacts for an outreach run.
2. Crawl and index website content to create a grounded intelligence layer.
3. Generate personalized campaign drafts from the CRM and site context.
4. Review and approve messages before external delivery.
5. Schedule follow-ups and track the campaign workflow from the dashboard.

## Local development

1. Copy `.env.example` to `.env` and provide required credentials.
2. Start PostgreSQL/pgvector and Redis with `docker compose up -d postgres redis`.
3. Run the backend from `backend/` with `uvicorn app.main:app --reload`.
4. Run the frontend from `frontend/` with `npm install && npm run dev`.

This repository is currently scaffolded from the reusable EmbedIQ foundation. Feature milestones are tracked in `Doc & prd/implementation.md`.

## Development notes

CampaignIQ is a modular monolith. The reusable crawling, extraction, knowledge,
embedding, retrieval, security, and infrastructure concepts are retained from
the foundation, while chatbot/widget/conversation surfaces are deliberately
outside this product’s scope.

The upstream implementation reviewed for this derivation is
[`awaisbaloch0334/Embeddable-AI-ARG-Chatbot`](https://github.com/awaisbaloch0334/Embeddable-AI-ARG-Chatbot)
at commit `ccfc436ff79cfa1c1053161cd68eb66f25a3eb39`. CampaignIQ retains only
the reusable crawling, extraction, knowledge, embedding, retrieval, security,
and infrastructure concepts; chatbot, widget, conversation, and analytics
product surfaces are intentionally excluded by the CampaignIQ PRD.
