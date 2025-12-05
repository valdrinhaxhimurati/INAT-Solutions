'use client'

import { motion } from 'framer-motion'
import { useInView } from 'framer-motion'
import { useRef } from 'react'

export default function Download() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true })

  return (
    <section id="download" className="py-24 bg-gradient-to-br from-primary via-primary-600 to-secondary relative overflow-hidden">
      {/* Background Pattern */}
      <div className="absolute inset-0 opacity-10">
        <div className="absolute top-10 right-10 w-64 h-64 bg-white rounded-full blur-3xl" />
        <div className="absolute bottom-10 left-10 w-96 h-96 bg-white rounded-full blur-3xl" />
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
          transition={{ duration: 0.6 }}
          className="text-center"
        >
          <span className="text-white/70 font-semibold text-sm uppercase tracking-wider">Download</span>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mt-2 mb-4">
            Jetzt kostenlos herunterladen
          </h2>
          <p className="text-xl text-white/80 max-w-2xl mx-auto mb-12">
            Laden Sie INAT Solutions herunter und starten Sie Ihre 30-tägige kostenlose Testphase. 
            Keine Kreditkarte erforderlich.
          </p>

          {/* Download Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-16">
            <motion.a
              href="https://github.com/valdrinhaxhimurati/INAT-Solutions/releases/latest"
              target="_blank"
              rel="noopener noreferrer"
              whileHover={{ scale: 1.05, y: -2 }}
              whileTap={{ scale: 0.95 }}
              className="bg-white text-primary hover:bg-gray-100 px-8 py-4 rounded-xl font-semibold text-lg shadow-xl transition-all inline-flex items-center justify-center gap-3"
            >
              <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 24 24">
                <path d="M0 3.449L9.75 2.1v9.451H0m10.949-9.602L24 0v11.4H10.949M0 12.6h9.75v9.451L0 20.699M10.949 12.6H24V24l-12.9-1.801"/>
              </svg>
              <div className="text-left">
                <div className="text-xs text-gray-500">Download für</div>
                <div className="font-bold">Windows</div>
              </div>
            </motion.a>
          </div>

          {/* System Requirements */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={isInView ? { opacity: 1 } : { opacity: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-white/10 backdrop-blur-sm rounded-2xl p-8 max-w-3xl mx-auto"
          >
            <h3 className="text-white font-semibold mb-6">Systemanforderungen</h3>
            <div className="grid sm:grid-cols-3 gap-6 text-left">
              <div>
                <div className="text-white/60 text-sm mb-1">Betriebssystem</div>
                <div className="text-white font-medium">Windows 10/11</div>
              </div>
              <div>
                <div className="text-white/60 text-sm mb-1">Speicher</div>
                <div className="text-white font-medium">4 GB RAM</div>
              </div>
              <div>
                <div className="text-white/60 text-sm mb-1">Festplatte</div>
                <div className="text-white font-medium">200 MB frei</div>
              </div>
            </div>
          </motion.div>

          {/* Version Info */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={isInView ? { opacity: 1 } : { opacity: 0 }}
            transition={{ delay: 0.5 }}
            className="mt-8 text-white/60 text-sm"
          >
            Aktuelle Version: 0.9.2.0 • Zuletzt aktualisiert: Dezember 2025
          </motion.div>
        </motion.div>
      </div>
    </section>
  )
}
