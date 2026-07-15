-- Run this in Supabase: Dashboard -> SQL Editor -> New query
-- (Optional — the backend will also auto-create this table on first run.)

create extension if not exists "pgcrypto";

create table if not exists tickets (
    id uuid primary key default gen_random_uuid(),
    ticket_ref text unique not null,

    name text not null,
    email text not null,
    phone text not null,

    payment_method text not null,       -- 'card' | 'bank_transfer'
    payment_status text not null default 'pending',  -- 'pending' | 'paid' | 'failed'
    amount_kobo integer not null,

    paystack_reference text unique not null,

    qr_token text,
    checked_in boolean not null default false,
    checked_in_at timestamp,

    created_at timestamp default now()
);

create index if not exists idx_tickets_email on tickets(email);
create index if not exists idx_tickets_status on tickets(payment_status);
