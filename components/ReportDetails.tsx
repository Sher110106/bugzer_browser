'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { ArrowLeft, MessageSquare, ChevronDown, ChevronUp } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { AnimatedBackground } from './ui/aceternity/animated-background'
import { useState } from 'react'

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

interface PerformanceMetrics {
  timing?: {
    pageLoad?: string
    domContentLoaded?: string
    firstPaint?: string
    firstContentfulPaint?: string
  }
  connection?: {
    dnsLookup?: string
    tcpConnection?: string
    serverResponse?: string
  }
  processing?: {
    domProcessing?: string
    resourceLoading?: string
  }
  resources?: {
    totalResources?: string
    totalSize?: string
    totalDuration?: string
  }
  slowestResources?: Array<{
    url: string
    duration: string
    size: string
    type: string
  }>
  networkRequests?: {
    total?: string
    byType?: Array<{
      type: string
      count: string
      size: string
    }>
  }
  largestRequests?: Array<{
    url: string
    size: string
    duration: string
  }>
  anomalies?: {
    layout?: string[]
    accessibility?: string[]
  }
}

export default function ReportDetails({ report }: ReportDetailsProps) {
  const router = useRouter()
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    timing: true,
    connection: true,
    processing: true,
    resources: true,
    slowestResources: false,
    networkRequests: false,
    largestRequests: false,
    anomalies: false
  })

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }))
  }

  const results = Array.isArray(report.results) ? report.results : [report.results]
  const hasError = results.some(r => r.error || r === 'error')

  // Extract system role message that contains the performance report
  const systemMessages = results.filter(result => 
    typeof result === 'object' && 
    result?.role === 'system' && 
    result?.content?.includes('PERFORMANCE_METRICS_REPORT')
  )

  // Parse performance metrics from system message
  const parsePerformanceMetrics = (content: string): PerformanceMetrics => {
    const metrics: PerformanceMetrics = {
      timing: {},
      connection: {},
      processing: {},
      resources: {},
      slowestResources: [],
      networkRequests: { byType: [] },
      largestRequests: [],
      anomalies: { layout: [], accessibility: [] }
    }

    // Extract timing metrics
    const timingMatch = content.match(/⏱️ Timing Metrics:[\s\S]*?-[\s\S]*?-[\s\S]*?-[\s\S]*?-/g)
    if (timingMatch && timingMatch[0]) {
      const lines = timingMatch[0].split('\n')
      metrics.timing = {
        pageLoad: lines.find(l => l.includes('Page Load Time'))?.split(':')[1]?.trim(),
        domContentLoaded: lines.find(l => l.includes('DOM Content Loaded'))?.split(':')[1]?.trim(),
        firstPaint: lines.find(l => l.includes('First Paint'))?.split(':')[1]?.trim(),
        firstContentfulPaint: lines.find(l => l.includes('First Contentful Paint'))?.split(':')[1]?.trim()
      }
    }

    // Extract connection metrics
    const connectionMatch = content.match(/🔄 Connection Metrics:[\s\S]*?-[\s\S]*?-[\s\S]*?-/g)
    if (connectionMatch && connectionMatch[0]) {
      const lines = connectionMatch[0].split('\n')
      metrics.connection = {
        dnsLookup: lines.find(l => l.includes('DNS Lookup'))?.split(':')[1]?.trim(),
        tcpConnection: lines.find(l => l.includes('TCP Connection'))?.split(':')[1]?.trim(),
        serverResponse: lines.find(l => l.includes('Server Response'))?.split(':')[1]?.trim()
      }
    }

    // Extract processing metrics
    const processingMatch = content.match(/⚙️ Processing Metrics:[\s\S]*?-[\s\S]*?-/g)
    if (processingMatch && processingMatch[0]) {
      const lines = processingMatch[0].split('\n')
      metrics.processing = {
        domProcessing: lines.find(l => l.includes('DOM Processing'))?.split(':')[1]?.trim(),
        resourceLoading: lines.find(l => l.includes('Resource Loading'))?.split(':')[1]?.trim()
      }
    }

    // Extract resource stats
    const resourcesMatch = content.match(/📦 Resource Stats:[\s\S]*?-[\s\S]*?-[\s\S]*?-/g)
    if (resourcesMatch && resourcesMatch[0]) {
      const lines = resourcesMatch[0].split('\n')
      metrics.resources = {
        totalResources: lines.find(l => l.includes('Total Resources'))?.split(':')[1]?.trim(),
        totalSize: lines.find(l => l.includes('Total Size'))?.split(':')[1]?.trim(),
        totalDuration: lines.find(l => l.includes('Total Resource Duration'))?.split(':')[1]?.trim()
      }
    }

    // Extract layout issues
    const layoutMatch = content.match(/📐 Layout Issues:[\s\S]*?1\.[\s\S]*?2\.[\s\S]*?3\.[\s\S]*?4\.[\s\S]*?5\./g)
    if (layoutMatch && layoutMatch[0]) {
      const lines = layoutMatch[0].split('\n').slice(1) // Skip header
      metrics.anomalies!.layout = lines
        .filter(l => l.trim().length > 0)
        .map(l => l.trim().replace(/^\d+\.\s*/, ''))
    }

    // Extract accessibility issues
    const accessibilityMatch = content.match(/♿ Accessibility Issues:[\s\S]*?1\.[\s\S]*?2\.[\s\S]*?3\.[\s\S]*?4\.[\s\S]*?5\./g)
    if (accessibilityMatch && accessibilityMatch[0]) {
      const lines = accessibilityMatch[0].split('\n').slice(1) // Skip header
      metrics.anomalies!.accessibility = lines
        .filter(l => l.trim().length > 0)
        .map(l => l.trim().replace(/^\d+\.\s*/, ''))
    }

    return metrics
  }

  function formatDate(dateString: string) {
    return new Date(dateString).toLocaleString()
  }

  // Extract and parse performance metrics from system message
  const performanceMetrics = systemMessages.length > 0 
    ? parsePerformanceMetrics(systemMessages[0].content) 
    : null

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center py-20 px-4">
      <AnimatedBackground />
      
      <motion.div
        initial={{ opacity: 0, y: 50 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7 }}
        className="backdrop-blur-sm bg-gray-900/40 rounded-2xl shadow-2xl p-8 max-w-5xl w-full relative z-10 border border-gray-800/50"
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

        {performanceMetrics && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="mb-8"
          >
            <Card className="p-6 bg-gray-800/50 hover:bg-gray-800/70 transition-all duration-300 border-gray-700/50">
              <h2 className="text-2xl font-semibold text-indigo-300 mb-4">Performance Report</h2>
              <p className="text-gray-300 mb-6">Performance metrics for {report.tests?.url || 'tested URL'}</p>
              
              {/* Timing Metrics */}
              <div className="mb-4">
                <div 
                  className="flex justify-between items-center cursor-pointer py-2 border-b border-gray-700/50"
                  onClick={() => toggleSection('timing')}
                >
                  <h3 className="text-xl font-semibold text-blue-300">⏱️ Timing Metrics</h3>
                  {expandedSections.timing ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
                </div>
                {expandedSections.timing && performanceMetrics.timing && (
                  <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-4 pl-2">
                    <div className="bg-gray-800/30 p-3 rounded-lg">
                      <p className="text-gray-400 text-sm">Page Load Time</p>
                      <p className="text-blue-300 text-xl font-medium">{performanceMetrics.timing.pageLoad}</p>
                    </div>
                    <div className="bg-gray-800/30 p-3 rounded-lg">
                      <p className="text-gray-400 text-sm">DOM Content Loaded</p>
                      <p className="text-blue-300 text-xl font-medium">{performanceMetrics.timing.domContentLoaded}</p>
                    </div>
                    <div className="bg-gray-800/30 p-3 rounded-lg">
                      <p className="text-gray-400 text-sm">First Paint</p>
                      <p className="text-blue-300 text-xl font-medium">{performanceMetrics.timing.firstPaint}</p>
                    </div>
                    <div className="bg-gray-800/30 p-3 rounded-lg">
                      <p className="text-gray-400 text-sm">First Contentful Paint</p>
                      <p className="text-blue-300 text-xl font-medium">{performanceMetrics.timing.firstContentfulPaint}</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Connection Metrics */}
              <div className="mb-4">
                <div 
                  className="flex justify-between items-center cursor-pointer py-2 border-b border-gray-700/50"
                  onClick={() => toggleSection('connection')}
                >
                  <h3 className="text-xl font-semibold text-green-300">🔄 Connection Metrics</h3>
                  {expandedSections.connection ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
                </div>
                {expandedSections.connection && performanceMetrics.connection && (
                  <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-4 pl-2">
                    <div className="bg-gray-800/30 p-3 rounded-lg">
                      <p className="text-gray-400 text-sm">DNS Lookup</p>
                      <p className="text-green-300 text-xl font-medium">{performanceMetrics.connection.dnsLookup}</p>
                    </div>
                    <div className="bg-gray-800/30 p-3 rounded-lg">
                      <p className="text-gray-400 text-sm">TCP Connection</p>
                      <p className="text-green-300 text-xl font-medium">{performanceMetrics.connection.tcpConnection}</p>
                    </div>
                    <div className="bg-gray-800/30 p-3 rounded-lg">
                      <p className="text-gray-400 text-sm">Server Response</p>
                      <p className="text-green-300 text-xl font-medium">{performanceMetrics.connection.serverResponse}</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Processing Metrics */}
              <div className="mb-4">
                <div 
                  className="flex justify-between items-center cursor-pointer py-2 border-b border-gray-700/50"
                  onClick={() => toggleSection('processing')}
                >
                  <h3 className="text-xl font-semibold text-yellow-300">⚙️ Processing Metrics</h3>
                  {expandedSections.processing ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
                </div>
                {expandedSections.processing && performanceMetrics.processing && (
                  <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-4 pl-2">
                    <div className="bg-gray-800/30 p-3 rounded-lg">
                      <p className="text-gray-400 text-sm">DOM Processing</p>
                      <p className="text-yellow-300 text-xl font-medium">{performanceMetrics.processing.domProcessing}</p>
                    </div>
                    <div className="bg-gray-800/30 p-3 rounded-lg">
                      <p className="text-gray-400 text-sm">Resource Loading</p>
                      <p className="text-yellow-300 text-xl font-medium">{performanceMetrics.processing.resourceLoading}</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Resource Stats */}
              <div className="mb-4">
                <div 
                  className="flex justify-between items-center cursor-pointer py-2 border-b border-gray-700/50"
                  onClick={() => toggleSection('resources')}
                >
                  <h3 className="text-xl font-semibold text-purple-300">📦 Resource Stats</h3>
                  {expandedSections.resources ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
                </div>
                {expandedSections.resources && performanceMetrics.resources && (
                  <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-4 pl-2">
                    <div className="bg-gray-800/30 p-3 rounded-lg">
                      <p className="text-gray-400 text-sm">Total Resources</p>
                      <p className="text-purple-300 text-xl font-medium">{performanceMetrics.resources.totalResources}</p>
                    </div>
                    <div className="bg-gray-800/30 p-3 rounded-lg">
                      <p className="text-gray-400 text-sm">Total Size</p>
                      <p className="text-purple-300 text-xl font-medium">{performanceMetrics.resources.totalSize}</p>
                    </div>
                    <div className="bg-gray-800/30 p-3 rounded-lg">
                      <p className="text-gray-400 text-sm">Total Resource Duration</p>
                      <p className="text-purple-300 text-xl font-medium">{performanceMetrics.resources.totalDuration}</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Anomalies Section */}
              {performanceMetrics.anomalies && (
                <div className="mb-4">
                  <div 
                    className="flex justify-between items-center cursor-pointer py-2 border-b border-gray-700/50"
                    onClick={() => toggleSection('anomalies')}
                  >
                    <h3 className="text-xl font-semibold text-red-300">🔍 Anomalies</h3>
                    {expandedSections.anomalies ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
                  </div>
                  {expandedSections.anomalies && (
                    <div className="mt-3 grid grid-cols-1 gap-4 pl-2">
                      {performanceMetrics.anomalies?.layout && performanceMetrics.anomalies.layout.length > 0 && (
                        <div className="bg-gray-800/30 p-4 rounded-lg">
                          <h4 className="text-lg font-medium text-red-300 mb-2">📐 Layout Issues</h4>
                          <ul className="list-disc pl-5 space-y-1">
                            {performanceMetrics.anomalies.layout?.map((issue, i) => (
                              <li key={i} className="text-gray-300">{issue}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {performanceMetrics.anomalies?.accessibility && performanceMetrics.anomalies.accessibility.length > 0 && (
                        <div className="bg-gray-800/30 p-4 rounded-lg">
                          <h4 className="text-lg font-medium text-red-300 mb-2">♿ Accessibility Issues</h4>
                          <ul className="list-disc pl-5 space-y-1">
                            {performanceMetrics.anomalies.accessibility?.map((issue, i) => (
                              <li key={i} className="text-gray-300">{issue}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </Card>
          </motion.div>
        )}

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.5 }}
          className="mb-8"
        >
          <Card className="p-6 bg-gray-800/50 hover:bg-gray-800/70 transition-all duration-300 border-gray-700/50">
            <h2 className="text-xl font-semibold text-indigo-300 mb-4">Conversation Log</h2>
            <div className="space-y-4 max-h-96 overflow-y-auto pr-2">
              {results
                .filter(result => 
                  typeof result === 'object' && 
                  result?.role !== 'system' &&
                  !(typeof result?.content === 'string' && result.content.includes('PERFORMANCE_METRICS_REPORT'))
                )
                .map((result, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.3, delay: 0.1 * index }}
                    className={`p-4 rounded-lg ${
                      result.role === 'user' ? 'bg-blue-500/10 border-l-2 border-blue-500' : 'bg-gray-700/50'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <span className={`mt-1 ${
                        result.role === 'user' ? 'text-blue-400' : 'text-green-400'
                      }`}>•</span>
                      <div className="flex-1">
                        <p className="text-xs font-medium mb-1 text-gray-400">{result.role}</p>
                        <p className="text-gray-200 whitespace-pre-wrap break-words">
                          {typeof result.content === 'string' ? result.content : JSON.stringify(result.content, null, 2)}
                        </p>
                        {result.timestamp && (
                          <p className="text-sm text-gray-400 mt-2 text-right">
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
          className="flex justify-between items-center gap-4 flex-wrap"
        >
          <Button onClick={() => router.back()} variant="secondary">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Reports
          </Button>
          <div className="flex gap-4 flex-wrap">
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