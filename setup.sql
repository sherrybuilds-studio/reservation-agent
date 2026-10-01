-- Run once in the Supabase SQL editor.
-- date and time are the restaurant's local date and wall-clock time ("2026-10-02", "20:00");
-- timestamptz columns are written in UTC.
create table reservations (
  id uuid default gen_random_uuid() primary key,
  restaurant_id text, customer_name text, phone text,
  party_size int, date text, time text,
  status text default 'confirmed', notes text,
  confirmation_number text, created_at timestamptz default now(),
  customer_confirmed boolean default false,
  reminder_24h_sent boolean default false, reminder_2h_sent boolean default false,
  review_request_sent boolean default false, review_request_sent_at timestamptz
);
create table customers (
  id uuid default gen_random_uuid() primary key,
  phone text unique, name text, visit_count int default 0,
  last_visit timestamptz, preferences text, no_show_count int default 0
);
create table waitlist (
  id uuid default gen_random_uuid() primary key,
  restaurant_id text, phone text, name text,
  party_size int, date text, time text,
  status text default 'waiting', created_at timestamptz default now(),
  notified_at timestamptz, expires_at timestamptz
);
create table broadcast_log (
  id uuid default gen_random_uuid() primary key,
  restaurant_id text, broadcast_id text, sent_at timestamptz,
  sent_count int, failed_count int, reply_count int default 0,
  booking_count int default 0, discount_percent int, message_preview text
);
create table review_log (
  id uuid default gen_random_uuid() primary key,
  restaurant_id text, review_id text, reviewer_name text,
  stars int, text text, received_at text, alerted_at timestamptz
);
create table analytics (
  id uuid default gen_random_uuid() primary key,
  restaurant_id text, date text, questions_asked int default 0,
  bookings_made int default 0, upsells_converted int default 0,
  reviews_sent int default 0, positive_reviews int default 0
);
