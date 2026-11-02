# Indian Market Lab — Public Beta Launch

Public beta: https://indian-market-lab-fullstack.onrender.com/beta

The existing research pages and /terminal remain available. No paid subscription, live orders, licensed market feed, or guaranteed price prediction is implied.

## What is implemented

- Responsive landing page at /beta with clear feature descriptions, risks and data limitations.
- Optional email waitlist (explicit consent) and anonymous feedback forms.
- GET /api/beta/status, POST /api/beta/interest and POST /api/beta/feedback.
- Email and consent validation, restricted fields, same-origin check, per-IP request limits, and bot-trap fields.
- Collection stays OFF until a dedicated persistent database is configured.
- No marketing scripts, tracking cookies, paid subscriptions or account creation.

## Enable the waitlist and feedback

**Never use the connected Ashok Enterprise Supabase project.** That database belongs to another website. Create a dedicated Supabase project.

1. In the new project's SQL editor, run fullstack/backend/beta_schema.sql. Verify that both tables have RLS enabled and anon/authenticated lack privileges.
2. Create an sb_secret_ API key for that dedicated project. Do not paste it into GitHub or frontend assets.
3. In the Render web service's Environment settings, configure:
   BETA_SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co
   BETA_SUPABASE_SECRET_KEY=sb_secret_...
   BETA_PUBLIC_ORIGIN=https://indian-market-lab-fullstack.onrender.com
4. Redeploy Render and check /api/beta/status. Both form flags should read true once the two private tables are available.
5. Make a disposable-email signup and one feedback submission. Verify both records in the dedicated Supabase database, then delete the tests.
6. Before collecting real emails, publish a privacy-contact email and establish retention, consent withdrawal and deletion procedures. A self-service deletion request is not implemented yet.
7. Monitor false-positives, error rates and spam. The simple per-IP limiter is in memory only and is not a robust anti-bot platform.

No existing Supabase project has been modified.

## Reliability and privacy behavior

- When storage is missing, the page clearly disables both submit buttons and explains that registration is not open.
- If the backend write fails, the page reports failure, not a false confirmation.
- Duplicate waitlist emails receive generic success, without confirming whether they were already stored.
- A secret API key stays on the Render server; no browser or public API exposes it.
- Feedback is anonymous. Do not put passwords or other private details in the feedback message.
- Temporary IP-based rate counters are held in process memory, not permanently stored, and reset when the host restarts.
- Never store signup data on Render free-tier ephemeral local disks.

## Launch acceptance checklist

- [ ] /api/health responds with ok=true
- [ ] /beta works on desktop and mobile
- [ ] /terminal works and exits to the main website
- [ ] Stock Research handles unavailable providers without fabricated prices
- [ ] DD/MM/YYYY HH:MM IST dates display correctly
- [ ] Beta forms are disabled before secure storage is available
- [ ] Separate database, privacy contact and deletion procedure ready before public email collection
- [ ] Submissions display success only after a confirmed server response
- [ ] No payment or brokerage credentials requested
- [ ] GitHub Actions and Render deployment for the latest commit pass

## Four-week validation plan

Week 1: stability, responsive design, storage and privacy readiness.
Weeks 2-3: seek 15-20 voluntary testers and collect structured feedback.
Week 4: prioritize retention functionality and evaluate whether anybody wants paid features.

Review commercial market-data licensing and SEBI classification of proposed paid features before monetizing. A disclaimer does not guarantee exemption.
