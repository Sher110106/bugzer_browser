'use client'

import Link from 'next/link'
import { motion } from 'framer-motion'
import { BackgroundBeams } from '@/components/ui/aceternity/background-beams'
import { SparklesCore } from '@/components/ui/aceternity/sparkles'

export function Footer() {
  return (
    <footer className="relative border-t border-border/40 bg-gradient-to-b from-transparent to-gray-900/50 mt-auto">
      
      <div className="container relative z-10 max-w-screen-2xl py-8">
        <div className="flex flex-col items-center justify-center space-y-6">
          <Link href="/" className="flex items-center space-x-2 mb-2">
            <span className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-500 to-purple-500">
              Bugzer
            </span>
          </Link>
          
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="flex flex-wrap justify-center gap-6"
          >
            <Link 
              href="/features" 
              className="text-sm font-medium text-gray-300 hover:text-white transition-all duration-300 hover:scale-105"
            >
              Features
            </Link>
            <Link 
              href="/pricing" 
              className="text-sm font-medium text-gray-300 hover:text-white transition-all duration-300 hover:scale-105"
            >
              Pricing
            </Link>
            <Link 
              href="/docs" 
              className="text-sm font-medium text-gray-300 hover:text-white transition-all duration-300 hover:scale-105"
            >
              Documentation
            </Link>
          </motion.div>

          <div className="flex space-x-4">
            <Link 
              href="https://twitter.com/bugzer" 
              className="text-gray-400 hover:text-white transition-colors hover:scale-110 transform duration-200"
              target="_blank"
            >
              <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M8.29 20.251c7.547 0 11.675-6.253 11.675-11.675 0-.178 0-.355-.012-.53A8.348 8.348 0 0022 5.92a8.19 8.19 0 01-2.357.646 4.118 4.118 0 001.804-2.27 8.224 8.224 0 01-2.605.996 4.107 4.107 0 00-6.993 3.743 11.65 11.65 0 01-8.457-4.287 4.106 4.106 0 001.27 5.477A4.072 4.072 0 012.8 9.713v.052a4.105 4.105 0 003.292 4.022 4.095 4.095 0 01-1.853.07 4.108 4.108 0 003.834 2.85A8.233 8.233 0 012 18.407a11.616 11.616 0 006.29 1.84" />
              </svg>
            </Link>
            <Link 
              href="https://github.com/bugzer" 
              className="text-gray-400 hover:text-white transition-colors hover:scale-110 transform duration-200"
              target="_blank"
            >
              <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
              </svg>
            </Link>
          </div>

          <div className="pt-6 border-t border-border/40 w-full">
            <p className="text-center text-sm text-gray-400">
              © {new Date().getFullYear()} Bugzer. All rights reserved.
            </p>
          </div>
        </div>
      </div>
    </footer>
  )
}