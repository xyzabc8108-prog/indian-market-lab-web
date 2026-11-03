-- Indian Market Lab: approved retention controls.
-- Schedule: 03:20 UTC daily, without granting public database access.
-- Treat the beta as OPEN until an operator explicitly sets beta_closed_at.
-- Public intake remains controlled separately by BETA_PRIVACY_READY=false.
--
-- Approved policy:
--   feedback: purge records older than 180 days (daily sweep);
--   waitlist: purge after 12 calendar months from explicit beta closure,
--             or earlier when an individually verified withdrawal is processed;
--   pending withdrawal requests: NEVER auto-delete without identity verification.
--
-- Apply ONLY to the dedicated Indian Market Lab Supabase project.
CREATE SCHEMA IF NOT EXISTS private;
REVOKE ALL ON SCHEMA private FROM PUBLIC, anon, authenticated;

CREATE TABLE IF NOT EXISTS private.iml_retention_control (
    singleton_id integer PRIMARY KEY DEFAULT 1 CHECK (singleton_id = 1),
    beta_closed_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO private.iml_retention_control (singleton_id, beta_closed_at)
VALUES (1, NULL)
ON CONFLICT (singleton_id) DO NOTHING;
ALTER TABLE private.iml_retention_control ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE private.iml_retention_control
    FROM PUBLIC, anon, authenticated, service_role;

CREATE OR REPLACE FUNCTION private.iml_retention_cleanup()
RETURNS TABLE (feedback_deleted bigint, waitlist_deleted bigint)
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = pg_catalog
AS $cleanup$
DECLARE
    removed_feedback bigint := 0;
    removed_waitlist bigint := 0;
BEGIN
    DELETE FROM public.beta_feedback
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '180 days';
    GET DIAGNOSTICS removed_feedback = ROW_COUNT;

    -- Never infer program closure from "waitlist_open = false".
    -- Only an explicit operator-set closure starts the 12-month deadline.
    IF EXISTS (
        SELECT 1
        FROM private.iml_retention_control
        WHERE singleton_id = 1
          AND beta_closed_at IS NOT NULL
          AND CURRENT_TIMESTAMP >= beta_closed_at + INTERVAL '12 months'
    ) THEN
        DELETE FROM public.beta_waitlist;
        GET DIAGNOSTICS removed_waitlist = ROW_COUNT;
    END IF;

    RETURN QUERY SELECT removed_feedback, removed_waitlist;
END;
$cleanup$;

REVOKE ALL ON FUNCTION private.iml_retention_cleanup()
    FROM PUBLIC, anon, authenticated, service_role;

-- Running as postgres is necessary for maintenance; never grant the
-- function or the private schema to a public role.
CREATE EXTENSION IF NOT EXISTS pg_cron WITH SCHEMA pg_catalog;
SELECT cron.schedule(
    'iml-beta-retention-daily',
    '20 3 * * *',
    'SELECT private.iml_retention_cleanup();'
);

-- WHEN THE BETA PROGRAM ACTUALLY ENDS, first disable public intake in Render
-- and then explicitly record the real closure timestamp (operator action):
-- UPDATE private.iml_retention_control
-- SET beta_closed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
-- WHERE singleton_id = 1 AND beta_closed_at IS NULL;
-- Do not execute the UPDATE while the beta program is active.
--
-- Monitoring query:
-- SELECT jobid, jobname, schedule, active
-- FROM cron.job WHERE jobname = 'iml-beta-retention-daily';
-- SELECT beta_closed_at FROM private.iml_retention_control WHERE singleton_id=1;
