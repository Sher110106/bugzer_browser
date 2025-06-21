'use client'

import { motion } from 'framer-motion'
import { TextGenerateEffect } from '@/components/ui/aceternity/text-generate-effect'
import { BentoGrid, BentoGridItem } from "@/components/ui/aceternity/bento-grid"
import { IconBug, IconBrain, IconReportAnalytics, IconRocket, IconCalendarEvent } from '@tabler/icons-react'

const steps = [
  { 
    title: "Define Your Test", 
    description: "Simply provide your web app's URL and describe the task you want the AI to perform in natural language.",
    icon: <IconBug className="w-10 h-10 text-blue-500" />,
    className: "md:col-span-2",
    header: "Step 1"
  },
  { 
    title: "AI Agent Takes Over", 
    description: "Bugzer deploys an autonomous AI agent that navigates your site in a real browser session, simulating user clicks, typing, and interactions.",
    icon: <IconBrain className="w-10 h-10 text-purple-500" />,
    className: "md:col-span-1",
    header: "Step 2"
  },
  { 
    title: "Analyze & Report", 
    description: "The agent monitors performance, logs network activity, detects errors and anomalies, and compiles everything into a detailed report.",
    icon: <IconReportAnalytics className="w-10 h-10 text-green-500" />,
    className: "md:col-span-2",
    header: "Step 3"
  },
  { 
    title: "Integrate & Automate", 
    description: "Schedule regular checks or integrate Bugzer into your workflow to test automatically after deployments.",
    icon: <IconCalendarEvent className="w-10 h-10 text-yellow-500" />,
    className: "md:col-span-3",
    header: "Step 4"
  }
]

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="py-20 px-4 bg-gradient-to-b from-gray-900 to-black">
      <motion.div
        initial={{ opacity: 0, y: 50 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="max-w-6xl mx-auto"
      >
        <h2 className="text-3xl md:text-5xl font-bold text-center mb-4 bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500">
          Go from Setup to Insights in Minutes
        </h2>
        <p className="text-xl text-gray-400 text-center mb-16 max-w-3xl mx-auto">
          Bugzer's simplified workflow makes web testing accessible to everyone, from developers to QA teams
        </p>
        
        <BentoGrid className="max-w-5xl mx-auto">
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

