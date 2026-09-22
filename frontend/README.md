# CampaignIQ frontend

The frontend is a Next.js application containing authentication and the
website, HubSpot, contact, campaign, and branding screens.

## Routes

- `/`: product landing page
- `/login`, `/register`, and `/verify-otp`: authentication screens
- `/dashboard`: authenticated workspace
- `/dashboard/bots`: website intelligence
- `/dashboard/hubspot` and `/dashboard/contacts`: CRM connection and cache
- `/dashboard/campaigns`: campaign preparation, review, and sending

The dashboard uses the API helpers in `frontend/lib/api.ts` and authentication
helpers in `frontend/lib/auth.ts`.

## Local development

Install dependencies and start the development server:

```bash
cd frontend
npm ci
npm run dev
```

The app runs at `http://localhost:3000`. Configure the API origin using the
frontend environment variables described in `.env.example`; keep local
overrides in `.env.local`, which is ignored by Git.

## Validation

```bash
npm run build
npm run lint
```

The frontend uses Next.js 14, React 18, TypeScript, and Tailwind CSS.
