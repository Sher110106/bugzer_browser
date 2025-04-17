'use client'

import { motion } from 'framer-motion'
import { TextGenerateEffect } from '@/components/ui/aceternity/text-generate-effect'
import { BentoGrid, BentoGridItem } from "@/components/ui/aceternity/bento-grid"
import { IconBug, IconBrain, IconReportAnalytics, IconRocket, IconRefresh } from '@tabler/icons-react'

const steps = [
  { 
    title: "Input URL", 
    description: "Enter your website's URL to begin the optimization journey.",
    icon: <IconBug className="w-10 h-10 text-blue-500" />,
    className: "md:col-span-2",
    header: "Start Here"
  },
  { 
    title: "AI Analysis", 
    description: "Our advanced AI simulates user behavior and analyzes your site.",
    icon: <IconBrain className="w-10 h-10 text-purple-500" />,
    className: "md:col-span-1",
    header: "Smart Scanning"
  },
  { 
    title: "Generate Report", 
    description: "Receive a comprehensive report with actionable insights.",
    icon: <IconReportAnalytics className="w-10 h-10 text-green-500" />,
    className: "md:col-span-1",
    header: "Detailed Insights"
  },
  { 
    title: "Optimize", 
    description: "Implement suggested improvements to enhance your website.",
    icon: <IconRocket className="w-10 h-10 text-red-500" />,
    className: "md:col-span-2",
    header: "Boost Performance"
  },
  { 
    title: "Continuous Improvement", 
    description: "Regular re-testing ensures your site stays optimized.",
    icon: <IconRefresh className="w-10 h-10 text-yellow-500" />,
    className: "md:col-span-3",
    header: "Stay Ahead"
  }
]

export default function HowItWorks() {
  return (
    <section className="py-20 px-4 bg-gradient-to-b from-gray-900 to-black">
      <motion.div
        initial={{ opacity: 0, y: 50 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="max-w-6xl mx-auto"
      >
        <h2 className="text-3xl md:text-4xl font-bold text-center mb-12">
          <TextGenerateEffect words="How Bugzer Optimizes Your Website" />
        </h2>
        <BentoGrid className="max-w-4xl mx-auto">
          {steps.map((step, i) => (
            <BentoGridItem
              key={i}
              title={step.title}
              description={step.description}
              header={step.header}
              icon={step.icon}
              className={step.className}
            />
          ))}
        </BentoGrid>
      </motion.div>
    </section>
  )
}

