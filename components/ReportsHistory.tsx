'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card } from '@/components/ui/card'
import { BarChart2, ExternalLink, Clock, Calendar, Trash2 } from 'lucide-react'
import { AnimatedBackground } from './ui/aceternity/animated-background'
import { apiClient } from '@/utils/api-client'

interface Report {
  id: string
  test_id: string
  results: any
  completed_at: string
  duration: number
  user_id: string
}

interface ReportsHistoryProps {
  reports: Report[]
}

export default function ReportsHistory({ reports }: ReportsHistoryProps) {
  const [searchTerm, setSearchTerm] = useState('')
  const [sortBy, setSortBy] = useState<'date' | 'duration'>('date')
  const [filterStatus, setFilterStatus] = useState<'all' | 'success' | 'error'>('all')
  const [isDeleting, setIsDeleting] = useState<string | null>(null)
  const router = useRouter()

  const handleDelete = async (reportId: string) => {
    if (confirm('Are you sure you want to delete this report?')) {
      setIsDeleting(reportId)
      try {
        // Use API client to delete the report
        await apiClient.deleteReport(reportId)
        router.refresh()
      } catch (error) {
        console.error('Error deleting report:', error)
        alert('Failed to delete report. Please try again.')
      } finally {
        setIsDeleting(null)
      }
    }
  }

  const filteredReports = reports
    .filter(report => {
      // Search filter
      const searchMatch = report.test_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        JSON.stringify(report.results).toLowerCase().includes(searchTerm.toLowerCase())
      
      // Status filter
      if (filterStatus === 'all') return searchMatch
      const hasError = report.results?.error || Object.values(report.results || {}).some(v => v === 'error')
      return filterStatus === 'error' ? hasError && searchMatch : !hasError && searchMatch
    })
    .sort((a, b) => {
      if (sortBy === 'date') {
        return new Date(b.completed_at).getTime() - new Date(a.completed_at).getTime()
      }
      return b.duration - a.duration
    })

  return (
    <div className="min-h-screen p-8 relative">
      <AnimatedBackground />
      
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-7xl mx-auto relative z-10"
      >
        <h1 className="text-3xl font-bold mb-8 bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500">Test Reports History</h1>
        
        <div className="mb-6 flex flex-wrap gap-4">
          <Input
            type="search"
            placeholder="Search reports..."
            className="max-w-xs bg-gray-800/50"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          
          <div className="flex gap-2">
            <Button
              variant={sortBy === 'date' ? 'default' : 'secondary'}
              onClick={() => setSortBy('date')}
            >
              Sort by Date
            </Button>
            <Button
              variant={sortBy === 'duration' ? 'default' : 'secondary'}
              onClick={() => setSortBy('duration')}
            >
              Sort by Duration
            </Button>
          </div>
          
          <div className="flex gap-2">
            <Button
              variant={filterStatus === 'all' ? 'default' : 'secondary'}
              onClick={() => setFilterStatus('all')}
            >
              All
            </Button>
            <Button
              variant={filterStatus === 'success' ? 'default' : 'secondary'}
              onClick={() => setFilterStatus('success')}
            >
              Success
            </Button>
            <Button
              variant={filterStatus === 'error' ? 'default' : 'secondary'}
              onClick={() => setFilterStatus('error')}
            >
              Error
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredReports.map((report) => (
            <Link key={report.id} href={`/reports/${report.id}`}>
              <Card className="p-6 hover:shadow-lg transition-all duration-300 bg-gray-800/50 backdrop-blur-sm border-gray-700/50 cursor-pointer transform hover:scale-102">
                <div className="space-y-4">
                  <div className="flex justify-between items-start">
                    <h3 className="font-semibold text-lg text-gray-200">Test #{report.test_id.slice(0, 8)}</h3>
                    <span className={`px-2 py-1 rounded text-xs ${
                      report.results?.error ? 'bg-red-500/20 text-red-300' : 'bg-green-500/20 text-green-300'
                    }`}>
                      {report.results?.error ? 'Error' : 'Success'}
                    </span>
                  </div>
                  
                  <div className="text-sm text-gray-400 space-y-2">
                    <p>Completed: {new Date(report.completed_at).toLocaleString()}</p>
                    <p>Duration: {report.duration}s</p>
                  </div>
                  
                  <div className="flex justify-between items-center">
                    <span className="text-blue-400 text-sm">View Details →</span>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={(e) => {
                        e.preventDefault()
                        handleDelete(report.id)
                      }}
                      disabled={isDeleting === report.id}
                    >
                      {isDeleting === report.id ? 'Deleting...' : 'Delete'}
                    </Button>
                  </div>
                </div>
              </Card>
            </Link>
          ))}

          {filteredReports.length === 0 && (
            <div className="col-span-full text-center py-12">
              <p className="text-gray-400 text-lg">
                {searchTerm ? 'No reports match your search criteria.' : 'No reports found. Run your first test!'}
              </p>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  )
}