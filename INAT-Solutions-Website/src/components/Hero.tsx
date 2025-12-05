'use client'

import { motion } from 'framer-motion'

export default function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden bg-gradient-to-br from-primary via-primary-600 to-secondary">
      {/* Background Pattern */}
      <div className="absolute inset-0 opacity-10">
        <div className="absolute top-20 left-10 w-72 h-72 bg-white rounded-full blur-3xl" />
        <div className="absolute bottom-20 right-10 w-96 h-96 bg-white rounded-full blur-3xl" />
        <div className="absolute top-1/2 left-1/2 w-64 h-64 bg-white rounded-full blur-3xl" />
      </div>

      {/* Grid Pattern Overlay */}
      <div className="absolute inset-0 opacity-5" style={{
        backgroundImage: 'radial-gradient(circle at 1px 1px, white 1px, transparent 0)',
        backgroundSize: '40px 40px'
      }} />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-32 relative z-10">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Text Content */}
          <motion.div
            initial={{ opacity: 0, x: -50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8 }}
          >
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="inline-flex items-center gap-2 bg-white/20 backdrop-blur-sm rounded-full px-4 py-2 mb-6"
            >
              <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
              <span className="text-white/90 text-sm font-medium">
                Version 0.9.2.0 • Jetzt mit Live-PDF-Vorschau
              </span>
            </motion.div>

            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-white leading-tight mb-6">
              Business-Software{' '}
              <span className="bg-gradient-to-r from-white to-blue-200 bg-clip-text text-transparent">
                die mitwächst
              </span>
            </h1>

            <p className="text-xl text-white/80 mb-8 leading-relaxed">
              Von der Rechnung bis zur Buchhaltung, vom Kundenkontakt bis zum Lager – 
              INAT Solutions vereint alles in einer eleganten Desktop-App. 
              Speziell entwickelt für Schweizer KMU.
            </p>

            {/* Feature Pills */}
            <div className="flex flex-wrap gap-3 mb-8">
              {['Swiss QR-Rechnungen', '12 Rechnungsstile', 'Outlook-Sync', 'Auto-Updates'].map((feature) => (
                <span key={feature} className="bg-white/10 backdrop-blur-sm text-white/90 px-4 py-2 rounded-full text-sm font-medium">
                  ✓ {feature}
                </span>
              ))}
            </div>

            <div className="flex flex-col sm:flex-row gap-4">
              <motion.a
                href="#download"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="bg-white text-primary hover:bg-gray-100 px-8 py-4 rounded-full font-semibold text-lg shadow-xl transition-all inline-flex items-center justify-center"
              >
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                30 Tage kostenlos testen
              </motion.a>
              <motion.a
                href="#features"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="border-2 border-white/30 text-white hover:bg-white/10 px-8 py-4 rounded-full font-semibold text-lg transition-all inline-flex items-center justify-center"
              >
                Features entdecken
                <svg className="w-5 h-5 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </motion.a>
            </div>

            {/* Trust Badges */}
            <div className="mt-12 grid grid-cols-4 gap-6">
              <div className="text-center">
                <div className="text-3xl font-bold text-white">30</div>
                <div className="text-sm text-white/60">Tage gratis</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-white">12</div>
                <div className="text-sm text-white/60">Rechnungsstile</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-white">4</div>
                <div className="text-sm text-white/60">Lagertypen</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-white">∞</div>
                <div className="text-sm text-white/60">Rechnungen</div>
              </div>
            </div>
          </motion.div>

          {/* App Screenshots - Stacked */}
          <motion.div
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
            className="relative"
          >
            {/* Main App Window */}
            <div className="relative bg-gray-900 rounded-2xl shadow-2xl overflow-hidden border border-white/10 transform rotate-1 hover:rotate-0 transition-transform duration-500">
              {/* Window Header */}
              <div className="bg-gray-800 px-4 py-3 flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-red-500" />
                <div className="w-3 h-3 rounded-full bg-yellow-500" />
                <div className="w-3 h-3 rounded-full bg-green-500" />
                <span className="ml-4 text-gray-400 text-sm">INAT Solutions - Dashboard</span>
              </div>
              
              {/* Dashboard Content */}
              <div className="bg-gradient-to-br from-gray-100 to-gray-50 p-4">
                {/* Stats Row */}
                <div className="grid grid-cols-4 gap-3 mb-4">
                  <div className="bg-white rounded-xl p-3 shadow-sm">
                    <div className="text-xs text-gray-500 mb-1">Umsatz (Monat)</div>
                    <div className="text-lg font-bold text-gray-800">CHF 24&apos;850</div>
                    <div className="text-xs text-green-600">↑ 12%</div>
                  </div>
                  <div className="bg-white rounded-xl p-3 shadow-sm">
                    <div className="text-xs text-gray-500 mb-1">Offene Rechnungen</div>
                    <div className="text-lg font-bold text-orange-600">8</div>
                    <div className="text-xs text-gray-400">CHF 3&apos;240</div>
                  </div>
                  <div className="bg-white rounded-xl p-3 shadow-sm">
                    <div className="text-xs text-gray-500 mb-1">Kunden</div>
                    <div className="text-lg font-bold text-primary">156</div>
                    <div className="text-xs text-green-600">↑ 3 neu</div>
                  </div>
                  <div className="bg-white rounded-xl p-3 shadow-sm">
                    <div className="text-xs text-gray-500 mb-1">Lagerbestand</div>
                    <div className="text-lg font-bold text-gray-800">423</div>
                    <div className="text-xs text-red-500">5 niedrig</div>
                  </div>
                </div>

                {/* Two Column Layout */}
                <div className="grid grid-cols-2 gap-3">
                  {/* Recent Invoices */}
                  <div className="bg-white rounded-xl p-3 shadow-sm">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-sm font-semibold text-gray-800">Letzte Rechnungen</span>
                      <span className="text-xs text-primary cursor-pointer">Alle →</span>
                    </div>
                    <div className="space-y-2">
                      {[
                        { kunde: 'Müller AG', betrag: '1\'250.00', status: 'bezahlt' },
                        { kunde: 'Swiss Tech GmbH', betrag: '3\'480.50', status: 'offen' },
                        { kunde: 'Garage Meier', betrag: '890.00', status: 'bezahlt' },
                      ].map((inv, i) => (
                        <div key={i} className="flex items-center justify-between py-1.5 border-b border-gray-50">
                          <div className="flex items-center gap-2">
                            <div className={`w-2 h-2 rounded-full ${inv.status === 'bezahlt' ? 'bg-green-500' : 'bg-orange-500'}`} />
                            <span className="text-xs text-gray-700">{inv.kunde}</span>
                          </div>
                          <span className="text-xs font-medium text-gray-900">CHF {inv.betrag}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Upcoming Tasks */}
                  <div className="bg-white rounded-xl p-3 shadow-sm">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-sm font-semibold text-gray-800">Aufträge heute</span>
                      <span className="text-xs text-primary cursor-pointer">Kalender →</span>
                    </div>
                    <div className="space-y-2">
                      {[
                        { zeit: '09:00', titel: 'Reifenwechsel - BMW X5', kunde: 'Hr. Schmidt' },
                        { zeit: '11:30', titel: 'Service - VW Golf', kunde: 'Fr. Weber' },
                        { zeit: '14:00', titel: 'Inspektion - Audi A4', kunde: 'Firma Huber' },
                      ].map((task, i) => (
                        <div key={i} className="flex items-start gap-2 py-1.5 border-b border-gray-50">
                          <span className="text-xs text-primary font-medium">{task.zeit}</span>
                          <div>
                            <div className="text-xs text-gray-700">{task.titel}</div>
                            <div className="text-xs text-gray-400">{task.kunde}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Floating Invoice Preview */}
            <motion.div
              animate={{ y: [0, -8, 0] }}
              transition={{ duration: 4, repeat: Infinity }}
              className="absolute -top-8 -right-4 bg-white rounded-xl shadow-2xl p-3 w-48 transform rotate-3"
            >
              <div className="text-xs font-semibold text-gray-800 mb-2">Rechnung #2024-0847</div>
              <div className="border border-gray-200 rounded-lg p-2 mb-2">
                <div className="text-xs text-gray-500">Swiss QR-Code</div>
                <div className="grid grid-cols-3 gap-1 mt-1">
                  {[...Array(9)].map((_, i) => (
                    <div key={i} className="w-3 h-3 bg-gray-800 rounded-sm" />
                  ))}
                </div>
              </div>
              <div className="text-xs text-gray-600">Total: <span className="font-bold text-gray-900">CHF 1&apos;250.00</span></div>
            </motion.div>

            {/* Floating Customer Card */}
            <motion.div
              animate={{ y: [0, 10, 0] }}
              transition={{ duration: 5, repeat: Infinity }}
              className="absolute -bottom-4 -left-4 bg-white rounded-xl shadow-2xl p-3 w-44 transform -rotate-3"
            >
              <div className="flex items-center gap-2 mb-2">
                <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center">
                  <span className="text-white text-xs font-bold">MA</span>
                </div>
                <div>
                  <div className="text-xs font-semibold text-gray-800">Müller AG</div>
                  <div className="text-xs text-gray-500">Kunde seit 2022</div>
                </div>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-gray-500">12 Rechnungen</span>
                <span className="text-green-600 font-medium">CHF 18&apos;420</span>
              </div>
            </motion.div>
          </motion.div>
        </div>
      </div>

      {/* Scroll Indicator */}
      <motion.div
        animate={{ y: [0, 10, 0] }}
        transition={{ duration: 2, repeat: Infinity }}
        className="absolute bottom-8 left-1/2 -translate-x-1/2"
      >
        <a href="#features" className="text-white/50 hover:text-white transition-colors flex flex-col items-center gap-2">
          <span className="text-sm">Mehr erfahren</span>
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </a>
      </motion.div>
    </section>
  )
}
