-- Chaque compte possède son espace de marque. Aucun accès anonyme aux données.
create extension if not exists pgcrypto;

create table public.brand_profiles (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null unique default auth.uid() references auth.users(id) on delete cascade,
  name text not null default 'Hympyr Energies',
  descriptor text not null default '',
  territory text not null default '',
  facts jsonb not null default '[]'::jsonb check (jsonb_typeof(facts) = 'array'),
  to_validate jsonb not null default '[]'::jsonb check (jsonb_typeof(to_validate) = 'array'),
  created_at timestamptz not null default now()
);

create table public.brand_colors (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  name text not null check (length(trim(name)) between 1 and 80),
  token text not null check (length(trim(token)) between 1 and 40),
  hex text not null check (hex ~ '^#[0-9A-Fa-f]{6}$'),
  sort_order integer not null default 0,
  unique (owner_id, token)
);
create table public.brand_fonts (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  family text not null check (length(trim(family)) between 1 and 100),
  weight integer not null default 400 check (weight between 100 and 900 and weight % 100 = 0),
  unique (owner_id, family, weight)
);
create table public.brand_assets (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  name text not null check (length(trim(name)) between 1 and 200),
  kind text not null check (kind in ('logo', 'image', 'template', 'document')),
  mime text not null,
  storage_path text not null unique,
  created_at timestamptz not null default now()
);
create table public.design_templates (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  name text not null check (length(trim(name)) between 1 and 120),
  format text not null default 'Social',
  width integer not null check (width between 200 and 4000),
  height integer not null check (height between 200 and 4000),
  background_token text not null default 'V-50',
  background_asset_id uuid references public.brand_assets(id) on delete set null,
  layers jsonb not null default '[]'::jsonb check (jsonb_typeof(layers) = 'array'),
  updated_at timestamptz not null default now()
);
create table public.contents (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  title text not null check (length(trim(title)) between 1 and 240),
  channel text not null default 'Instagram',
  body text not null default '',
  sources text not null default '',
  status text not null default 'Brouillon',
  publish_date date,
  template_id uuid references public.design_templates(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table public.slides (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  content_id uuid not null references public.contents(id) on delete cascade,
  position integer not null check (position between 1 and 100),
  fields jsonb not null default '{}'::jsonb check (jsonb_typeof(fields) = 'object'),
  unique (content_id, position)
);
create table public.ideas (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  title text not null check (length(trim(title)) between 1 and 240),
  channel text not null default 'Instagram',
  priority text not null default 'Normale',
  status text not null default 'À explorer',
  notes text not null default '',
  created_at timestamptz not null default now()
);

create index contents_owner_date_idx on public.contents (owner_id, publish_date, updated_at desc);
create index slides_owner_content_idx on public.slides (owner_id, content_id, position);
create index assets_owner_idx on public.brand_assets (owner_id, created_at desc);
create index ideas_owner_idx on public.ideas (owner_id, created_at desc);
create index templates_owner_idx on public.design_templates (owner_id, updated_at desc);

-- Les clés étrangères vers des ressources du même compte sont vérifiées aussi en base.
create or replace function public.check_brand_relation() returns trigger
language plpgsql security invoker set search_path = public as $$
begin
  if TG_TABLE_NAME = 'design_templates' and new.background_asset_id is not null
     and not exists (select 1 from public.brand_assets where id = new.background_asset_id and owner_id = new.owner_id) then
    raise exception 'Asset outside owner scope';
  end if;
  if TG_TABLE_NAME = 'contents' and new.template_id is not null
     and not exists (select 1 from public.design_templates where id = new.template_id and owner_id = new.owner_id) then
    raise exception 'Template outside owner scope';
  end if;
  if TG_TABLE_NAME = 'slides' and not exists
     (select 1 from public.contents where id = new.content_id and owner_id = new.owner_id) then
    raise exception 'Content outside owner scope';
  end if;
  return new;
end $$;
revoke execute on function public.check_brand_relation() from public, anon, authenticated;
create trigger template_owner_check before insert or update on public.design_templates
  for each row execute function public.check_brand_relation();
create trigger content_owner_check before insert or update on public.contents
  for each row execute function public.check_brand_relation();
create trigger slide_owner_check before insert or update on public.slides
  for each row execute function public.check_brand_relation();

alter table public.brand_profiles enable row level security;
alter table public.brand_colors enable row level security;
alter table public.brand_fonts enable row level security;
alter table public.brand_assets enable row level security;
alter table public.design_templates enable row level security;
alter table public.contents enable row level security;
alter table public.slides enable row level security;
alter table public.ideas enable row level security;

do $$ declare tab text; begin
  foreach tab in array array['brand_profiles','brand_colors','brand_fonts','brand_assets','design_templates','contents','slides','ideas'] loop
    execute format('revoke all on public.%I from anon; grant select, insert, update, delete on public.%I to authenticated', tab, tab);
    execute format('create policy "read own" on public.%I for select to authenticated using ((select auth.uid()) = owner_id)', tab);
    execute format('create policy "insert own" on public.%I for insert to authenticated with check ((select auth.uid()) = owner_id)', tab);
    execute format('create policy "update own" on public.%I for update to authenticated using ((select auth.uid()) = owner_id) with check ((select auth.uid()) = owner_id)', tab);
    execute format('create policy "delete own" on public.%I for delete to authenticated using ((select auth.uid()) = owner_id)', tab);
  end loop;
end $$;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('brand-assets', 'brand-assets', false, 20971520,
  array['image/png','image/jpeg','image/webp','image/svg+xml','application/pdf','text/plain','text/markdown','text/html'])
on conflict (id) do nothing;

create policy "read own brand files" on storage.objects for select to authenticated
  using (bucket_id = 'brand-assets' and (storage.foldername(name))[1] = (select auth.uid())::text);
create policy "upload own brand files" on storage.objects for insert to authenticated
  with check (bucket_id = 'brand-assets' and (storage.foldername(name))[1] = (select auth.uid())::text);
create policy "delete own brand files" on storage.objects for delete to authenticated
  using (bucket_id = 'brand-assets' and (storage.foldername(name))[1] = (select auth.uid())::text);
