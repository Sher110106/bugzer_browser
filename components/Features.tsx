'use client'

import { motion } from 'framer-motion'
import { InfiniteMovingCards } from '@/components/ui/aceternity/infinite-moving-cards'

const featureHighlights = [
  {
    title: 'AI-Powered Navigation',
    description: 'Our autonomous AI agent navigates your website like a real user.',
    icon: '🤖'
  },
  {
    title: 'Natural Language Instructions',
    description: 'Simply tell Bugzer what to test in plain English.',
    icon: '💬'
  },
  {
    title: 'Automated VM Infrastructure',
    description: 'Tests run in isolated, secure virtual machines.',
    icon: '🖥️'
  },
  {
    title: 'Real-time Monitoring',
    description: 'Get instant alerts when issues are detected.',
    icon: '📡'
  }
]

export default function Features() {
  return (
    <section className="py-12 md:py-20 px-4 overflow-hidden bg-gradient-to-b from-gray-900 to-black">
      <div className="max-w-7xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-center mb-12"
        >
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            AI-Powered Testing
          </h2>
          <p className="text-xl text-gray-400 max-w-3xl mx-auto">
            Experience the future of web testing with our autonomous AI agent
          </p>
        </motion.div>
        
        <div className="-mx-4 sm:mx-0">
          <InfiniteMovingCards 
            items={featureHighlights} 
            direction="left" 
            speed="slow" 
            pauseOnHover={true}
          />
        </div>
      </div>
    </section>
  )
}

