# -*- coding: utf-8 -*-
"""
Lizenzsystem für INAT Solutions
- 30 Tage Trial
- Professional ($8/Monat)
- Enterprise ($14/Monat)
- Super User (unbegrenzt)
"""
import os
import json
import hashlib
import hmac
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Tuple
import platform

# Geheimer Schlüssel für Lizenz-Signierung (NICHT ÄNDERN!)
_LICENSE_SECRET = b"INAT_S0lut10ns_2024_L1c3ns3_K3y_V3ry_S3cr3t!"

# Lizenz-Typen
LICENSE_TRIAL = "TRIAL"
LICENSE_PROFESSIONAL = "PROFESSIONAL"
LICENSE_ENTERPRISE = "ENTERPRISE"
LICENSE_SUPERUSER = "SUPERUSER"

# Trial-Dauer in Tagen
TRIAL_DAYS = 30

# Pfad zur Lizenzdatei
def _get_license_path() -> Path:
    """Gibt den Pfad zur Lizenzdatei zurück."""
    if platform.system() == "Windows":
        app_data = Path(os.environ.get("APPDATA", Path.home()))
    else:
        app_data = Path.home() / ".config"
    
    license_dir = app_data / "INAT-Solutions"
    license_dir.mkdir(parents=True, exist_ok=True)
    return license_dir / "license.json"


def _get_hardware_id() -> str:
    """Generiert eine eindeutige Hardware-ID."""
    import uuid
    # Kombination aus verschiedenen System-Infos
    info = f"{platform.node()}-{platform.machine()}-{uuid.getnode()}"
    return hashlib.sha256(info.encode()).hexdigest()[:16].upper()


def _sign_license(data: str) -> str:
    """Signiert Lizenzdaten."""
    signature = hmac.new(_LICENSE_SECRET, data.encode(), hashlib.sha256).digest()
    return base64.b64encode(signature).decode()[:32]


def _verify_signature(data: str, signature: str) -> bool:
    """Prüft die Signatur der Lizenzdaten."""
    expected = _sign_license(data)
    return hmac.compare_digest(expected, signature)


def generate_license_key(
    license_type: str,
    customer_name: str,
    valid_until: Optional[datetime] = None,
    hardware_id: Optional[str] = None
) -> str:
    """
    Generiert einen Lizenzschlüssel.
    
    Format: INAT-TYPE-DATA-DATA-SIGN
    """
    if license_type == LICENSE_SUPERUSER:
        # Super User: Spezieller Schlüssel, niemals ablaufend
        data = f"SU|{customer_name}|FOREVER|*"
    else:
        if valid_until is None:
            valid_until = datetime.now() + timedelta(days=365)
        
        hw = hardware_id or "*"  # * = beliebige Hardware
        data = f"{license_type[:2]}|{customer_name[:20]}|{valid_until.strftime('%Y%m%d')}|{hw}"
    
    # Daten kodieren
    encoded = base64.b64encode(data.encode()).decode()
    
    # Signatur erstellen
    signature = _sign_license(data)
    
    # Schlüssel formatieren
    combined = encoded + signature
    # In 4er-Gruppen aufteilen
    parts = [combined[i:i+4].upper() for i in range(0, min(len(combined), 16), 4)]
    
    return f"INAT-{'-'.join(parts)}"


def decode_license_key(license_key: str) -> Optional[Dict]:
    """
    Dekodiert und validiert einen Lizenzschlüssel.
    
    Returns: Dict mit license_type, customer_name, valid_until, hardware_id
             oder None wenn ungültig
    """
    try:
        # Format prüfen
        if not license_key.startswith("INAT-"):
            return None
        
        # Teile extrahieren
        parts = license_key[5:].replace("-", "")
        
        if len(parts) < 16:
            return None
        
        # Encoded data und Signatur trennen (erste 12 Zeichen = Daten, Rest = Signatur)
        # Wir brauchen mehr Zeichen für die base64-Daten
        encoded_part = parts[:len(parts)-32] if len(parts) > 32 else parts[:8]
        signature = parts[-32:] if len(parts) > 32 else parts[8:16]
        
        # Padding für base64
        encoded_padded = encoded_part + "=" * (4 - len(encoded_part) % 4) if len(encoded_part) % 4 else encoded_part
        
        try:
            data = base64.b64decode(encoded_padded.lower()).decode()
        except Exception:
            # Fallback: Versuche direkten Match für bekannte Schlüssel
            return None
        
        # Signatur prüfen
        if not _verify_signature(data, signature[:32]):
            return None
        
        # Daten parsen
        parts = data.split("|")
        if len(parts) != 4:
            return None
        
        type_code, customer, valid_date, hw_id = parts
        
        # Typ ermitteln
        type_map = {
            "SU": LICENSE_SUPERUSER,
            "PR": LICENSE_PROFESSIONAL,
            "EN": LICENSE_ENTERPRISE,
            "TR": LICENSE_TRIAL
        }
        license_type = type_map.get(type_code, LICENSE_TRIAL)
        
        # Ablaufdatum
        if valid_date == "FOREVER":
            valid_until = None  # Niemals ablaufend
        else:
            try:
                valid_until = datetime.strptime(valid_date, "%Y%m%d")
            except ValueError:
                return None
        
        return {
            "license_type": license_type,
            "customer_name": customer,
            "valid_until": valid_until,
            "hardware_id": hw_id
        }
    except Exception:
        return None


def _is_superuser_key(license_key: str) -> bool:
    """Prüft ob es ein Super User Schlüssel ist."""
    # Bekannte Super User Schlüssel (du kannst hier weitere hinzufügen)
    SUPERUSER_KEYS = [
        "INAT-SUPER-USER-MASTER-KEY1",
        "INAT-VALDRIN-HAXHI-MURAT-2024",
    ]
    return license_key.upper().strip() in [k.upper() for k in SUPERUSER_KEYS]


class LicenseManager:
    """Verwaltet die Lizenz der Anwendung."""
    
    def __init__(self):
        self._license_data: Optional[Dict] = None
        self._trial_start: Optional[datetime] = None
        self._load_license()
    
    def _load_license(self):
        """Lädt die gespeicherte Lizenz."""
        license_path = _get_license_path()
        
        if license_path.exists():
            try:
                with open(license_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Lizenzschlüssel prüfen
                if "license_key" in data:
                    key = data["license_key"]
                    
                    # Super User Check
                    if _is_superuser_key(key):
                        self._license_data = {
                            "license_type": LICENSE_SUPERUSER,
                            "customer_name": "Super User",
                            "valid_until": None,
                            "hardware_id": "*"
                        }
                        return
                    
                    # Normaler Schlüssel
                    decoded = decode_license_key(key)
                    if decoded:
                        self._license_data = decoded
                        return
                
                # Trial-Daten laden
                if "trial_start" in data:
                    self._trial_start = datetime.fromisoformat(data["trial_start"])
                else:
                    self._start_trial()
            except Exception:
                self._start_trial()
        else:
            self._start_trial()
    
    def _start_trial(self):
        """Startet die Trial-Periode."""
        self._trial_start = datetime.now()
        self._save_license()
    
    def _save_license(self):
        """Speichert die Lizenzdaten."""
        license_path = _get_license_path()
        
        data = {}
        
        if self._license_data:
            # Wir speichern den Schlüssel nicht direkt, nur die Info
            data["license_type"] = self._license_data.get("license_type", LICENSE_TRIAL)
            data["customer_name"] = self._license_data.get("customer_name", "")
            if self._license_data.get("valid_until"):
                data["valid_until"] = self._license_data["valid_until"].isoformat()
        
        if self._trial_start:
            data["trial_start"] = self._trial_start.isoformat()
        
        try:
            with open(license_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass
    
    def activate_license(self, license_key: str) -> Tuple[bool, str]:
        """
        Aktiviert einen Lizenzschlüssel.
        
        Returns: (Erfolg, Nachricht)
        """
        license_key = license_key.strip().upper()
        
        # Super User Check
        if _is_superuser_key(license_key):
            self._license_data = {
                "license_type": LICENSE_SUPERUSER,
                "customer_name": "Super User",
                "valid_until": None,
                "hardware_id": "*"
            }
            # Schlüssel speichern
            license_path = _get_license_path()
            try:
                with open(license_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "license_key": license_key,
                        "license_type": LICENSE_SUPERUSER,
                        "customer_name": "Super User",
                        "activated_at": datetime.now().isoformat()
                    }, f, indent=2)
            except Exception:
                pass
            return True, "🎉 Super User Lizenz aktiviert! Alle Funktionen freigeschaltet."
        
        # Normaler Lizenzschlüssel
        decoded = decode_license_key(license_key)
        
        if not decoded:
            return False, "❌ Ungültiger Lizenzschlüssel. Bitte überprüfen Sie die Eingabe."
        
        # Hardware-ID prüfen (wenn nicht * = beliebig)
        if decoded["hardware_id"] != "*":
            current_hw = _get_hardware_id()
            if decoded["hardware_id"] != current_hw:
                return False, "❌ Dieser Lizenzschlüssel ist für einen anderen Computer registriert."
        
        # Ablaufdatum prüfen
        if decoded["valid_until"] and decoded["valid_until"] < datetime.now():
            return False, "❌ Dieser Lizenzschlüssel ist abgelaufen."
        
        # Lizenz aktivieren
        self._license_data = decoded
        
        # Speichern
        license_path = _get_license_path()
        try:
            with open(license_path, "w", encoding="utf-8") as f:
                json.dump({
                    "license_key": license_key,
                    "license_type": decoded["license_type"],
                    "customer_name": decoded["customer_name"],
                    "valid_until": decoded["valid_until"].isoformat() if decoded["valid_until"] else None,
                    "activated_at": datetime.now().isoformat()
                }, f, indent=2)
        except Exception:
            pass
        
        type_names = {
            LICENSE_PROFESSIONAL: "Professional",
            LICENSE_ENTERPRISE: "Enterprise",
            LICENSE_SUPERUSER: "Super User"
        }
        type_name = type_names.get(decoded["license_type"], decoded["license_type"])
        
        return True, f"✅ {type_name} Lizenz erfolgreich aktiviert!"
    
    def get_license_status(self) -> Dict:
        """
        Gibt den aktuellen Lizenzstatus zurück.
        
        Returns: Dict mit:
            - is_valid: bool
            - license_type: str
            - days_remaining: int oder None
            - customer_name: str
            - message: str
        """
        # Aktive Lizenz?
        if self._license_data:
            license_type = self._license_data.get("license_type", LICENSE_TRIAL)
            customer = self._license_data.get("customer_name", "")
            valid_until = self._license_data.get("valid_until")
            
            # Super User = immer gültig
            if license_type == LICENSE_SUPERUSER:
                return {
                    "is_valid": True,
                    "license_type": LICENSE_SUPERUSER,
                    "days_remaining": None,
                    "customer_name": customer,
                    "message": "Super User - Unbegrenzte Lizenz"
                }
            
            # Ablaufdatum prüfen
            if valid_until:
                if valid_until < datetime.now():
                    return {
                        "is_valid": False,
                        "license_type": license_type,
                        "days_remaining": 0,
                        "customer_name": customer,
                        "message": "Lizenz abgelaufen"
                    }
                
                days = (valid_until - datetime.now()).days
                return {
                    "is_valid": True,
                    "license_type": license_type,
                    "days_remaining": days,
                    "customer_name": customer,
                    "message": f"{license_type} - Noch {days} Tage gültig"
                }
            
            # Lizenz ohne Ablaufdatum
            return {
                "is_valid": True,
                "license_type": license_type,
                "days_remaining": None,
                "customer_name": customer,
                "message": f"{license_type} Lizenz aktiv"
            }
        
        # Trial-Modus
        if self._trial_start:
            elapsed = (datetime.now() - self._trial_start).days
            remaining = TRIAL_DAYS - elapsed
            
            if remaining > 0:
                return {
                    "is_valid": True,
                    "license_type": LICENSE_TRIAL,
                    "days_remaining": remaining,
                    "customer_name": "",
                    "message": f"Testversion - Noch {remaining} Tage"
                }
            else:
                return {
                    "is_valid": False,
                    "license_type": LICENSE_TRIAL,
                    "days_remaining": 0,
                    "customer_name": "",
                    "message": "Testversion abgelaufen"
                }
        
        # Kein Status bekannt - Trial starten
        self._start_trial()
        return {
            "is_valid": True,
            "license_type": LICENSE_TRIAL,
            "days_remaining": TRIAL_DAYS,
            "customer_name": "",
            "message": f"Testversion - {TRIAL_DAYS} Tage"
        }
    
    def is_licensed(self) -> bool:
        """Prüft ob die App lizenziert (oder Trial aktiv) ist."""
        return self.get_license_status()["is_valid"]
    
    def is_trial(self) -> bool:
        """Prüft ob es sich um eine Trial-Version handelt."""
        return self.get_license_status()["license_type"] == LICENSE_TRIAL
    
    def is_professional(self) -> bool:
        """Prüft ob Professional oder höher."""
        status = self.get_license_status()
        return status["is_valid"] and status["license_type"] in [
            LICENSE_PROFESSIONAL, LICENSE_ENTERPRISE, LICENSE_SUPERUSER
        ]
    
    def is_enterprise(self) -> bool:
        """Prüft ob Enterprise oder höher."""
        status = self.get_license_status()
        return status["is_valid"] and status["license_type"] in [
            LICENSE_ENTERPRISE, LICENSE_SUPERUSER
        ]
    
    def is_superuser(self) -> bool:
        """Prüft ob Super User."""
        status = self.get_license_status()
        return status["license_type"] == LICENSE_SUPERUSER
    
    def reset_license(self):
        """Setzt die Lizenz zurück (für Tests)."""
        license_path = _get_license_path()
        if license_path.exists():
            license_path.unlink()
        self._license_data = None
        self._trial_start = None
        self._start_trial()


# Globale Instanz
_license_manager: Optional[LicenseManager] = None

def get_license_manager() -> LicenseManager:
    """Gibt die globale LicenseManager-Instanz zurück."""
    global _license_manager
    if _license_manager is None:
        _license_manager = LicenseManager()
    return _license_manager
