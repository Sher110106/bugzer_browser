'use client'
import { motion as Motion } from 'framer-motion'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { SparklesCore } from './ui/aceternity/sparkles'
import { BackgroundBeams } from './ui/aceternity/background-beams'

const ReportDetails = () => {
  const reportData = {
    websiteUrl: 'https://example-shop.com',
    testContext: 'Check if the add to-cart button works on the product page',
    results: [
      'Navigated to https://example-shop.com successfully at 14:32:05 UTC',
      'Page load latency: 1.8 seconds',
      "Located 'Add to Cart' button on product 'Blue T-Shirt' after 2 seconds",
      "Clicked 'Add to Cart' button at 14:32:08 UTC",
      'Cart update latency: 0.9 seconds',
      'Cart updated successfully - 1 item added (confirmed via cart counter)',
      'Observed smooth transition to cart summary page',
      'Total test duration: 12 seconds',
      'Network requests: 15 successful, 0 failed',
      'No errors encountered during test',
      'Additional note: Product image loaded correctly before action.',
    ],
  }

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center py-20 px-4 overflow-hidden bg-gradient-to-b from-gray-900 via-gray-800 to-black">
      <BackgroundBeams className="opacity-40" />
      <div className="absolute inset-0 w-full h-full z-0">
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
      <Motion.div
        initial={{ opacity: 0, y: 50 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7 }}
        className="backdrop-blur-sm bg-black/30 rounded-2xl shadow-2xl p-8 max-w-4xl w-full relative z-10 border border-gray-800/50"
      >
        <Motion.h1
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="text-4xl font-bold text-center mb-8 bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500"
        >
          Your Test Report
        </Motion.h1>
        <Motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="mb-8 p-6 rounded-xl bg-gray-900/50 hover:bg-gray-900/70 transition-all duration-300"
        >
          <p className="text-xl font-semibold text-blue-300 mb-3">Website URL:</p>
          <p className="text-gray-300 text-lg">{reportData.websiteUrl}</p>
        </Motion.div>
        <Motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="mb-8 p-6 rounded-xl bg-gray-900/50 hover:bg-gray-900/70 transition-all duration-300"
        >
          <p className="text-xl font-semibold text-purple-300 mb-3">Test Context:</p>
          <p className="text-gray-300 text-lg">{reportData.testContext}</p>
        </Motion.div>
        <Motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.5 }}
          className="mb-8 p-6 rounded-xl bg-gray-900/50 hover:bg-gray-900/70 transition-all duration-300"
        >
          <p className="text-xl font-semibold text-indigo-300 mb-4">Results:</p>
          <ul className="space-y-3">
            {reportData.results.map((result, index) => (
              <Motion.li
                key={index}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3, delay: 0.1 * index }}
                className="flex items-start space-x-3 text-gray-300 hover:text-gray-100 transition-colors duration-200"
              >
                <span className="text-blue-400 mt-1">•</span>
                <span>{result}</span>
              </Motion.li>
            ))}
          </ul>
        </Motion.div>
        <Motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.6 }}
          className="flex justify-center"
        >
          <Link href="/">
            <Button className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white text-lg px-10 py-6 rounded-full transition-all duration-300 transform hover:scale-105 hover:shadow-[0_0_20px_rgba(66,153,225,0.5)] font-medium">
              Back to Test
            </Button>
          </Link>
        </Motion.div>
      </Motion.div>
    </div>
  )
}

export default ReportDetails