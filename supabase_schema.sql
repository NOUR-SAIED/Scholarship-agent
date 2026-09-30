-- Paste into Supabase: SQL Editor -> New query -> Run
create table if not exists opportunities (
  id text primary key,
  source text, title text, organization text, url text,
  description text, location text, posted_at text,
  tags jsonb default '[]',
  category text, badge text, blockers jsonb default '[]',
  seniority text, skill_matches jsonb default '[]', score int default 0,
  why text, country text, deadline date, paid text, visa_sponsorship text,
  timezone_note text, classified_by text,
  status text default 'new', notes text default '',
  found_at timestamptz default now()
);
create index if not exists opportunities_status_idx on opportunities (status);
create index if not exists opportunities_category_idx on opportunities (category);

-- Lock the table: only the secret service_role key (used by the pipeline and
-- the dashboard server) can read or write. The public anon key gets nothing.
alter table opportunities enable row level security;

-- One row per daily run: per-source counts, so a silently broken source is visible.
create table if not exists runs (
  id bigserial primary key,
  ran_at timestamptz default now(),
  stats jsonb
);
alter table runs enable row level security;
