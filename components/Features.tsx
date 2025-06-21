'use client'

import { motion } from 'framer-motion'
import { InfiniteMovingCards } from '@/components/ui/aceternity/infinite-moving-cards'
import { CheckCircleIcon } from '@heroicons/react/24/outline'

const featureHighlights = [
  {
    title: 'AI-Powered Autonomous Navigation',
    description: 'Intelligent agents understand context and navigate complex web applications like a real user.',
    icon: '🤖'
  },
  {
    title: 'Natural Language Test Instructions',
    description: 'No complex scripting needed. Just tell Bugzer what you want to test in plain English.',
    icon: '💬'
  },
  {
    title: 'Comprehensive Performance Analysis',
    description: 'Automatically capture key performance metrics to identify bottlenecks.',
    icon: '📊'
  },
  {
    title: 'Automated Anomaly & Bug Detection',
    description: 'Detects Javascript errors, network request failures, layout issues, and other common problems.',
    icon: '🐛'
  },
  {
    title: 'Detailed Actionable Reports',
    description: 'Get clear summaries with step-by-step agent actions for easy debugging.',
    icon: '📝'
  },
  {
    title: 'Scheduled & Automated Runs',
    description: 'Set up recurring tests to continuously monitor your application.',
    icon: '⏱️'
  }
]

const benefits = [
  "Save Time & Reduce Costs: Dramatically cut down on manual testing effort",
  "Improve Application Quality: Catch bugs and regressions before they impact users",
  "Release Faster & More Confidently: Integrate automated checks into your workflow",
  "Gain Performance Insights: Understand how your application performs under simulated use",
  "Focus on Building: Let AI handle the repetitive testing, freeing up your team for feature development"
]

export default function Features() {
  return (
    <section className="py-16 md:py-24 px-4 overflow-hidden bg-gradient-to-b from-gray-900 to-black">
      <div className="max-w-7xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl md:text-5xl font-bold mb-4 bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500">
            Powerful Features Driven by AI
          </h2>
          <p className="text-xl text-gray-400 max-w-3xl mx-auto">
            Experience the future of web testing with our intelligent autonomous agents
          </p>
        </motion.div>
        
        <div className="-mx-4 sm:mx-0 mb-20">
          <InfiniteMovingCards 
            items={featureHighlights} 
            direction="left" 
            speed="slow" 
            pauseOnHover={true}
          />
        </div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          viewport={{ once: true, margin: "-50px" }}
          className="mt-20"
        >
          <h3 className="text-2xl md:text-3xl font-bold text-center mb-10">
            Why Development Teams Choose Bugzer
          </h3>
          
          <div className="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto">
            {benefits.map((benefit, index) => (
              <motion.div 
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1, duration: 0.4 }}
                viewport={{ once: true }}
                className="flex p-4 bg-gray-800/30 backdrop-blur-sm rounded-lg border border-gray-700/30"
              >
                <CheckCircleIcon className="h-6 w-6 text-green-500 mr-3 flex-shrink-0" />
                <p className="text-gray-300">{benefit}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          viewport={{ once: true, margin: "-50px" }}
          className="mt-20 text-center"
        >
          <h3 className="text-2xl md:text-3xl font-bold mb-8">
            How Can Bugzer Help You?
          </h3>
          
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5 max-w-5xl mx-auto">
            {[
              {
                title: "Post-Deployment Checks",
                description: "Quickly verify critical functionality after pushing new code",
                icon: "🚀"
              },
              {
                title: "Regression Testing",
                description: "Ensure new features haven't broken existing ones",
                icon: "🔄"
              },
              {
                title: "Performance Benchmarking",
                description: "Track performance trends over time or after changes",
                icon: "📈"
              },
              {
                title: "Testing User Flows",
                description: "Validate multi-step processes like sign-up or checkout",
                icon: "🔄"
              }
            ].map((useCase, index) => (
              <motion.div 
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1, duration: 0.4 }}
                viewport={{ once: true }}
                className="p-5 bg-gradient-to-br from-gray-800/50 to-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-700/30 text-center"
              >
                <div className="text-3xl mb-3">{useCase.icon}</div>
                <h4 className="text-lg font-semibold text-white mb-2">{useCase.title}</h4>
                <p className="text-sm text-gray-400">{useCase.description}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  )
}

