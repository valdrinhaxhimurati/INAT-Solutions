'use client'

import { motion } from 'framer-motion'
import { useInView } from 'framer-motion'
import { useRef, useState } from 'react'

const plans = [
  {
    name: 'Testversion',
    price: '0',
    period: '30 Tage',
    description: 'Voller Zugang zum Kennenlernen',
    features: [
      'Alle Funktionen freigeschaltet',
      '30 Tage kostenlos testen',
      'Keine Kreditkarte nötig',
      'Lokale Datenspeicherung',
      'Unbegrenzte Rechnungen',
    ],
    cta: 'Kostenlos starten',
    popular: false,
    color: 'border-gray-200',
    icon: '🎁',
  },
  {
    name: 'Professional',
    price: '8',
    period: 'pro Monat',
    description: 'Für Einzelunternehmer & kleine Betriebe',
    features: [
      'Alle Module inklusive',
      '1 Benutzer',
      'E-Mail Support',
      'Automatische Updates',
      'Swiss QR-Rechnungen',
      '4 Lagertypen',
      'Outlook Integration',
      'Buchhaltung & Kalender',
    ],
    cta: 'Plan wählen',
    popular: true,
    color: 'border-primary',
    icon: '⭐',
    yearlyPrice: '79',
  },
  {
    name: 'Enterprise',
    price: '14',
    period: 'pro Monat',
    description: 'Für Teams & wachsende Unternehmen',
    features: [
      'Alles aus Professional',
      'Unbegrenzte Benutzer',
      'Prioritäts-Support',
      'Telefon-Support',
      'Individuelle Anpassungen',
      'Daten-Export für Treuhänder',
      'Onboarding-Unterstützung',
      'Mehrere Firmenprofile',
    ],
    cta: 'Plan wählen',
    popular: false,
    color: 'border-secondary',
    icon: '🏢',
    yearlyPrice: '139',
  },
]

function PricingCard({ plan, index, isYearly }: { plan: typeof plans[0]; index: number; isYearly: boolean }) {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: '-50px' })
  const displayPrice = isYearly && plan.yearlyPrice ? plan.yearlyPrice : plan.price

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 50 }}
      animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 50 }}
      transition={{ duration: 0.5, delay: index * 0.15 }}
      className={`relative bg-white rounded-2xl p-8 shadow-sm hover:shadow-xl transition-all duration-300 border-2 ${plan.color} ${
        plan.popular ? 'scale-105 shadow-lg' : ''
      }`}
    >
      {plan.popular && (
        <div className="absolute -top-4 left-1/2 -translate-x-1/2">
          <span className="bg-gradient-to-r from-primary to-secondary text-white text-sm font-semibold px-4 py-1 rounded-full">
            Empfohlen
          </span>
        </div>
      )}

      <div className="text-center mb-6">
        <span className="text-3xl mb-3 block">{plan.icon}</span>
        <h3 className="text-xl font-bold text-gray-900 mb-2">{plan.name}</h3>
        <p className="text-gray-500 text-sm">{plan.description}</p>
      </div>

      <div className="text-center mb-6">
        <div className="flex items-baseline justify-center">
          <span className="text-xl font-bold text-gray-400">CHF</span>
          <span className="text-5xl font-bold text-gray-900 mx-1">{displayPrice}</span>
        </div>
        <span className="text-gray-500">{isYearly && plan.yearlyPrice ? 'pro Jahr' : plan.period}</span>
        {isYearly && plan.yearlyPrice && (
          <div className="mt-1">
            <span className="text-sm text-green-600 font-medium">
              Spare {Math.round((1 - parseInt(plan.yearlyPrice) / (parseInt(plan.price) * 12)) * 100)}%
            </span>
          </div>
        )}
      </div>

      <ul className="space-y-3 mb-8">
        {plan.features.map((feature) => (
          <li key={feature} className="flex items-start text-gray-600 text-sm">
            <svg className="w-5 h-5 text-green-500 mr-3 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            {feature}
          </li>
        ))}
      </ul>

      <motion.a
        href="#download"
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        className={`block w-full text-center py-3 rounded-xl font-semibold transition-all ${
          plan.popular
            ? 'bg-gradient-to-r from-primary to-secondary text-white hover:opacity-90'
            : 'bg-gray-100 text-gray-900 hover:bg-gray-200'
        }`}
      >
        {plan.cta}
      </motion.a>
    </motion.div>
  )
}

export default function Pricing() {
  const [isYearly, setIsYearly] = useState(false)
  const headerRef = useRef(null)
  const isHeaderInView = useInView(headerRef, { once: true })

  return (
    <section id="pricing" className="py-24 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <motion.div
          ref={headerRef}
          initial={{ opacity: 0, y: 30 }}
          animate={isHeaderInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
          transition={{ duration: 0.6 }}
          className="text-center mb-12"
        >
          <span className="inline-block bg-primary/10 text-primary font-semibold text-sm uppercase tracking-wider px-4 py-2 rounded-full mb-4">
            Preise
          </span>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 mb-6">
            Faire Preise, keine Überraschungen
          </h2>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Starten Sie kostenlos und upgraden Sie, wenn Sie bereit sind. 
            Alle Preise in Schweizer Franken, inkl. MWST.
          </p>
        </motion.div>

        {/* Billing Toggle */}
        <div className="flex justify-center items-center gap-4 mb-12">
          <span className={`text-sm font-medium ${!isYearly ? 'text-gray-900' : 'text-gray-500'}`}>
            Monatlich
          </span>
          <button
            onClick={() => setIsYearly(!isYearly)}
            className={`relative w-14 h-7 rounded-full transition-colors ${
              isYearly ? 'bg-primary' : 'bg-gray-300'
            }`}
          >
            <span
              className={`absolute top-1 left-1 w-5 h-5 bg-white rounded-full transition-transform ${
                isYearly ? 'translate-x-7' : ''
              }`}
            />
          </button>
          <span className={`text-sm font-medium ${isYearly ? 'text-gray-900' : 'text-gray-500'}`}>
            Jährlich
            <span className="ml-1 text-green-600 text-xs font-bold">-17%</span>
          </span>
        </div>

        {/* Pricing Cards */}
        <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto mb-16">
          {plans.map((plan, index) => (
            <PricingCard key={plan.name} plan={plan} index={index} isYearly={isYearly} />
          ))}
        </div>

        {/* Guarantee Banner */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="bg-white rounded-2xl p-8 shadow-sm border border-gray-100"
        >
          <div className="grid md:grid-cols-3 gap-8">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center flex-shrink-0">
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <div>
                <h4 className="font-semibold text-gray-900 mb-1">30-Tage Geld-zurück</h4>
                <p className="text-sm text-gray-500">Nicht zufrieden? Volle Rückerstattung, keine Fragen.</p>
              </div>
            </div>
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center flex-shrink-0">
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </div>
              <div>
                <h4 className="font-semibold text-gray-900 mb-1">Sichere Zahlung</h4>
                <p className="text-sm text-gray-500">Zahlung via Twint, Kreditkarte oder Rechnung.</p>
              </div>
            </div>
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center flex-shrink-0">
                <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <div>
                <h4 className="font-semibold text-gray-900 mb-1">Jederzeit kündbar</h4>
                <p className="text-sm text-gray-500">Keine Mindestlaufzeit, monatlich kündbar.</p>
              </div>
            </div>
          </div>
        </motion.div>

        {/* FAQ Teaser */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="text-center mt-12"
        >
          <p className="text-gray-600">
            Haben Sie Fragen zu den Preisen?{' '}
            <a href="#contact" className="text-primary font-semibold hover:text-secondary">
              Kontaktieren Sie uns →
            </a>
          </p>
        </motion.div>
      </div>
    </section>
  )
}
