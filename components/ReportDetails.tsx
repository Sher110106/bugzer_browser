'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { ArrowLeft, MessageSquare } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { AnimatedBackground } from './ui/aceternity/animated-background'

interface ReportDetailsProps {
  report: {
    id: string
    test_id: string
    results: any
    completed_at: string
    duration: number
    tests?: {
      url?: string
      context?: string
    }
  }
}

export default function ReportDetails({ report }: ReportDetailsProps) {
  const router = useRouter()
  const results = Array.isArray(report.results) ? report.results : [report.results]
  const hasError = results.some(r => r.error || r === 'error')

  function formatDate(dateString: string) {
    return new Date(dateString).toLocaleString()
  }

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center py-20 px-4">
      <AnimatedBackground />
      
      <motion.div
        initial={{ opacity: 0, y: 50 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7 }}
        className="backdrop-blur-sm bg-gray-900/40 rounded-2xl shadow-2xl p-8 max-w-4xl w-full relative z-10 border border-gray-800/50"
      >
        <div className="flex justify-between items-start mb-8">
          <motion.h1
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500"
          >
            Test Report Details
          </motion.h1>
          <span className={`px-3 py-1 rounded-full text-sm ${
            hasError ? 'bg-red-500/20 text-red-300' : 'bg-green-500/20 text-green-300'
          }`}>
            {hasError ? 'Failed' : 'Success'}
          </span>
        </div>

        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8"
        >
          <Card className="p-6 bg-gray-800/50 hover:bg-gray-800/70 transition-all duration-300 border-gray-700/50">
            <h2 className="text-xl font-semibold text-blue-300 mb-3">Test Details</h2>
            <div className="space-y-2 text-gray-300">
              <p><span className="text-gray-400">URL:</span> {report.tests?.url || 'N/A'}</p>
              <p><span className="text-gray-400">Context:</span> {report.tests?.context || 'N/A'}</p>
              <p><span className="text-gray-400">Duration:</span> {report.duration}s</p>
              <p><span className="text-gray-400">Completed:</span> {formatDate(report.completed_at)}</p>
            </div>
          </Card>

          <Card className="p-6 bg-gray-800/50 hover:bg-gray-800/70 transition-all duration-300 border-gray-700/50">
            <h2 className="text-xl font-semibold text-purple-300 mb-3">Test Statistics</h2>
            <div className="space-y-2 text-gray-300">
              <p><span className="text-gray-400">Test ID:</span> {report.test_id}</p>
              <p><span className="text-gray-400">Status:</span> {hasError ? 'Failed' : 'Successful'}</p>
              <p><span className="text-gray-400">Steps Count:</span> {results.length}</p>
            </div>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.5 }}
          className="mb-8"
        >
          <Card className="p-6 bg-gray-800/50 hover:bg-gray-800/70 transition-all duration-300 border-gray-700/50">
            <h2 className="text-xl font-semibold text-indigo-300 mb-4">Results Log</h2>
            <div className="space-y-4">
              {results.map((result, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, delay: 0.1 * index }}
                  className={`p-4 rounded-lg ${
                    result.error ? 'bg-red-500/10' : 'bg-gray-700/50'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <span className={`mt-1 ${
                      result.error ? 'text-red-400' : 'text-blue-400'
                    }`}>•</span>
                    <div>
                      <p className="text-gray-200">{
                        typeof result === 'string' ? result : JSON.stringify(result, null, 2)
                      }</p>
                      {result.timestamp && (
                        <p className="text-sm text-gray-400 mt-1">
                          {new Date(result.timestamp).toLocaleString()}
                        </p>
                      )}
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.6 }}
          className="flex justify-between items-center gap-4"
        >
          <Button onClick={() => router.back()} variant="secondary">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Reports
          </Button>
          <div className="flex gap-4">
            <Button onClick={() => router.push(`/report?id=${report.id}`)}>
              <MessageSquare className="w-4 h-4 mr-2" />
              Provide Feedback
            </Button>
            <Button
              className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
              onClick={() => window.print()}
            >
              Export Report
            </Button>
          </div>
        </motion.div>
      </motion.div>
    </div>
  )
}