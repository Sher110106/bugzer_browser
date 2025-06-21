'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { TextGenerateEffect } from '@/components/ui/aceternity/text-generate-effect'
import { BackgroundBeams } from '@/components/ui/aceternity/background-beams'
import { SparklesCore } from '@/components/ui/aceternity/sparkles'
import Link from 'next/link'

export default function Hero() {
  const [isHovered, setIsHovered] = useState(false)

  return (
    <section className="relative flex flex-col items-center justify-center min-h-screen text-center px-4 overflow-hidden bg-black">
      <BackgroundBeams className="z-0" />
      <div className="absolute inset-0 w-full h-full z-10">
        <SparklesCore
          id="tsparticlesfullpage"
          background="transparent"
          minSize={0.6}
          maxSize={1.4}
          particleDensity={30}
          className="w-full h-full"
          particleColor="#FFFFFF"
        />
      </div>
      <motion.div
        className="z-20 relative"
        initial={{ opacity: 0, y: -50 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <h1 className="text-5xl md:text-7xl font-extrabold mb-6 bg-clip-text text-transparent bg-gradient-to-r from-blue-500 to-purple-500 leading-tight py-2">
          Bugzer
        </h1>
        <h2 className="text-2xl md:text-3xl font-bold mb-4 text-blue-300">
          Automate Web Testing with Bugzer AI
        </h2>
      </motion.div>
      <motion.p 
        className="text-xl md:text-2xl mb-8 max-w-3xl z-10 text-gray-300"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2, duration: 0.5 }}
      >
        Bugzer uses intelligent AI agents to simulate real user interactions, identify issues, and analyze performance, so you can release updates with confidence.
      </motion.p>
      <motion.div
        className="z-10 flex flex-col sm:flex-row gap-4 items-center"
        initial={{ opacity: 0, y: 50 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4, duration: 0.5 }}
      >
        <Button 
          size="lg" 
          className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white text-lg px-8 py-4 rounded-full transition-all duration-300 transform hover:scale-105 shadow-lg hover:shadow-blue-500/20"
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
        >
          Get Started Free
        </Button>
        <Link 
          href="#how-it-works" 
          className="text-blue-400 hover:text-blue-300 font-medium flex items-center transition-colors duration-300"
        >
          <span>Watch Demo</span>
          <svg className="w-5 h-5 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </Link>
      </motion.div>

      <motion.div
        className="z-10 mt-16 max-w-3xl mx-auto bg-gray-900/50 backdrop-blur-sm rounded-xl p-6 border border-gray-800/50"
        initial={{ opacity: 0, y: 50 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6, duration: 0.5 }}
      >
        
      </motion.div>
    </section>
  )
}

