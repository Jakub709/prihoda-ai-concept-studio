-- PŘÍHODA Concept Studio: server-only access, private assets, atomic versions.
create table if not exists public.prihoda_projects (
  id uuid primary key,
  name text not null,
  latest_version integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.prihoda_versions (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.prihoda_projects(id) on delete cascade,
  version integer not null check (version > 0),
  parameters jsonb not null,
  assets jsonb not null,
  note text not null default '',
  created_at timestamptz not null default now(),
  unique(project_id, version)
);
alter table public.prihoda_projects enable row level security;
alter table public.prihoda_versions enable row level security;
revoke all on public.prihoda_projects, public.prihoda_versions from anon, authenticated;
grant select, insert, update, delete on public.prihoda_projects, public.prihoda_versions to service_role;

create or replace view public.prihoda_project_library with (security_invoker = true) as
select p.id, p.name, p.latest_version, p.created_at, p.updated_at,
  v.parameters->'room' as room, v.parameters->'ducts' as ducts
from public.prihoda_projects p
join public.prihoda_versions v on v.project_id=p.id and v.version=p.latest_version;
revoke all on public.prihoda_project_library from anon, authenticated;
grant select on public.prihoda_project_library to service_role;

create or replace function public.save_prihoda_version(
  p_id uuid, p_name text, p_expected integer, p_parameters jsonb, p_assets jsonb, p_note text
) returns jsonb language plpgsql security invoker set search_path = public as $$
declare current_version integer; next_version integer;
begin
  insert into public.prihoda_projects (id, name) values (p_id, p_name) on conflict (id) do nothing;
  select latest_version into current_version from public.prihoda_projects where id=p_id for update;
  if current_version <> p_expected then
    raise exception 'Version conflict' using errcode = '40001';
  end if;
  next_version := current_version + 1;
  insert into public.prihoda_versions(project_id, version, parameters, assets, note)
    values (p_id, next_version, p_parameters, p_assets, p_note);
  update public.prihoda_projects set name=p_name, latest_version=next_version, updated_at=now() where id=p_id;
  return jsonb_build_object('project_id', p_id, 'version', next_version, 'name', p_name);
end;
$$;
revoke all on function public.save_prihoda_version(uuid,text,integer,jsonb,jsonb,text) from public, anon, authenticated;
grant execute on function public.save_prihoda_version(uuid,text,integer,jsonb,jsonb,text) to service_role;
insert into storage.buckets (id, name, public, file_size_limit)
values ('prihoda-concepts', 'prihoda-concepts', false, 104857600) on conflict (id) do nothing;
notify pgrst, 'reload schema';
