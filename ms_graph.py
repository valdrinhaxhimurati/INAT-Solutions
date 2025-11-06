import os
import json
import time
import requests
import msal

# --- Feste Konfiguration ---
# Ersetze diesen Wert mit deiner Multi-Tenant Client ID aus dem Azure Portal
CLIENT_ID = "88f14dfd-42bb-41c0-a26b-b6e59d615930"
TENANT_ID = "common"  # "common" ist wichtig für Multi-Tenant
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"

# Einfacher Cache-Pfad im Benutzerverzeichnis
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".inat_solutions")
CACHE_PATH = os.path.join(CACHE_DIR, "msal_cache.bin")
GRAPH_BASE = "https://graph.microsoft.com/v1.0"
SCOPES = ["Calendars.ReadWrite"]

# --- Die Funktionen _load_config und _save_config werden nicht mehr benötigt ---
# def _load_config(): ...
# def _save_config(ms_graph_cfg: dict): ...

def _ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)

def _load_token_cache():
    _ensure_cache_dir()
    cache = msal.SerializableTokenCache()
    if os.path.exists(CACHE_PATH):
        try:
            cache.deserialize(open(CACHE_PATH, "r", encoding="utf-8").read())
        except Exception:
            pass
    return cache

def _persist_cache(cache: msal.SerializableTokenCache):
    if cache.has_state_changed:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            f.write(cache.serialize())

def _build_app():
    if not CLIENT_ID or "DEINE-MULTI-TENANT-CLIENT-ID" in CLIENT_ID:
        raise RuntimeError("Microsoft Graph ist nicht konfiguriert. Der Entwickler muss die CLIENT_ID in ms_graph.py hinterlegen.")
    
    cache = _load_token_cache()
    app = msal.PublicClientApplication(client_id=CLIENT_ID, authority=AUTHORITY, token_cache=cache)
    return app, cache

def is_connected() -> bool:
    try:
        app, _ = _build_app()
        accounts = app.get_accounts()
        if not accounts:
            return False
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        return bool(result and "access_token" in result)
    except Exception:
        return False

def initiate_device_flow():
    app, cache = _build_app()
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        raise RuntimeError("Konnte Device Code Flow nicht starten.")
    # message enthält URL + Code
    return flow

def acquire_token_by_device_flow(flow: dict) -> dict:
    app, cache = _build_app()
    result = app.acquire_token_by_device_flow(flow)  # blockiert bis bestätigt/Timeout
    _persist_cache(app.token_cache)
    return result

def get_access_token() -> str:
    """Holt den Access Token aus dem Cache oder wirft einen Fehler."""
    app, cache = _build_app()
    accounts = app.get_accounts()
    token = None
    if accounts:
        token = app.acquire_token_silent(SCOPES, account=accounts[0])
    
    if not token or "access_token" not in token:
        raise RuntimeError("Nicht mit Outlook verbunden oder Token abgelaufen. Bitte zuerst anmelden.")
        
    _persist_cache(cache)
    return token["access_token"]

def create_event(subject: str, start_dt_utc, end_dt_utc, location: str = "", body_html: str = "") -> dict:
    """
    Legt ein Termin im Outlook-Kalender des angemeldeten Benutzers an.
    start_dt_utc / end_dt_utc: datetime mit tzinfo=UTC
    """
    access_token = get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "subject": subject or "",
        "body": {
            "contentType": "HTML",
            "content": body_html or ""
        },
        "start": {
            "dateTime": start_dt_utc.isoformat(),
            "timeZone": "UTC"
        },
        "end": {
            "dateTime": end_dt_utc.isoformat(),
            "timeZone": "UTC"
        },
        "location": {
            "displayName": location or ""
        }
    }
    resp = requests.post(f"{GRAPH_BASE}/me/events", headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()

def update_event(event_id, subject, start_dt_utc, end_dt_utc, location, body_html):
    """Aktualisiert einen bestehenden Termin im Outlook-Kalender."""
    access_token = get_access_token()
    headers = {
        'Authorization': 'Bearer ' + access_token,
        'Content-Type': 'application/json'
    }
    
    event_data = {
        "subject": subject,
        "body": {
            "contentType": "HTML",
            "content": body_html
        },
        "start": {
            "dateTime": start_dt_utc.isoformat(),
            "timeZone": "UTC"
        },
        "end": {
            "dateTime": end_dt_utc.isoformat(),
            "timeZone": "UTC"
        },
        "location": {
            "displayName": location
        }
    }
    
    response = requests.patch(
        f"{GRAPH_BASE}/me/events/{event_id}",
        headers=headers,
        json=event_data
    )
    response.raise_for_status() # Löst einen Fehler aus, wenn der Request fehlschlägt
    return response.json()

def delete_event(event_id):
    """Löscht einen Termin aus dem Outlook-Kalender."""
    access_token = get_access_token()
    headers = {'Authorization': 'Bearer ' + access_token}
    
    response = requests.delete(
        f"{GRAPH_BASE}/me/events/{event_id}",
        headers=headers
    )
    # Bei Erfolg gibt es keinen Body, wir prüfen nur den Status-Code
    if response.status_code not in [200, 204]:
        raise Exception(f"Fehler beim Löschen des Events: {response.text}")