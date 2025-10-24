from PyQt5.QtWidgets import QHBoxLayout, QPushButton
from db_connection import get_db, dict_cursor_factory

def create_button_bar(*buttons):
    layout = QHBoxLayout()
    layout.setSpacing(10)
    layout.addStretch()
    for btn in buttons:
        layout.addWidget(btn)
    return layout

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

def exportiere_rechnung_pdf(rechnung):
    """
    Rechnung dict Beispiel:
    {
        'rechnung_nr': '2025-0001',
        'kunde': 'Max Mustermann',
        'adresse': 'Musterstrasse 1\n8000 Zürich',
        'datum': '2025-06-24',
        'positionen': [
            {'beschreibung': 'Produkt A', 'menge': 2, 'einzelpreis': 50.00},
            {'beschreibung': 'Service B', 'menge': 1, 'einzelpreis': 120.00},
        ],
        'mwst_satz': 7.7,
        'zahlungskonditionen': 'Zahlbar innert 30 Tagen ohne Abzug',
    }
    """
    datei_name = f"Rechnung_{rechnung['rechnung_nr']}.pdf"
    c = canvas.Canvas(datei_name, pagesize=A4)
    width, height = A4

    # Kopfzeile
    c.setFont("Helvetica-Bold", 16)
    c.drawString(20*mm, height - 20*mm, "Rechnung")

    # Rechnungsnummer & Datum rechts oben
    c.setFont("Helvetica", 10)
    c.drawRightString(width - 20*mm, height - 20*mm, f"Rechnungs-Nr: {rechnung['rechnung_nr']}")
    c.drawRightString(width - 20*mm, height - 28*mm, f"Datum: {rechnung['datum']}")

    # Kundenadresse links
    c.setFont("Helvetica", 10)
    kunden_adresse = rechnung['kunde'] + "\n" + rechnung['adresse']
    text_obj = c.beginText(20*mm, height - 45*mm)
    for zeile in kunden_adresse.split('\n'):
        text_obj.textLine(zeile)
    c.drawText(text_obj)

    # Positionen Tabelle
    c.setFont("Helvetica-Bold", 10)
    c.drawString(20*mm, height - 70*mm, "Beschreibung")
    c.drawString(120*mm, height - 70*mm, "Menge")
    c.drawString(140*mm, height - 70*mm, "Einzelpreis (CHF)")
    c.drawString(180*mm, height - 70*mm, "Total (CHF)")

    c.setFont("Helvetica", 10)
    y = height - 75*mm
    gesamt = 0
    for pos in rechnung['positionen']:
        total_pos = pos['menge'] * pos['einzelpreis']
        gesamt += total_pos
        c.drawString(20*mm, y, pos['beschreibung'])
        c.drawRightString(135*mm, y, str(pos['menge']))
        c.drawRightString(175*mm, y, f"{pos['einzelpreis']:.2f}")
        c.drawRightString(200*mm, y, f"{total_pos:.2f}")
        y -= 7*mm

    # MwSt und Gesamtsumme
    mwst_betrag = gesamt * rechnung['mwst_satz'] / 100
    gesamtsumme = gesamt + mwst_betrag

    y -= 10*mm
    c.drawRightString(175*mm, y, "Zwischensumme (CHF):")
    c.drawRightString(200*mm, y, f"{gesamt:.2f}")

    y -= 7*mm
    c.drawRightString(175*mm, y, f"MWST {rechnung['mwst_satz']:.1f}% (CHF):")
    c.drawRightString(200*mm, y, f"{mwst_betrag:.2f}")

    y -= 7*mm
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(175*mm, y, "Gesamtsumme (CHF):")
    c.drawRightString(200*mm, y, f"{gesamtsumme:.2f}")

    # Zahlungsbedingungen unten
    y -= 20*mm
    c.setFont("Helvetica", 9)
    c.drawString(20*mm, y, "Zahlungskonditionen:")
    y -= 5*mm
    for zeile in rechnung['zahlungskonditionen'].split('\n'):
        c.drawString(20*mm, y, zeile)
        y -= 5*mm

    c.showPage()
    c.save()
    print(f"PDF {datei_name} wurde erstellt.")


