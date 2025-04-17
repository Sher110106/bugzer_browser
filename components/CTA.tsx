'use client'

import { useState, useRef } from 'react'
import { motion, useInView } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Spotlight } from '@/components/ui/aceternity/spotlight'
import { TextGenerateEffect } from '@/components/ui/aceternity/text-generate-effect'
import { BackgroundBeams } from '@/components/ui/aceternity/background-beams'
import { SparklesCore } from '@/components/ui/aceternity/sparkles'

export default function CTA() {
  const [email, setEmail] = useState('')
  const [isHovered, setIsHovered] = useState(false)
  const ref = useRef(null)
  // Change the useInView margin to trigger sooner
  const isInView = useInView(ref, { once: true, margin: "-20px" })

  return (
    <section className="py-32 relative overflow-hidden min-h-[600px] flex items-center">
      <BackgroundBeams className="opacity-40" />
      <div className="absolute inset-0 w-full h-full">
        <SparklesCore
          id="tsparticlesfullpage"
          background="transparent"
          minSize={0.6}
          maxSize={1.4}
          particleDensity={20}
          className="w-full h-full"
          particleColor="#FFFFFF"
        />
      </div>
      <Spotlight
        className="-top-40 left-0 md:left-60 md:-top-20"
        fill="white"
      />
      <div className="container mx-auto px-4 relative z-10">
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 20 }} // Reduced initial y offset
          animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
          transition={{ duration: 0.3 }} // Reduced duration
          className="text-center"
        >
          <motion.div
            initial={{ scale: 1 }}
            animate={{ scale: isHovered ? 1.02 : 1 }}
            transition={{ duration: 0.1 }}
            className="mb-8"
          >
            <h2 className="text-4xl md:text-6xl font-bold mb-6 bg-clip-text text-transparent bg-gradient-to-r from-blue-500 to-purple-500">
              {isInView && <TextGenerateEffect words="Ready to Transform Your Website?" />}
            </h2>
            <p className="text-xl md:text-2xl mb-8 max-w-3xl mx-auto text-gray-300">
              Join thousands of developers who are already using Bugzer to create flawless user experiences.
            </p>
          </motion.div>
          <motion.form 
            onSubmit={(e) => {
              e.preventDefault();
              // Handle form submission here
              console.log('Form submitted with email:', email);
            }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4 max-w-lg mx-auto"
          >
            <Input
              type="email"
              placeholder="Enter your email address..."
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full sm:w-96 h-12 bg-gray-800/50 text-white border-gray-700 rounded-full px-6 text-lg placeholder:text-gray-400 focus:ring-2 focus:ring-blue-500 transition-all duration-300"
              required
            />
            <Button
              type="submit"
              size="lg"
              onMouseEnter={() => setIsHovered(true)}
              onMouseLeave={() => setIsHovered(false)}
              className="w-full sm:w-auto h-12 px-8 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white rounded-full text-lg font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-[0_0_20px_rgba(66,153,225,0.5)]"
            >
              Get Started Free
            </Button>
          </motion.form>
          <motion.p 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="mt-6 text-sm text-gray-400"
          >
            ✨ No credit card required · Free 14-day trial · Cancel anytime
          </motion.p>
        </motion.div>
      </div>
    </section>
  )
}

