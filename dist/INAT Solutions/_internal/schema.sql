-- schema.sql
CREATE SCHEMA IF NOT EXISTS public;

-- Kunden
CREATE TABLE IF NOT EXISTS public.kunden (
  kundennr BIGSERIAL PRIMARY KEY,
  name     TEXT,
  firma    TEXT,
  plz      TEXT,
  strasse  TEXT,
  stadt    TEXT,
  email    TEXT,
  anrede   TEXT
);

-- Rechnungen
CREATE TABLE IF NOT EXISTS public.rechnungen (
  id BIGSERIAL PRIMARY KEY,
  rechnung_nr          TEXT,
  kunde                TEXT,
  firma                TEXT,
  adresse              TEXT,
  datum                TEXT,
  mwst                 REAL,
  zahlungskonditionen  TEXT,
  positionen           TEXT,
  uid                  TEXT,
  abschluss            TEXT,
  abschluss_text       TEXT
);

-- Lieferanten
CREATE TABLE IF NOT EXISTS public.lieferanten (
  lieferantnr BIGSERIAL PRIMARY KEY,
  name        TEXT,
  portal_link TEXT,
  login       TEXT,
  passwort    TEXT
);

-- Artikellager
CREATE TABLE IF NOT EXISTS public.artikellager (
  artikel_id    BIGSERIAL PRIMARY KEY,
  artikelnummer TEXT,
  bezeichnung   TEXT,
  bestand       INTEGER,
  lagerort      TEXT
);

-- Reifenlager
CREATE TABLE IF NOT EXISTS public.reifenlager (
  reifen_id      BIGSERIAL PRIMARY KEY,
  kundennr       INTEGER,
  kunde_anzeige  TEXT,
  fahrzeug       TEXT,
  dimension      TEXT,
  typ            TEXT,
  dot            TEXT,
  lagerort       TEXT,
  eingelagert_am TEXT,
  ausgelagert_am TEXT,
  bemerkung      TEXT
);
