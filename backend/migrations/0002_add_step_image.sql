-- Migration: add step_image column to conversations table
-- Run with: psql <connection_string> -f backend/migrations/0002_add_step_image.sql

ALTER TABLE conversations
  ADD COLUMN IF NOT EXISTS step_image TEXT;

-- Optional: backfill logic could be added here if you have previous guide outputs stored elsewhere.
