# Indian Market Lab — Beta Storage and Admin Setup

Status: CODE ONLY. The connected Supabase account contains no dedicated Indian Market Lab project yet. The unrelated Ashok Enterprise project must not be used.

## Configure a NEW dedicated Supabase database

1. Create a separate Supabase project for Indian Market Lab and review billing/free-tier conditions.
2. Run fullstack/backend/beta_schema.sql in that project's SQL editor. It creates private RLS tables beta_waitlist, beta_feedback, and beta_withdrawal_requests. Verify role permissions and Data API access.
3. Configure these values in the Render service environment, NOT GitHub or browser JavaScript:
   BETA_SUPABASE_URL=https://YOUR-NEW-PROJECT.supabase.co
   BETA_SUPABASE_SECRET_KEY=sb_secret_...
   BETA_ADMIN_TOKEN=<a-unique-random-token-at-least-32-characters>
   BETA_PUBLIC_ORIGIN=https://indian-market-lab-fullstack.onrender.com
   BETA_PRIVACY_READY=false
4. Locally create the admin token using: python -c 'import secrets; print(secrets.token_urlsafe(48))'. Do not paste the generated secret into a chat or screenshot.
5. Test the admin and withdrawal workflow with disposable records. Confirm rohanchhaya108@gmail.com is monitored and deletion-response procedures are working.
6. Only then deliberately set BETA_PRIVACY_READY=true in Render. The status endpoint will open the public forms only after dedicated storage responds.

## API routes

Public:
- GET /api/beta/status: actual availability.
- POST /api/beta/interest: existing frontend contract email/feature/consent.
- POST /api/beta/waitlist: explicit contract email/feature_interest/consent_given.
- POST /api/beta/feedback: feature/rating/message.
- POST /api/beta/withdrawal-request: email/confirmation=true; queues a PENDING request. It does not erase anything without human verification.

Admin: HTTPS Authorization: Bearer <BETA_ADMIN_TOKEN>, never in the URL:
- GET /api/admin/submissions?kind=withdrawals&limit=30&offset=0 (or kind=waitlist / feedback). Private, paginated, no-store.
- POST /api/admin/withdrawals/{uuid}/complete: body {"verification_method":"reply-from-subscribed-email","confirmed_by_operator":true}. ONLY after ownership confirmation by replying from the subscribed mailbox.
- DELETE /api/admin/feedback/{uuid}: operator-controlled erasure of a feedback entry.
- DELETE /api/admin/withdrawals/{uuid}: discard a fraudulent/unverified request without touching the subscriber's record.

## Operational procedure

1. Review pending requests regularly via the protected admin endpoint, not application logs.
2. Verify ownership by corresponding with the person from the subscribing email address at the public support mailbox.
3. After verification, complete the withdrawal. The backend deletes BOTH the waitlist entry and the withdrawal request record that contains the same email. Discard demonstrably false/unverified requests separately without deleting subscriber records.
4. Anonymous feedback is not linked to subscriber identity; removal requires the particular feedback ID.
5. A public request is not an automated email-ownership verification or deletion. No email delivery provider is configured.
6. Test denial for missing/invalid admin tokens. Confirm that adding a contact email alone never opens the public beta.
7. Confirm GitHub Actions, Render deployment, and private database behavior before activating public collection.

## Security limitations

- Modern Supabase sb_secret_ keys belong in the apikey header, not Authorization: Bearer. They never enter browser code.
- Public signup rate limit is 3 submissions per IP per hour PER SERVER PROCESS; this is not distributed abuse protection.
- Permanent IP hashes are intentionally omitted. An IP hash remains pseudonymous personal data and is unnecessary for the present in-memory throttle.
- No self-service verification email, background retention job, CAPTCHA, or complete audit trail has been added. Plan these before scale.
- Never use the unrelated Supabase project or enable a fake form success message.

Documentation: https://supabase.com/docs/guides/getting-started/api-keys
