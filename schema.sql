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
  anrede   TEXT,
  bemerkung TEXT
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

-- Buchhaltung
CREATE TABLE IF NOT EXISTS public.buchhaltung (
  buchung_id BIGSERIAL PRIMARY KEY,
  datum TEXT,
  betrag REAL,
  kategorie TEXT,
  beschreibung TEXT
);

-- App-weite Einstellungen (Key-Value, inkl. BLOBs wie Logo)
CREATE TABLE IF NOT EXISTS app_settings (
  key TEXT PRIMARY KEY,
  value_bytes BLOB,
  value_text TEXT,
  mime TEXT,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
-- Für PostgreSQL wird BYTEA statt BLOB verwendet (siehe settings_store.py).

-- Tabelle für allgemeine Konfigurationen (ersetzt config.json)
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Tabelle für Rechnungslayout (ersetzt rechnung_layout.json)
CREATE TABLE IF NOT EXISTS rechnung_layout (
    id INTEGER PRIMARY KEY DEFAULT 1,
    layout_data TEXT  -- JSON-String speichern
);

-- Tabelle für Einstellungen (ersetzt einstellungen.json, z.B. Kategorien)
CREATE TABLE IF NOT EXISTS einstellungen (
    id INTEGER PRIMARY KEY DEFAULT 1,
    data TEXT  -- JSON-String speichern
);

-- Tabelle für QR-Daten (ersetzt qr_daten.json)
CREATE TABLE IF NOT EXISTS qr_daten (
    id INTEGER PRIMARY KEY DEFAULT 1,
    data TEXT  -- JSON-String speichern
);

-- =========================
-- PATCH: Tabellen für SQLite
-- =========================

-- Kunden
CREATE TABLE IF NOT EXISTS kunden (
  kundennr INTEGER PRIMARY KEY AUTOINCREMENT,
  name     TEXT,
  firma    TEXT,
  plz      TEXT,
  strasse  TEXT,
  stadt    TEXT,
  email    TEXT,
  anrede   TEXT,
  bemerkung TEXT
);

-- Reifenlager
CREATE TABLE IF NOT EXISTS reifenlager (
  reifen_id INTEGER PRIMARY KEY AUTOINCREMENT,
  kundennr INTEGER,
  kunde_anzeige TEXT,
  fahrzeug TEXT,
  dimension TEXT,
  typ TEXT,
  dot TEXT,
  lagerort TEXT,
  eingelagert_am TEXT,
  ausgelagert_am TEXT,
  bemerkung TEXT
);

-- Artikellager
CREATE TABLE IF NOT EXISTS artikellager (
  artikel_id INTEGER PRIMARY KEY AUTOINCREMENT,
  artikelnummer TEXT,
  bezeichnung TEXT,
  bestand INTEGER,
  lagerort TEXT
);

-- Lieferanten
CREATE TABLE IF NOT EXISTS lieferanten (
  lieferantnr INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT,
  portal_link TEXT,
  login TEXT,
  passwort TEXT
);

-- Buchhaltung
CREATE TABLE IF NOT EXISTS buchhaltung (
  buchung_id INTEGER PRIMARY KEY AUTOINCREMENT,
  datum TEXT,
  betrag REAL,
  kategorie TEXT,
  beschreibung TEXT
);

-- Tabelle für zentrale gespeicherte Rechnungen (SQLite-Variante)
CREATE TABLE IF NOT EXISTS invoices (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  buchung_id INTEGER,
  filename TEXT NOT NULL,
  content BLOB NOT NULL,
  content_type TEXT DEFAULT 'application/pdf',
  size INTEGER NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================
-- PATCH: Tabellen für Postgres
-- ============================

-- Kunden
CREATE TABLE IF NOT EXISTS kunden (
  kundennr BIGSERIAL PRIMARY KEY,
  name     TEXT,
  firma    TEXT,
  plz      TEXT,
  strasse  TEXT,
  stadt    TEXT,
  email    TEXT,
  anrede   TEXT,
  bemerkung TEXT
);

-- Reifenlager
CREATE TABLE IF NOT EXISTS reifenlager (
  reifen_id BIGSERIAL PRIMARY KEY,
  kundennr INTEGER,
  kunde_anzeige TEXT,
  fahrzeug TEXT,
  dimension TEXT,
  typ TEXT,
  dot TEXT,
  lagerort TEXT,
  eingelagert_am TEXT,
  ausgelagert_am TEXT,
  bemerkung TEXT
);

-- Artikellager
CREATE TABLE IF NOT EXISTS artikellager (
  artikel_id BIGSERIAL PRIMARY KEY,
  artikelnummer TEXT,
  bezeichnung TEXT,
  bestand INTEGER,
  lagerort TEXT
);

-- Lieferanten
CREATE TABLE IF NOT EXISTS lieferanten (
  lieferantnr BIGSERIAL PRIMARY KEY,
  name TEXT,
  portal_link TEXT,
  login TEXT,
  passwort TEXT
);

-- Buchhaltung
CREATE TABLE IF NOT EXISTS buchhaltung (
  buchung_id BIGSERIAL PRIMARY KEY,
  datum TEXT,
  betrag REAL,
  kategorie TEXT,
  beschreibung TEXT
);

-- Tabelle für zentrale gespeicherte Rechnungen (Postgres-Variante)
CREATE TABLE IF NOT EXISTS invoices (
  id BIGSERIAL PRIMARY KEY,
  buchung_id BIGINT,
  filename TEXT NOT NULL,
  content BYTEA NOT NULL,
  content_type TEXT DEFAULT 'application/pdf',
  size INTEGER NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Beispiel-Insert für MWST-Default (nur einmalig ausführen, z.B. beim ersten DB-Setup)
INSERT OR IGNORE INTO config (key, value) VALUES ('mwst_default', '0.0');
