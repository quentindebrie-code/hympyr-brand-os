-- A record's columns are only available on its own table. PL/pgSQL does not
-- guarantee short-circuit evaluation across the old TG_TABLE_NAME AND checks.
create or replace function public.check_brand_relation() returns trigger
language plpgsql security invoker set search_path = public as $$
begin
  if TG_TABLE_NAME = 'design_templates' then
    if new.background_asset_id is not null
       and not exists (select 1 from public.brand_assets
                       where id = new.background_asset_id and owner_id = new.owner_id) then
      raise exception 'Asset outside owner scope';
    end if;
  elsif TG_TABLE_NAME = 'contents' then
    if new.template_id is not null
       and not exists (select 1 from public.design_templates
                       where id = new.template_id and owner_id = new.owner_id) then
      raise exception 'Template outside owner scope';
    end if;
  elsif TG_TABLE_NAME = 'slides' then
    if not exists (select 1 from public.contents
                   where id = new.content_id and owner_id = new.owner_id) then
      raise exception 'Content outside owner scope';
    end if;
  else
    raise exception 'Unexpected table for brand relation check: %', TG_TABLE_NAME;
  end if;
  return new;
end $$;

revoke execute on function public.check_brand_relation() from public, anon, authenticated;
