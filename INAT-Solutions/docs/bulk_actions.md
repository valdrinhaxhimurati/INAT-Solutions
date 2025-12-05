Bulk‑Aktionen / Mehrfachauswahl
===============================

Kurz: Die App unterstützt jetzt Mehrfachauswahl in den wichtigsten Tabellen (Kunden, Rechnungen, Artikellager, Dienstleistungen, Materiallager, Reifenlager, Lieferanten).

Was bedeutet Mehrfachauswahl?
- Du kannst mehrere Zeilen markieren (Shift/Ctrl oder einfache Klicks — siehe Auswahlmodus).

Bulk‑Löschen
- Wenn mehrere Zeilen markiert sind, klappt der "Löschen"‑Button nun mehrere Objekte in einem Schritt (Bestätigung wird abgefragt).

Warum werden beim einfachen Anklicken mehrere Zeilen markiert?
- Der momentane Auswahlmodus ist "MultiSelection". Das bedeutet: ein Klick toggelt die Auswahl einer Zeile (kein Ctrl erforderlich). Wenn du stattdessen die klassische Verhalten bevorzugst (mit Ctrl zum hinzufügen/entfernen), kann der Modus auf "ExtendedSelection" umgestellt werden.

Änderung rückgängig machen / Verhalten anpassen
- Ich habe alle Tabellen so eingestellt, dass die klassische Auswahl (ExtendedSelection) aktiv ist: Ctrl/Shift zum erweitern der Auswahl.

- Wenn du stattdessen ein Klick‑Toggle (kein Ctrl) bevorzugst, kann ich die Tabellen wieder auf MultiSelection zurückstellen.

Weiteres
- Auf Wunsch implementiere ich noch Bulk‑Export (CSV), Massen‑Aktualisierungen oder Undo für Bulk‑Löschen.

Formular‑Validierung
---------------------
Wir haben jetzt eine einfache UI‑Validierung in den wichtigsten Erfassungsdialogen (Artikel, Material, Reifen, Dienstleistungen):

- Das Feld "Preis" ist Pflicht — der OK/Bestätigen‑Button ist deaktiviert, solange kein gültiger numerischer Wert eingegeben wurde.
- Die Überprüfung akzeptiert sowohl Punkt als Dezimaltrenner ("12.95") als auch Komma ("12,95").

 Welche Felder sind jetzt Pflicht?
 - Artikellager: Bezeichnung*, Preis* (OK deaktiviert bis erfüllt)
 - Materiallager: Bezeichnung*, Preis* (OK deaktiviert bis erfüllt)
 - Reifenlager: Dimension* (z. B. "205/55 R16"), Preis* (OK deaktiviert bis erfüllt)
 - Dienstleistungen: Bezeichnung*, Preis* (OK deaktiviert bis erfüllt)
 
 (* = Pflichtfeld)
