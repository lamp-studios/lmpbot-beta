-- LMPBot fallback storage schema for Supabase.
-- Run this once in the Supabase SQL editor (or `supabase db` migration) so the
-- Mongo -> Supabase -> SQLite fallback chain can write here when Mongo is full.

create table if not exists guild_vars (
  guild_id text not null,
  key      text not null,
  value    text,
  primary key (guild_id, key)
);

create table if not exists member_vars (
  guild_id  text not null,
  member_id text not null,
  key       text not null,
  value     text,
  primary key (guild_id, member_id, key)
);

create table if not exists user_facts (
  guild_id text not null,
  user_id  text not null,
  key      text not null,
  value    text,
  primary key (guild_id, user_id, key)
);

create table if not exists chat_memory (
  id         bigint generated always as identity primary key,
  guild_id   text,
  channel_id text,
  user_id    text,
  role       text,
  content    text,
  created_at timestamptz not null default now()
);

create index if not exists chat_memory_lookup
  on chat_memory (guild_id, channel_id, user_id, created_at desc);
