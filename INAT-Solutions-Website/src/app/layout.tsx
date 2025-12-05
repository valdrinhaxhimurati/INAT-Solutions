import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'INAT Solutions - Business Management Software',
  description: 'Die All-in-One Lösung für Ihr Unternehmen. Rechnungen, Kunden, Lager, Buchhaltung - alles in einer App.',
  keywords: ['Business Software', 'Rechnungen', 'Buchhaltung', 'Lagerverwaltung', 'Swiss QR', 'KMU'],
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="de">
      <body className="antialiased">{children}</body>
    </html>
  )
}
