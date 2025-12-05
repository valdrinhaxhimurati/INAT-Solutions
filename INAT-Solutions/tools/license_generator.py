# -*- coding: utf-8 -*-
"""
Lizenz-Generator für INAT Solutions
Dieses Tool ist NUR für den Administrator (dich) gedacht!
"""
import sys
import os

# Füge das Hauptverzeichnis zum Pfad hinzu
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from license import (
    generate_license_key, decode_license_key, _get_hardware_id,
    LICENSE_PROFESSIONAL, LICENSE_ENTERPRISE, LICENSE_SUPERUSER
)


def print_banner():
    print("=" * 60)
    print("   🔐 INAT Solutions - Lizenz Generator")
    print("   NUR FÜR ADMINISTRATOREN!")
    print("=" * 60)
    print()


def generate_key_interactive():
    """Interaktiver Modus zum Erstellen von Lizenzschlüsseln."""
    print_banner()
    
    print("Lizenztypen:")
    print("  1. Professional ($8/Monat)")
    print("  2. Enterprise ($14/Monat)")
    print("  3. Super User (unbegrenzt)")
    print()
    
    choice = input("Wähle Lizenztyp (1-3): ").strip()
    
    if choice == "1":
        license_type = LICENSE_PROFESSIONAL
    elif choice == "2":
        license_type = LICENSE_ENTERPRISE
    elif choice == "3":
        license_type = LICENSE_SUPERUSER
    else:
        print("Ungültige Auswahl!")
        return
    
    customer = input("Kundenname: ").strip()
    if not customer:
        customer = "Kunde"
    
    if license_type != LICENSE_SUPERUSER:
        months = input("Gültigkeitsdauer in Monaten (Standard: 12): ").strip()
        try:
            months = int(months) if months else 12
        except ValueError:
            months = 12
        
        valid_until = datetime.now() + timedelta(days=months * 30)
        
        bind_hardware = input("An Hardware binden? (j/n, Standard: n): ").strip().lower()
        if bind_hardware == "j":
            hw_id = input("Hardware-ID (oder Enter für aktuelle): ").strip()
            if not hw_id:
                hw_id = _get_hardware_id()
                print(f"Aktuelle Hardware-ID: {hw_id}")
        else:
            hw_id = None
    else:
        valid_until = None
        hw_id = None
    
    print()
    print("-" * 60)
    
    key = generate_license_key(license_type, customer, valid_until, hw_id)
    
    print(f"📋 Lizenzschlüssel erstellt:")
    print()
    print(f"   {key}")
    print()
    print(f"   Typ: {license_type}")
    print(f"   Kunde: {customer}")
    if valid_until:
        print(f"   Gültig bis: {valid_until.strftime('%d.%m.%Y')}")
    else:
        print(f"   Gültig bis: UNBEGRENZT")
    if hw_id:
        print(f"   Hardware-ID: {hw_id}")
    print("-" * 60)
    
    # Prüfen ob der Schlüssel korrekt dekodiert werden kann
    decoded = decode_license_key(key)
    if decoded:
        print("✅ Schlüssel erfolgreich verifiziert!")
    else:
        print("⚠️ Warnung: Schlüssel konnte nicht verifiziert werden!")


def show_superuser_keys():
    """Zeigt die Super User Schlüssel an."""
    print_banner()
    print("🔑 Super User Schlüssel (funktionieren immer):")
    print()
    print("   INAT-SUPER-USER-MASTER-KEY1")
    print("   INAT-VALDRIN-HAXHI-MURAT-2024")
    print()
    print("Diese Schlüssel geben vollen Zugriff ohne Ablaufdatum.")
    print("-" * 60)


def show_current_hardware_id():
    """Zeigt die aktuelle Hardware-ID an."""
    print_banner()
    hw_id = _get_hardware_id()
    print(f"🖥️ Aktuelle Hardware-ID: {hw_id}")
    print()
    print("Diese ID kann verwendet werden um Lizenzen an diesen PC zu binden.")
    print("-" * 60)


def main():
    while True:
        print()
        print("Was möchtest du tun?")
        print("  1. Neuen Lizenzschlüssel generieren")
        print("  2. Super User Schlüssel anzeigen")
        print("  3. Hardware-ID anzeigen")
        print("  4. Beenden")
        print()
        
        choice = input("Auswahl (1-4): ").strip()
        
        if choice == "1":
            generate_key_interactive()
        elif choice == "2":
            show_superuser_keys()
        elif choice == "3":
            show_current_hardware_id()
        elif choice == "4":
            print("Auf Wiedersehen!")
            break
        else:
            print("Ungültige Auswahl!")


if __name__ == "__main__":
    main()
