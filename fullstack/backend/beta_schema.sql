-- Run ONLY in a NEW dedicated Supabase project for Indian Market Lab.
-- Do not run against the unrelated business database.
create table if not exists public.beta_waitlist (
  id uuid primary key default gen_random_uuid(),
  email text not null,
  feature text not null check (feature in ('charts','scanner','backtesting','paper-trading','news','other')),
  consent_at timestamptz not null,
  created_at timestamptz not null default now(),
  constraint beta_waitlist_email_check check (length(email) between 5 and 254)
);
create unique index if not exists beta_waitlist_unique_email on public.beta_waitlist (lower(email));
create table if not exists public.beta_feedback (
  id uuid primary key default gen_random_uuid(),
  feature text not null check (feature in ('charts','scanner','backtesting','paper-trading','news','other')),
  rating integer not null check (rating between 1 and 5),
  message text not null check (char_length(message) between 12 and 1200),
  created_at timestamptz not null default now()
);
alter table public.beta_waitlist enable row level security;
alter table public.beta_feedback enable row level security;
revoke all on table public.beta_waitlist from anon, authenticated;
revoke all on table public.beta_feedback from anon, authenticated;
grant select, insert on table public.beta_waitlist to service_role;
grant select, insert on table public.beta_feedback to service_role;
-- No anon or authenticated policies. No public SELECT policy. Server key only.
