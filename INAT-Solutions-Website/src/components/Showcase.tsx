'use client'

import { motion } from 'framer-motion'
import { useState } from 'react'

const screens = [
  {
    id: 'dashboard',
    title: 'Dashboard',
    icon: '📊',
    description: 'Ihr täglicher Überblick über alle wichtigen Geschäftszahlen',
    preview: (
      <div className="bg-gray-100 p-6 min-h-[400px]">
        {/* Stats Row */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-lg p-4 shadow-sm">
            <div className="text-xs text-gray-500 mb-1">Umsatz (Monat)</div>
            <div className="text-xl font-bold text-gray-800">CHF 24&apos;850</div>
            <div className="text-xs text-green-600 mt-1">↑ 12% zum Vormonat</div>
          </div>
          <div className="bg-white rounded-lg p-4 shadow-sm">
            <div className="text-xs text-gray-500 mb-1">Offene Rechnungen</div>
            <div className="text-xl font-bold text-orange-600">8</div>
            <div className="text-xs text-gray-400 mt-1">Total CHF 3&apos;240</div>
          </div>
          <div className="bg-white rounded-lg p-4 shadow-sm">
            <div className="text-xs text-gray-500 mb-1">Neue Kunden</div>
            <div className="text-xl font-bold text-primary">12</div>
            <div className="text-xs text-green-600 mt-1">↑ 3 diese Woche</div>
          </div>
          <div className="bg-white rounded-lg p-4 shadow-sm">
            <div className="text-xs text-gray-500 mb-1">Lagerwarnungen</div>
            <div className="text-xl font-bold text-red-500">5</div>
            <div className="text-xs text-gray-400 mt-1">Artikel nachbestellen</div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-6">
          {/* Recent Invoices */}
          <div className="bg-white rounded-lg shadow-sm p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-800">Letzte Rechnungen</h3>
              <button className="text-xs text-primary hover:underline">Alle anzeigen</button>
            </div>
            <div className="space-y-3">
              {[
                { kunde: 'Müller AG', betrag: '1\'250.00', status: 'bezahlt', date: 'Heute' },
                { kunde: 'Swiss Tech GmbH', betrag: '3\'480.50', status: 'offen', date: 'Gestern' },
                { kunde: 'Garage Meier', betrag: '890.00', status: 'bezahlt', date: '28.11.' },
              ].map((inv, i) => (
                <div key={i} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                  <div className="flex items-center gap-3">
                    <div className={`w-2 h-2 rounded-full ${inv.status === 'bezahlt' ? 'bg-green-500' : 'bg-orange-500'}`} />
                    <div>
                      <div className="text-sm font-medium text-gray-800">{inv.kunde}</div>
                      <div className="text-xs text-gray-500">{inv.date}</div>
                    </div>
                  </div>
                  <div className="text-sm font-semibold text-gray-900">CHF {inv.betrag}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Today's Tasks */}
          <div className="bg-white rounded-lg shadow-sm p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-800">Aufträge heute</h3>
              <button className="text-xs text-primary hover:underline">Zum Kalender</button>
            </div>
            <div className="space-y-3">
              {[
                { time: '09:00', title: 'Reifenwechsel BMW X5', client: 'Hr. Schmidt', type: 'Werkstatt' },
                { time: '11:30', title: 'Service VW Golf', client: 'Fr. Weber', type: 'Service' },
                { time: '14:00', title: 'Beratungstermin', client: 'Firma Huber', type: 'Büro' },
              ].map((task, i) => (
                <div key={i} className="flex gap-3 p-2 hover:bg-gray-50 rounded-lg transition-colors">
                  <div className="text-sm font-bold text-gray-400 w-12">{task.time}</div>
                  <div>
                    <div className="text-sm font-medium text-gray-800">{task.title}</div>
                    <div className="text-xs text-gray-500">{task.client} • {task.type}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    )
  },
  {
    id: 'rechnungen',
    title: 'Rechnungen',
    icon: '📄',
    description: 'Erstellen Sie professionelle Swiss QR-Rechnungen in Sekunden',
    preview: (
      <div className="bg-gray-100 p-6 min-h-[400px]">
        {/* Toolbar */}
        <div className="bg-white rounded-lg shadow-sm p-3 mb-4 flex items-center gap-3">
          <button className="bg-primary text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Neue Rechnung
          </button>
          <div className="flex-1" />
          <div className="flex items-center gap-2 bg-gray-100 rounded-lg px-3 py-2">
            <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <span className="text-sm text-gray-400">Suchen...</span>
          </div>
        </div>

        {/* Table */}
        <div className="bg-white rounded-lg shadow-sm overflow-hidden">
          <div className="grid grid-cols-6 gap-4 p-3 bg-gray-50 border-b text-xs font-medium text-gray-500">
            <div>Nummer</div>
            <div>Kunde</div>
            <div>Datum</div>
            <div>Betrag</div>
            <div>Status</div>
            <div>Aktionen</div>
          </div>
          {[
            { nr: '2024-0851', kunde: 'Müller AG', datum: '28.11.2024', betrag: '1\'250.00', status: 'bezahlt' },
            { nr: '2024-0850', kunde: 'Swiss Tech GmbH', datum: '27.11.2024', betrag: '3\'480.50', status: 'offen' },
            { nr: '2024-0849', kunde: 'Garage Huber', datum: '25.11.2024', betrag: '890.00', status: 'bezahlt' },
            { nr: '2024-0848', kunde: 'Restaurant Sonne', datum: '24.11.2024', betrag: '2\'150.00', status: 'überfällig' },
            { nr: '2024-0847', kunde: 'Elektro Weber', datum: '22.11.2024', betrag: '675.50', status: 'bezahlt' },
          ].map((row, i) => (
            <div key={i} className="grid grid-cols-6 gap-4 p-3 border-b border-gray-50 text-sm hover:bg-gray-50">
              <div className="font-medium text-primary">{row.nr}</div>
              <div className="text-gray-700">{row.kunde}</div>
              <div className="text-gray-500">{row.datum}</div>
              <div className="font-medium">CHF {row.betrag}</div>
              <div>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                  row.status === 'bezahlt' ? 'bg-green-100 text-green-700' :
                  row.status === 'offen' ? 'bg-orange-100 text-orange-700' :
                  'bg-red-100 text-red-700'
                }`}>
                  {row.status}
                </span>
              </div>
              <div className="flex gap-2">
                <button className="text-gray-400 hover:text-primary">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                </button>
                <button className="text-gray-400 hover:text-primary">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    ),
  },
  {
    id: 'kunden',
    title: 'Kunden',
    icon: '👥',
    description: 'Verwalten Sie alle Ihre Kundenbeziehungen an einem Ort',
    preview: (
      <div className="bg-gray-100 p-6 min-h-[400px]">
        <div className="grid grid-cols-3 gap-4">
          {/* Left: Customer List */}
          <div className="col-span-1 bg-white rounded-lg shadow-sm p-4">
            <div className="mb-4">
              <div className="bg-gray-100 rounded-lg px-3 py-2 flex items-center gap-2">
                <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <span className="text-sm text-gray-400">Kunde suchen...</span>
              </div>
            </div>
            <div className="space-y-2">
              {['Müller AG', 'Swiss Tech GmbH', 'Garage Huber', 'Elektro Weber'].map((name, i) => (
                <div key={i} className={`p-3 rounded-lg cursor-pointer ${i === 0 ? 'bg-primary/10 border border-primary/20' : 'hover:bg-gray-50'}`}>
                  <div className="flex items-center gap-2">
                    <div className={`w-8 h-8 rounded-full ${i === 0 ? 'bg-primary' : 'bg-gray-200'} flex items-center justify-center`}>
                      <span className={`text-xs font-bold ${i === 0 ? 'text-white' : 'text-gray-500'}`}>
                        {name.slice(0, 2).toUpperCase()}
                      </span>
                    </div>
                    <span className="text-sm font-medium text-gray-800">{name}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Right: Customer Details */}
          <div className="col-span-2 bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-start justify-between mb-6">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 bg-primary rounded-xl flex items-center justify-center">
                  <span className="text-white text-xl font-bold">MA</span>
                </div>
                <div>
                  <h3 className="text-xl font-bold text-gray-800">Müller AG</h3>
                  <p className="text-gray-500">Industriestrasse 45, 8005 Zürich</p>
                </div>
              </div>
              <button className="bg-primary text-white px-4 py-2 rounded-lg text-sm">Bearbeiten</button>
            </div>

            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="text-2xl font-bold text-primary">18</div>
                <div className="text-sm text-gray-500">Rechnungen</div>
              </div>
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="text-2xl font-bold text-green-600">CHF 24&apos;850</div>
                <div className="text-sm text-gray-500">Umsatz gesamt</div>
              </div>
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="text-2xl font-bold text-orange-500">CHF 1&apos;250</div>
                <div className="text-sm text-gray-500">Offen</div>
              </div>
            </div>

            <div className="border-t pt-4">
              <div className="text-sm font-medium text-gray-700 mb-2">Kontakt</div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div className="text-gray-500">📧 info@mueller-ag.ch</div>
                <div className="text-gray-500">📞 044 123 45 67</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    ),
  },
  {
    id: 'kalender',
    title: 'Kalender',
    icon: '📅',
    description: 'Planen Sie Aufträge und Termine übersichtlich',
    preview: (
      <div className="bg-gray-100 p-6 min-h-[400px]">
        <div className="bg-white rounded-lg shadow-sm">
          {/* Calendar Header */}
          <div className="p-4 border-b flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button className="p-2 hover:bg-gray-100 rounded-lg">
                <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <span className="text-lg font-semibold text-gray-800">Dezember 2024</span>
              <button className="p-2 hover:bg-gray-100 rounded-lg">
                <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>
            <button className="bg-primary text-white px-4 py-2 rounded-lg text-sm">+ Neuer Termin</button>
          </div>

          {/* Days Header */}
          <div className="grid grid-cols-7 border-b">
            {['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'].map((day) => (
              <div key={day} className="p-3 text-center text-sm font-medium text-gray-500">{day}</div>
            ))}
          </div>

          {/* Calendar Grid */}
          <div className="grid grid-cols-7">
            {[...Array(35)].map((_, i) => {
              const day = i - 2
              const hasEvent = [3, 5, 12, 15, 19].includes(day)
              const isToday = day === 2
              return (
                <div key={i} className={`min-h-[60px] p-2 border-b border-r ${day < 1 || day > 31 ? 'bg-gray-50' : ''}`}>
                  {day >= 1 && day <= 31 && (
                    <>
                      <div className={`text-sm ${isToday ? 'bg-primary text-white w-6 h-6 rounded-full flex items-center justify-center' : 'text-gray-700'}`}>
                        {day}
                      </div>
                      {hasEvent && (
                        <div className="mt-1 text-xs bg-primary/10 text-primary p-1 rounded truncate">
                          {day === 3 ? 'Reifenwechsel' : day === 5 ? 'Service BMW' : day === 12 ? 'Inspektion' : day === 15 ? 'Öl wechsel' : 'Termin'}
                        </div>
                      )}
                    </>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      </div>
    ),
  },
  {
    id: 'lager',
    title: 'Lager',
    icon: '📦',
    description: 'Material-, Reifen-, Artikel- und Dienstleistungslager',
    preview: (
      <div className="bg-gray-100 p-6 min-h-[400px]">
        {/* Tab Navigation */}
        <div className="bg-white rounded-lg shadow-sm mb-4">
          <div className="flex border-b">
            {['Materiallager', 'Reifenlager', 'Artikellager', 'Dienstleistungen'].map((tab, i) => (
              <button key={tab} className={`flex-1 px-4 py-3 text-sm font-medium ${i === 1 ? 'text-primary border-b-2 border-primary' : 'text-gray-500 hover:text-gray-700'}`}>
                {tab}
              </button>
            ))}
          </div>
        </div>

        {/* Inventory Table */}
        <div className="bg-white rounded-lg shadow-sm overflow-hidden">
          <div className="p-4 border-b flex items-center justify-between">
            <span className="font-semibold text-gray-800">Reifenlager (423 Artikel)</span>
            <button className="bg-primary text-white px-4 py-2 rounded-lg text-sm">+ Hinzufügen</button>
          </div>
          <div className="divide-y">
            {[
              { name: 'Continental WinterContact TS 870', groesse: '205/55 R16', menge: 24, min: 10, preis: '145.00' },
              { name: 'Michelin Pilot Sport 5', groesse: '225/45 R17', menge: 3, min: 8, preis: '189.00' },
              { name: 'Pirelli P Zero', groesse: '235/40 R18', menge: 16, min: 6, preis: '215.00' },
              { name: 'Bridgestone Blizzak LM005', groesse: '195/65 R15', menge: 32, min: 12, preis: '125.00' },
            ].map((item, i) => (
              <div key={i} className="p-4 flex items-center justify-between hover:bg-gray-50">
                <div className="flex-1">
                  <div className="font-medium text-gray-800">{item.name}</div>
                  <div className="text-sm text-gray-500">{item.groesse}</div>
                </div>
                <div className="w-24 text-center">
                  <div className={`font-bold ${item.menge < item.min ? 'text-red-600' : 'text-gray-800'}`}>
                    {item.menge} Stk
                  </div>
                  {item.menge < item.min && (
                    <div className="text-xs text-red-500">Unter Minimum</div>
                  )}
                </div>
                <div className="w-24 text-right font-medium">CHF {item.preis}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    ),
  },
  {
    id: 'buchhaltung',
    title: 'Buchhaltung',
    icon: '💰',
    description: 'Einfache Einnahmen- und Ausgabenrechnung',
    preview: (
      <div className="bg-gray-100 p-6 min-h-[400px]">
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-white rounded-lg p-4 shadow-sm border-l-4 border-green-500">
            <div className="text-sm text-gray-500">Einnahmen (Nov)</div>
            <div className="text-2xl font-bold text-green-600">CHF 24&apos;850.00</div>
          </div>
          <div className="bg-white rounded-lg p-4 shadow-sm border-l-4 border-red-500">
            <div className="text-sm text-gray-500">Ausgaben (Nov)</div>
            <div className="text-2xl font-bold text-red-600">CHF 8&apos;320.00</div>
          </div>
          <div className="bg-white rounded-lg p-4 shadow-sm border-l-4 border-primary">
            <div className="text-sm text-gray-500">Gewinn (Nov)</div>
            <div className="text-2xl font-bold text-primary">CHF 16&apos;530.00</div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm overflow-hidden">
          <div className="p-4 border-b flex items-center justify-between">
            <h3 className="font-semibold text-gray-800">Buchungen</h3>
            <div className="flex gap-2">
              <button className="text-sm text-gray-600 hover:text-primary">Exportieren</button>
              <button className="bg-primary text-white px-3 py-1.5 rounded text-sm">+ Buchung</button>
            </div>
          </div>
          <div className="divide-y">
            {[
              { date: '28.11.2024', text: 'Rechnung #2024-0851 (Müller AG)', cat: 'Einnahmen', amount: '+ 1\'250.00', type: 'in' },
              { date: '27.11.2024', text: 'Miete Werkstatt Dezember', cat: 'Miete', amount: '- 2\'400.00', type: 'out' },
              { date: '26.11.2024', text: 'Einkauf Ersatzteile', cat: 'Material', amount: '- 450.00', type: 'out' },
              { date: '25.11.2024', text: 'Rechnung #2024-0849 (Garage Huber)', cat: 'Einnahmen', amount: '+ 890.00', type: 'in' },
            ].map((item, i) => (
              <div key={i} className="p-3 flex items-center justify-between hover:bg-gray-50">
                <div className="flex items-center gap-4">
                  <div className="text-sm text-gray-500 w-24">{item.date}</div>
                  <div>
                    <div className="text-sm font-medium text-gray-800">{item.text}</div>
                    <div className="text-xs text-gray-500">{item.cat}</div>
                  </div>
                </div>
                <div className={`font-mono font-medium ${item.type === 'in' ? 'text-green-600' : 'text-red-600'}`}>
                  {item.amount}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  },
  {
    id: 'einstellungen',
    title: 'Einstellungen',
    icon: '⚙️',
    description: 'Passen Sie die App an Ihre Bedürfnisse an',
    preview: (
      <div className="bg-gray-100 p-6 min-h-[400px]">
        <div className="grid grid-cols-3 gap-6">
          <div className="col-span-1 space-y-2">
            {['Allgemein', 'Firma', 'Rechnungen', 'Backup', 'Benutzer', 'Lizenz'].map((item, i) => (
              <div key={i} className={`p-3 rounded-lg cursor-pointer ${i === 0 ? 'bg-white shadow-sm text-primary font-medium' : 'text-gray-600 hover:bg-white/50'}`}>
                {item}
              </div>
            ))}
          </div>
          <div className="col-span-2 bg-white rounded-lg shadow-sm p-6">
            <h3 className="font-bold text-gray-800 mb-6">Allgemeine Einstellungen</h3>
            
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Sprache</label>
                <select className="w-full border-gray-300 rounded-lg shadow-sm p-2 border">
                  <option>Deutsch</option>
                  <option>Français</option>
                  <option>English</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Design</label>
                <div className="flex gap-4">
                  <div className="border-2 border-primary rounded-lg p-2 cursor-pointer">
                    <div className="w-20 h-12 bg-gray-100 rounded mb-1"></div>
                    <div className="text-xs text-center font-medium text-primary">Hell</div>
                  </div>
                  <div className="border border-gray-200 rounded-lg p-2 cursor-pointer opacity-60">
                    <div className="w-20 h-12 bg-gray-800 rounded mb-1"></div>
                    <div className="text-xs text-center font-medium">Dunkel</div>
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between pt-4 border-t">
                <div>
                  <div className="font-medium text-gray-800">Automatische Updates</div>
                  <div className="text-xs text-gray-500">Nach Updates beim Start suchen</div>
                </div>
                <div className="w-10 h-6 bg-primary rounded-full relative cursor-pointer">
                  <div className="absolute right-1 top-1 w-4 h-4 bg-white rounded-full"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }
]

export default function Showcase() {
  const [activeScreen, setActiveScreen] = useState('dashboard')
  const currentScreen = screens.find(s => s.id === activeScreen) || screens[0]

  return (
    <section id="showcase" className="py-24 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <span className="inline-block bg-primary/10 text-primary font-semibold text-sm uppercase tracking-wider px-4 py-2 rounded-full mb-4">
            Live-Vorschau
          </span>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 mb-6">
            So sieht INAT Solutions aus
          </h2>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Entdecken Sie die intuitive Benutzeroberfläche – modern, übersichtlich und effizient.
          </p>
        </motion.div>

        {/* Tab Navigation (Mobile/Tablet) */}
        <div className="flex md:hidden justify-center mb-8 overflow-x-auto pb-4">
          <div className="inline-flex bg-white rounded-xl shadow-sm p-1">
            {screens.map((screen) => (
              <button
                key={screen.id}
                onClick={() => setActiveScreen(screen.id)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
                  activeScreen === screen.id
                    ? 'bg-primary text-white shadow-md'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                {screen.title}
              </button>
            ))}
          </div>
        </div>

        {/* App Window */}
        <motion.div
          key={activeScreen}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="max-w-6xl mx-auto"
        >
          <div className="bg-gray-900 rounded-2xl shadow-2xl overflow-hidden border border-gray-800">
            {/* Window Header */}
            <div className="bg-gray-800 px-4 py-3 flex items-center gap-2 border-b border-gray-700">
              <div className="w-3 h-3 rounded-full bg-red-500" />
              <div className="w-3 h-3 rounded-full bg-yellow-500" />
              <div className="w-3 h-3 rounded-full bg-green-500" />
              <span className="ml-4 text-gray-400 text-sm font-medium">INAT Solutions - {currentScreen.title}</span>
            </div>

            {/* Sidebar + Content */}
            <div className="flex min-h-[600px]">
              {/* Sidebar (Desktop) */}
              <div className="w-64 bg-gray-800 p-4 hidden md:flex flex-col border-r border-gray-700">
                <div className="mb-8 px-2">
                  <div className="text-white font-bold text-xl tracking-tight">INAT Solutions</div>
                  <div className="text-gray-500 text-xs">Business Software v0.9.2</div>
                </div>
                
                <div className="space-y-1 flex-1">
                  {screens.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => setActiveScreen(item.id)}
                      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                        activeScreen === item.id
                          ? 'bg-primary text-white shadow-lg shadow-primary/20'
                          : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                      }`}
                    >
                      <span className="text-lg">{item.icon}</span>
                      <span>{item.title}</span>
                      {activeScreen === item.id && (
                        <motion.div
                          layoutId="activeIndicator"
                          className="ml-auto w-1.5 h-1.5 rounded-full bg-white"
                        />
                      )}
                    </button>
                  ))}
                </div>

                <div className="mt-auto pt-4 border-t border-gray-700">
                  <div className="flex items-center gap-3 px-3 py-2">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white text-xs font-bold">
                      VH
                    </div>
                    <div className="text-sm">
                      <div className="text-white font-medium">Valdrin H.</div>
                      <div className="text-gray-500 text-xs">Administrator</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Main Content */}
              <div className="flex-1 bg-gray-100 flex flex-col">
                {/* Top Bar inside App */}
                <div className="bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center">
                  <h2 className="text-xl font-bold text-gray-800">{currentScreen.title}</h2>
                  <div className="flex items-center gap-4">
                    <button className="p-2 text-gray-400 hover:text-gray-600 relative">
                      <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full border-2 border-white"></span>
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                      </svg>
                    </button>
                    <div className="h-8 w-px bg-gray-200"></div>
                    <div className="text-sm text-gray-500">{new Date().toLocaleDateString('de-CH')}</div>
                  </div>
                </div>

                {/* Screen Content */}
                <div className="flex-1 overflow-y-auto">
                  {currentScreen.preview}
                </div>
              </div>
            </div>
          </div>

          {/* Description */}
          <div className="text-center mt-8">
            <p className="text-lg text-gray-600">{currentScreen.description}</p>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
