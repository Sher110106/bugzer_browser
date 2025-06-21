'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { createClient } from '@/utils/supabase/client'
import { useRouter } from 'next/navigation'
import { apiClient } from '@/utils/api-client'

export default function Landing() {
  const [websiteUrl, setWebsiteUrl] = useState('')
  const [whatToTest, setWhatToTest] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    setError('')

    try {
      const supabase = createClient()
      const { data: { user } } = await supabase.auth.getUser()

      if (!user) {
        router.push('/sign-in')
        return
      }

      // Create test using the API client
      await apiClient.createTest({
        url: websiteUrl,
        context: whatToTest
      });
      
      // After successful test creation, redirect to the reports page
      router.push('/reports')
    } catch (err) {
      console.error('Error creating test:', err)
      setError('Failed to create test. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="py-20 md:py-40 px-4 bg-gradient-to-b from-gray-900 to-black">
      <div className="max-w-5xl mx-auto text-center">
        <motion.h1
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="text-4xl md:text-6xl lg:text-7xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-500 to-purple-500 mb-4"
        >
          Hi, Welcome to Bugzer!
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="text-lg md:text-xl lg:text-2xl text-gray-400 max-w-3xl mx-auto mb-12"
        >
          Easily test your website with AI-powered agents
        </motion.p>

        <motion.form
          onSubmit={handleSubmit}
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.6 }}
          className="bg-white/5 backdrop-blur-md rounded-lg p-8 md:p-12 shadow-lg mx-auto max-w-lg"
        >
          <div className="mb-6">
            <label htmlFor="websiteUrl" className="block text-sm font-medium text-gray-200 mb-2">
              Enter Website URL
            </label>
            <input
              type="url"
              id="websiteUrl"
              value={websiteUrl}
              onChange={(e) => setWebsiteUrl(e.target.value)}
              placeholder="https://example.com"
              className="bg-gray-800/50 border border-gray-700 text-gray-100 placeholder-gray-500 rounded-md px-4 py-3 w-full focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
          </div>
          <div className="mb-8">
            <label htmlFor="whatToTest" className="block text-sm font-medium text-gray-200 mb-2">
              What to Test
            </label>
            <textarea
              id="whatToTest"
              value={whatToTest}
              onChange={(e) => setWhatToTest(e.target.value)}
              placeholder="e.g., check if the login form works, verify product search functionality"
              rows={4}
              className="bg-gray-800/50 border border-gray-700 text-gray-100 placeholder-gray-500 rounded-md px-4 py-3 w-full focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
          </div>
          {error && (
            <div className="mb-6 p-3 rounded bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              {error}
            </div>
          )}
          <Button 
            type="submit" 
            className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Creating Test...' : 'Start Test'}
          </Button>
        </motion.form>
      </div>
    </section>
  )
}