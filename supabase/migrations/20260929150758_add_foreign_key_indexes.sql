create index contents_template_idx on public.contents (template_id) where template_id is not null;
create index design_templates_background_asset_idx on public.design_templates (background_asset_id)
  where background_asset_id is not null;
