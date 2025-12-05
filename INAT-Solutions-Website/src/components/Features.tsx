'use client'

import { motion } from 'framer-motion'
import { useInView } from 'framer-motion'
import { useRef } from 'react'

const mainFeatures = [
  {
    icon: (
      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
    title: 'Swiss QR-Rechnungen',
    description: 'Erstellen Sie professionelle Rechnungen mit integriertem Swiss QR-Code. Automatische Berechnung, IBAN-Validierung und sofortige PDF-Generierung.',
    details: ['12 verschiedene Rechnungsstile', 'Live-PDF-Vorschau', 'Automatische Nummerierung', 'Mehrsprachig (DE/FR/EN)'],
    preview: (
      <div className="bg-white rounded-xl p-4 shadow-inner">
        <div className="flex justify-between items-start mb-3">
          <div>
            <div className="text-xs text-gray-400">RECHNUNG</div>
            <div className="text-sm font-bold text-gray-800">#2024-0847</div>
          </div>
          <div className="bg-green-100 text-green-700 text-xs px-2 py-1 rounded-full">Bezahlt</div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-xs text-gray-500 mb-2">Positionen</div>
            <div className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-gray-600">Winterreifen 4x</span>
                <span className="font-medium">680.00</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-gray-600">Montage</span>
                <span className="font-medium">120.00</span>
              </div>
              <div className="flex justify-between text-xs border-t pt-1 mt-1">
                <span className="font-medium text-gray-800">Total CHF</span>
                <span className="font-bold text-primary">800.00</span>
              </div>
            </div>
          </div>
          <div className="flex items-center justify-center">
            <div className="border-2 border-gray-200 rounded-lg p-2">
              <div className="grid grid-cols-5 gap-0.5">
                {[...Array(25)].map((_, i) => (
                  <div key={i} className={`w-2 h-2 ${Math.random() > 0.3 ? 'bg-gray-800' : 'bg-white'}`} />
                ))}
              </div>
              <div className="text-center text-xs text-gray-400 mt-1">Swiss QR</div>
            </div>
          </div>
        </div>
      </div>
    ),
  },
  {
    icon: (
      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
      </svg>
    ),
    title: 'Kundenverwaltung',
    description: 'Alle Kundendaten zentral verwaltet. Kontakthistorie, Notizen, Rechnungsübersicht und direkte Verknüpfung zu allen Geschäftsvorgängen.',
    details: ['Suchfunktion & Filter', 'Kundenhistorie', 'Schnellaktionen', 'Excel-Import/Export'],
    preview: (
      <div className="bg-white rounded-xl p-4 shadow-inner">
        <div className="flex items-center gap-3 mb-3 pb-3 border-b border-gray-100">
          <div className="w-10 h-10 bg-primary rounded-full flex items-center justify-center">
            <span className="text-white font-bold text-sm">MA</span>
          </div>
          <div className="flex-1">
            <div className="font-semibold text-gray-800 text-sm">Müller AG</div>
            <div className="text-xs text-gray-500">Zürich • Kunde seit 2022</div>
          </div>
          <div className="text-right">
            <div className="text-xs text-gray-400">Gesamt</div>
            <div className="text-sm font-bold text-green-600">CHF 18&apos;420</div>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="bg-gray-50 rounded-lg p-2">
            <div className="text-lg font-bold text-primary">12</div>
            <div className="text-xs text-gray-500">Rechnungen</div>
          </div>
          <div className="bg-gray-50 rounded-lg p-2">
            <div className="text-lg font-bold text-green-600">11</div>
            <div className="text-xs text-gray-500">Bezahlt</div>
          </div>
          <div className="bg-gray-50 rounded-lg p-2">
            <div className="text-lg font-bold text-orange-500">1</div>
            <div className="text-xs text-gray-500">Offen</div>
          </div>
        </div>
      </div>
    ),
  },
  {
    icon: (
      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
      </svg>
    ),
    title: '4-Fach Lagerverwaltung',
    description: 'Material-, Reifen-, Artikel- und Dienstleistungslager in einer App. Bestandsübersicht, Mindestbestand-Warnungen und vollständige Inventur.',
    details: ['4 Lagertypen', 'Barcode-Support', 'Inventur-Funktion', 'Bestandswarnungen'],
    preview: (
      <div className="bg-white rounded-xl p-4 shadow-inner">
        <div className="flex justify-between items-center mb-3">
          <div className="text-sm font-semibold text-gray-800">Reifenlager</div>
          <div className="text-xs text-primary">423 Artikel</div>
        </div>
        <div className="space-y-2">
          {[
            { name: 'Continental WinterContact', menge: 24, status: 'ok' },
            { name: 'Michelin Pilot Sport', menge: 3, status: 'low' },
            { name: 'Pirelli P Zero', menge: 16, status: 'ok' },
          ].map((item, i) => (
            <div key={i} className="flex items-center justify-between py-1.5 border-b border-gray-50">
              <span className="text-xs text-gray-700">{item.name}</span>
              <div className="flex items-center gap-2">
                <span className={`text-xs font-medium ${item.status === 'low' ? 'text-red-600' : 'text-gray-900'}`}>
                  {item.menge} Stk
                </span>
                {item.status === 'low' && (
                  <span className="text-xs bg-red-100 text-red-600 px-1.5 py-0.5 rounded">Niedrig</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    ),
  },
  {
    icon: (
      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
      </svg>
    ),
    title: 'Buchhaltung',
    description: 'Einfache Buchhaltung mit Einnahmen und Ausgaben. Automatische Verknüpfung mit Rechnungen, Zahlungserfassung und Finanzübersicht.',
    details: ['Einnahmen & Ausgaben', 'Kategorisierung', 'Monatsübersicht', 'Export für Treuhänder'],
    preview: (
      <div className="bg-white rounded-xl p-4 shadow-inner">
        <div className="flex justify-between items-center mb-3">
          <div className="text-sm font-semibold text-gray-800">November 2024</div>
          <div className="text-xs text-gray-400">Übersicht</div>
        </div>
        <div className="grid grid-cols-2 gap-2 mb-3">
          <div className="bg-green-50 rounded-lg p-2">
            <div className="text-xs text-green-600">Einnahmen</div>
            <div className="text-sm font-bold text-green-700">CHF 24&apos;850</div>
          </div>
          <div className="bg-red-50 rounded-lg p-2">
            <div className="text-xs text-red-600">Ausgaben</div>
            <div className="text-sm font-bold text-red-700">CHF 8&apos;320</div>
          </div>
        </div>
        <div className="bg-primary/10 rounded-lg p-2 text-center">
          <div className="text-xs text-primary">Gewinn</div>
          <div className="text-lg font-bold text-primary">CHF 16&apos;530</div>
        </div>
      </div>
    ),
  },
]

const additionalFeatures = [
  {
    icon: '📅',
    title: 'Auftragskalender',
    description: 'Planen Sie Aufträge und Termine übersichtlich. Drag & Drop, Erinnerungen und Tagesansicht.',
  },
  {
    icon: '📧',
    title: 'Outlook Integration',
    description: 'Rechnungen direkt per E-Mail senden. Microsoft 365 Kontakte synchronisieren.',
  },
  {
    icon: '🔄',
    title: 'Auto-Updates',
    description: 'Die App aktualisiert sich automatisch. Immer die neuesten Features ohne Aufwand.',
  },
  {
    icon: '🔒',
    title: 'Lokale Daten',
    description: 'Ihre Daten bleiben auf Ihrem PC. Keine Cloud, volle Kontrolle, maximale Sicherheit.',
  },
  {
    icon: '🌐',
    title: 'Mehrsprachig',
    description: 'Verfügbar in Deutsch, Französisch und Englisch. Wechseln Sie jederzeit die Sprache.',
  },
  {
    icon: '📊',
    title: 'Dashboard',
    description: 'Alle wichtigen KPIs auf einen Blick. Umsatz, offene Rechnungen, Termine.',
  },
  {
    icon: '🏷️',
    title: 'Kategorien',
    description: 'Organisieren Sie Kunden, Artikel und Rechnungen mit eigenen Kategorien.',
  },
  {
    icon: '📥',
    title: 'Import/Export',
    description: 'CSV-Import für Kundendaten. Export für Excel und Buchhaltungssoftware.',
  },
]

function MainFeatureCard({ feature, index, isReversed }: { feature: typeof mainFeatures[0]; index: number; isReversed: boolean }) {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: '-100px' })

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 50 }}
      animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 50 }}
      transition={{ duration: 0.6, delay: index * 0.1 }}
      className={`grid md:grid-cols-2 gap-8 items-center ${isReversed ? 'md:flex-row-reverse' : ''}`}
    >
      <div className={isReversed ? 'md:order-2' : ''}>
        <div className="inline-flex items-center justify-center w-16 h-16 bg-primary/10 text-primary rounded-2xl mb-4">
          {feature.icon}
        </div>
        <h3 className="text-2xl font-bold text-gray-900 mb-3">{feature.title}</h3>
        <p className="text-gray-600 mb-4 leading-relaxed">{feature.description}</p>
        <ul className="grid grid-cols-2 gap-2">
          {feature.details.map((detail, i) => (
            <li key={i} className="flex items-center gap-2 text-sm text-gray-700">
              <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              {detail}
            </li>
          ))}
        </ul>
      </div>
      <div className={`${isReversed ? 'md:order-1' : ''} bg-gradient-to-br from-gray-50 to-gray-100 rounded-2xl p-6`}>
        {feature.preview}
      </div>
    </motion.div>
  )
}

export default function Features() {
  const headerRef = useRef(null)
  const isHeaderInView = useInView(headerRef, { once: true })

  return (
    <section id="features" className="py-24 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <motion.div
          ref={headerRef}
          initial={{ opacity: 0, y: 30 }}
          animate={isHeaderInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
          transition={{ duration: 0.6 }}
          className="text-center mb-20"
        >
          <span className="inline-block bg-primary/10 text-primary font-semibold text-sm uppercase tracking-wider px-4 py-2 rounded-full mb-4">
            Funktionen
          </span>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 mb-6">
            Alles für Ihr Tagesgeschäft
          </h2>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            INAT Solutions bietet alle Werkzeuge, die ein Schweizer KMU für den täglichen Betrieb benötigt – 
            von der Rechnung bis zur Buchhaltung, vom Lager bis zum Kalender.
          </p>
        </motion.div>

        {/* Main Features with Previews */}
        <div className="space-y-24 mb-24">
          {mainFeatures.map((feature, index) => (
            <MainFeatureCard 
              key={feature.title} 
              feature={feature} 
              index={index}
              isReversed={index % 2 === 1}
            />
          ))}
        </div>

        {/* Additional Features Grid */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true }}
          className="mb-16"
        >
          <h3 className="text-2xl font-bold text-gray-900 text-center mb-12">
            Und noch viel mehr...
          </h3>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {additionalFeatures.map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                viewport={{ once: true }}
                className="group bg-gray-50 rounded-xl p-5 hover:bg-white hover:shadow-lg transition-all duration-300"
              >
                <span className="text-3xl mb-3 block">{feature.icon}</span>
                <h4 className="font-semibold text-gray-900 mb-2">{feature.title}</h4>
                <p className="text-sm text-gray-600">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Bottom CTA */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          viewport={{ once: true }}
          className="text-center bg-gradient-to-r from-primary to-secondary rounded-3xl p-12"
        >
          <h3 className="text-2xl sm:text-3xl font-bold text-white mb-4">
            Bereit, Ihr Geschäft zu optimieren?
          </h3>
          <p className="text-white/80 mb-8 max-w-xl mx-auto">
            Testen Sie INAT Solutions 30 Tage kostenlos und unverbindlich. 
            Keine Kreditkarte erforderlich.
          </p>
          <a
            href="#download"
            className="inline-flex items-center bg-white text-primary font-semibold px-8 py-4 rounded-full hover:bg-gray-100 transition-colors"
          >
            Jetzt kostenlos starten
            <svg className="w-5 h-5 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
            </svg>
          </a>
        </motion.div>
      </div>
    </section>
  )
}
