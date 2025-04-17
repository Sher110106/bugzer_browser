'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { TextGenerateEffect } from '@/components/ui/aceternity/text-generate-effect'
import { BackgroundBeams } from '@/components/ui/aceternity/background-beams'
import { SparklesCore } from '@/components/ui/aceternity/sparkles'

export default function Hero() {
  const [isHovered, setIsHovered] = useState(false)

  return (
    <section className="relative flex flex-col items-center justify-center min-h-screen text-center px-4 overflow-hidden">
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
        <h1 className="text-6xl md:text-8xl font-extrabold mb-10 bg-clip-text text-transparent bg-gradient-to-r from-blue-500 to-purple-500 leading-normal py-2">
          Bugzer
        </h1>
      </motion.div>
      <motion.p 
        className="text-xl md:text-2xl mb-8 max-w-2xl z-10 text-gray-300"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2, duration: 0.5 }}
      >
        Simulate user interactions, analyze performance, and get actionable insights to improve your website.
      </motion.p>
      <motion.div
        className="z-10"
        initial={{ opacity: 0, y: 50 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4, duration: 0.5 }}
      >
        <Button 
          size="lg" 
          className="bg-blue-600 hover:bg-blue-700 text-white text-lg px-8 py-4 rounded-full transition-all duration-300 transform hover:scale-105"
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
        >
          {isHovered ? "Let's Optimize!" : "Get Started"}
        </Button>
      </motion.div>
    </section>
  )
}

