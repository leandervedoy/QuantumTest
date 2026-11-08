create extension if not exists pgcrypto;
create table if not exists public.shield_subscriptions (
 id uuid primary key default gen_random_uuid(),
 owner_id uuid not null references auth.users(id),
 project_id uuid not null,
 target_url text not null check (target_url ~ '^https://'),
 stripe_customer_id text,
 stripe_subscription_id text unique,
 stripe_price_id text,
 status text not null default 'pending' check (status in ('pending','active','trialing','past_due','canceled','unpaid')),
 cadence text not null default 'monthly' check (cadence in ('monthly')),
 enabled_checks text[] not null default array['tls','pqc','security'],
 authorized_at timestamptz,
 next_run_at timestamptz,
 last_run_at timestamptz,
 created_at timestamptz not null default now(),
 unique(owner_id,project_id)
);
create table if not exists public.shield_scan_jobs (
 id uuid primary key default gen_random_uuid(),
 subscription_id uuid not null references public.shield_subscriptions(id) on delete cascade,
 scheduled_for timestamptz not null,
 status text not null default 'queued' check(status in ('queued','running','succeeded','failed')),
 attempts integer not null default 0 check(attempts between 0 and 3),
 locked_until timestamptz,
 started_at timestamptz,
 finished_at timestamptz,
 error_code text,
 result jsonb,
 created_at timestamptz not null default now(),
 unique(subscription_id,scheduled_for)
);
create table if not exists public.shield_notifications (
 id uuid primary key default gen_random_uuid(),
 subscription_id uuid not null references public.shield_subscriptions(id) on delete cascade,
 job_id uuid references public.shield_scan_jobs(id),
 kind text not null,
 payload jsonb not null default '{}'::jsonb,
 delivered_at timestamptz,
 created_at timestamptz not null default now(),
 unique(job_id,kind)
);
create index if not exists shield_due_idx on public.shield_subscriptions(next_run_at) where status='active';
create index if not exists shield_queue_idx on public.shield_scan_jobs(status,scheduled_for);
alter table public.shield_subscriptions enable row level security;
alter table public.shield_scan_jobs enable row level security;
alter table public.shield_notifications enable row level security;
create policy "owner read subscriptions" on public.shield_subscriptions for select to authenticated using (owner_id=auth.uid());
create policy "owner read jobs" on public.shield_scan_jobs for select to authenticated using (exists(select 1 from public.shield_subscriptions s where s.id=subscription_id and s.owner_id=auth.uid()));
create policy "owner read notifications" on public.shield_notifications for select to authenticated using (exists(select 1 from public.shield_subscriptions s where s.id=subscription_id and s.owner_id=auth.uid()));
-- All writes are performed only by a trusted backend service role.
create or replace function public.shield_claim_job() returns setof public.shield_scan_jobs language plpgsql security definer set search_path=public as $$
begin
 if auth.role() <> 'service_role' then raise exception 'forbidden'; end if;
 return query
 with candidate as (
   select j.id from public.shield_scan_jobs j
   join public.shield_subscriptions s on s.id=j.subscription_id
   where j.status='queued' and j.scheduled_for<=now() and j.attempts<3
   and s.status='active' and s.authorized_at is not null
   order by j.scheduled_for for update of j skip locked limit 1
 )
 update public.shield_scan_jobs j set status='running', attempts=j.attempts+1,
 started_at=now(), locked_until=now()+interval '15 minutes'
 from candidate where j.id=candidate.id returning j.*;
end $$;
revoke all on function public.shield_claim_job() from public,anon,authenticated;
grant execute on function public.shield_claim_job() to service_role;
