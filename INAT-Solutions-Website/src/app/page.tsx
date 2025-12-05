'use client'

import Navbar from '@/components/Navbar'
import Hero from '@/components/Hero'
import Features from '@/components/Features'
import Showcase from '@/components/Showcase'
import Benefits from '@/components/Benefits'
import Pricing from '@/components/Pricing'
import Download from '@/components/Download'
import Contact from '@/components/Contact'
import Footer from '@/components/Footer'

export default function Home() {
  return (
    <main className="min-h-screen bg-white">
      <Navbar />
      <Hero />
      <Features />
      <Showcase />
      <Benefits />
      <Pricing />
      <Download />
      <Contact />
      <Footer />
    </main>
  )
}
