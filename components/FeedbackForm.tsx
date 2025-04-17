'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card } from '@/components/ui/card'
import { createClient } from '@/utils/supabase/client'
import { AnimatedBackground } from './ui/aceternity/animated-background'
import { apiClient } from '@/utils/api-client'

interface FeedbackFormProps {
  userId: string
  reportId: string  // Add reportId prop
}

type FeedbackCategory = 'test_results' | 'user_interface' | 'performance' | 'feature_request' | 'bug_report' | 'other'

export default function FeedbackForm({ userId, reportId }: FeedbackFormProps) {
  const [category, setCategory] = useState<FeedbackCategory>('test_results')
  const [rating, setRating] = useState<number>(5)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitStatus, setSubmitStatus] = useState<'idle' | 'success' | 'error'>('idle')

  const categories: { value: FeedbackCategory; label: string }[] = [
    { value: 'test_results', label: 'Test Results Accuracy' },
    { value: 'user_interface', label: 'User Interface' },
    { value: 'performance', label: 'Performance' },
    { value: 'feature_request', label: 'Feature Request' },
    { value: 'bug_report', label: 'Bug Report' },
    { value: 'other', label: 'Other' }
  ]

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    
    try {
      // Use the API client to update report feedback
      await apiClient.updateReportFeedback(reportId, {
        category,
        rating,
        title,
        description,
        created_at: new Date().toISOString()
      });
      
      setSubmitStatus('success')
      setTitle('')
      setDescription('')
      setRating(5)
      
      // Reset form after 3 seconds
      setTimeout(() => {
        setSubmitStatus('idle')
      }, 3000)
    } catch (error) {
      console.error('Error submitting feedback:', error)
      setSubmitStatus('error')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center py-20 px-4 relative">
      <AnimatedBackground />
      
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative z-10 w-full max-w-2xl"
      >
        <Card className="p-8 backdrop-blur-sm bg-gray-900/40 border border-gray-800/50">
          <h1 className="text-3xl font-bold mb-8 bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500">
            Provide Feedback
          </h1>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Category
              </label>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {categories.map(({ value, label }) => (
                  <Button
                    key={value}
                    type="button"
                    variant={category === value ? 'default' : 'secondary'}
                    onClick={() => setCategory(value)}
                    className="w-full"
                  >
                    {label}
                  </Button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Rating
              </label>
              <div className="flex gap-2">
                {[1, 2, 3, 4, 5].map((value) => (
                  <Button
                    key={value}
                    type="button"
                    variant={rating === value ? 'default' : 'secondary'}
                    onClick={() => setRating(value)}
                    className="w-12 h-12"
                  >
                    {value}
                  </Button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Title
              </label>
              <Input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Brief summary of your feedback"
                required
                className="bg-gray-800/50"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Description
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Detailed feedback..."
                required
                rows={4}
                className="w-full rounded-md border border-gray-700 bg-gray-800/50 px-3 py-2 text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div className="flex justify-end">
              <Button
                type="submit"
                disabled={isSubmitting}
                className={`${
                  submitStatus === 'success'
                    ? 'bg-green-600 hover:bg-green-700'
                    : submitStatus === 'error'
                    ? 'bg-red-600 hover:bg-red-700'
                    : 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700'
                } transition-all duration-300`}
              >
                {isSubmitting
                  ? 'Submitting...'
                  : submitStatus === 'success'
                  ? 'Feedback Submitted!'
                  : submitStatus === 'error'
                  ? 'Error Submitting'
                  : 'Submit Feedback'}
              </Button>
            </div>
          </form>
        </Card>
      </motion.div>
    </div>
  )
}