import Hero from '@/components/Hero'
import Features from '@/components/Features'
import HowItWorks from '@/components/HowItWorks'
import CTA from '@/components/CTA'

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-gray-900 to-black text-white overflow-hidden">
      <Hero />
      <div id="features">
        <Features />
      </div>
      <HowItWorks />
      <CTA />
    </main>
  )
}

