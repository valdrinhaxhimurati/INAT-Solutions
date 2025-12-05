'use client'

import { motion } from 'framer-motion'

const benefits = [
  {
    title: 'Speziell für die Schweiz',
    description: 'Swiss QR-Rechnungen, CHF-Formatierung, MWST-konform – entwickelt für Schweizer Unternehmen.',
    icon: (
      <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none">
        <rect x="3" y="3" width="18" height="18" rx="2" fill="#DC2626" />
        <path d="M12 7v10M7 12h10" stroke="white" strokeWidth="3" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    title: 'Keine Cloud, keine Sorgen',
    description: 'Ihre Daten bleiben auf Ihrem Computer. Kein Abo für Speicherplatz, keine Datenübertragung ins Ausland.',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
      </svg>
    ),
  },
  {
    title: 'Einmalzahlung möglich',
    description: 'Wählen Sie zwischen monatlichem Abo oder einmaliger Lifetime-Lizenz. Kein Zwang, flexibel bleiben.',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
      </svg>
    ),
  },
  {
    title: 'Persönlicher Support',
    description: 'Direkter Kontakt zum Entwickler. Keine Warteschleifen, keine Chatbots – echte Hilfe wenn Sie sie brauchen.',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 5.636l-3.536 3.536m0 5.656l3.536 3.536M9.172 9.172L5.636 5.636m3.536 9.192l-3.536 3.536M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-5 0a4 4 0 11-8 0 4 4 0 018 0z" />
      </svg>
    ),
  },
]

const stats = [
  { value: '12', label: 'Rechnungsstile', suffix: '' },
  { value: '4', label: 'Lagertypen', suffix: '' },
  { value: '3', label: 'Sprachen', suffix: '' },
  { value: '∞', label: 'Rechnungen', suffix: '' },
]

export default function Benefits() {
  return (
    <section id="benefits" className="py-24 bg-gray-900 text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Stats */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true }}
          className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-20"
        >
          {stats.map((stat, i) => (
            <div key={i} className="text-center">
              <div className="text-4xl sm:text-5xl font-bold text-primary mb-2">
                {stat.value}{stat.suffix}
              </div>
              <div className="text-gray-400">{stat.label}</div>
            </div>
          ))}
        </motion.div>

        {/* Main Content */}
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          {/* Left: Benefits */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
          >
            <h2 className="text-3xl sm:text-4xl font-bold mb-6">
              Warum Schweizer KMU{' '}
              <span className="text-primary">INAT Solutions</span>{' '}
              wählen
            </h2>
            <p className="text-gray-400 mb-8 text-lg">
              Entwickelt von einem Schweizer Unternehmer, für Schweizer Unternehmer. 
              Keine Kompromisse bei Qualität und Datenschutz.
            </p>

            <div className="space-y-6">
              {benefits.map((benefit, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.1 }}
                  viewport={{ once: true }}
                  className="flex gap-4"
                >
                  <div className="flex-shrink-0 w-12 h-12 bg-primary/20 rounded-xl flex items-center justify-center text-primary">
                    {benefit.icon}
                  </div>
                  <div>
                    <h3 className="font-semibold text-lg mb-1">{benefit.title}</h3>
                    <p className="text-gray-400 text-sm leading-relaxed">{benefit.description}</p>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>

          {/* Right: Feature Comparison */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            whileInView={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
            className="bg-gray-800 rounded-2xl p-8"
          >
            <h3 className="text-xl font-bold mb-6 text-center">INAT Solutions vs. Andere</h3>
            <div className="space-y-4">
              {[
                { feature: 'Swiss QR-Rechnungen', inat: true, andere: 'Teilweise' },
                { feature: 'Lokale Datenspeicherung', inat: true, andere: false },
                { feature: 'Einmalzahlung möglich', inat: true, andere: false },
                { feature: 'Unbegrenzte Rechnungen', inat: true, andere: 'Limitiert' },
                { feature: 'Mehrere Lagertypen', inat: '4 Typen', andere: '1 Typ' },
                { feature: 'Outlook Integration', inat: true, andere: 'Aufpreis' },
                { feature: 'Automatische Updates', inat: true, andere: true },
                { feature: 'Schweizer Support', inat: true, andere: 'Ausland' },
              ].map((row, i) => (
                <div key={i} className="grid grid-cols-3 gap-4 py-3 border-b border-gray-700 last:border-0">
                  <div className="text-gray-300 text-sm">{row.feature}</div>
                  <div className="text-center">
                    {row.inat === true ? (
                      <span className="text-green-400">✓</span>
                    ) : (
                      <span className="text-green-400 text-sm">{row.inat}</span>
                    )}
                  </div>
                  <div className="text-center">
                    {row.andere === true ? (
                      <span className="text-gray-500">✓</span>
                    ) : row.andere === false ? (
                      <span className="text-red-400">✗</span>
                    ) : (
                      <span className="text-gray-500 text-sm">{row.andere}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-3 gap-4 mt-4 text-center text-xs text-gray-500">
              <div></div>
              <div>INAT Solutions</div>
              <div>Andere Software</div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
