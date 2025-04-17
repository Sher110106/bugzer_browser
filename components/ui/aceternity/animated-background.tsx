'use client'

import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'

export const AnimatedBackground = () => {
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 })
  const backgroundRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (backgroundRef.current) {
        const rect = backgroundRef.current.getBoundingClientRect()
        setMousePosition({
          x: ((e.clientX - rect.left) / rect.width) * 100,
          y: ((e.clientY - rect.top) / rect.height) * 100,
        })
      }
    }

    window.addEventListener('mousemove', handleMouseMove)
    return () => window.removeEventListener('mousemove', handleMouseMove)
  }, [])

  return (
    <>
      <div className="fixed inset-0 -z-10 h-full w-full bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(120,119,198,0.3),rgba(255,255,255,0))]" />
      <div
        ref={backgroundRef}
        className="fixed inset-0 -z-20 h-full w-full overflow-hidden"
      >
        <motion.div
          className="absolute inset-0 bg-gradient-to-br from-blue-500/20 via-purple-500/20 to-pink-500/20"
          animate={{
            background: [
              'radial-gradient(circle at 0% 0%, rgba(29, 78, 216, 0.15) 0%, transparent 50%)',
              'radial-gradient(circle at 100% 100%, rgba(167, 139, 250, 0.15) 0%, transparent 50%)',
              'radial-gradient(circle at 50% 50%, rgba(249, 168, 212, 0.15) 0%, transparent 50%)',
              'radial-gradient(circle at 0% 100%, rgba(29, 78, 216, 0.15) 0%, transparent 50%)',
              'radial-gradient(circle at 100% 0%, rgba(167, 139, 250, 0.15) 0%, transparent 50%)',
            ],
          }}
          transition={{
            duration: 8,
            repeat: Infinity,
            repeatType: "reverse",
          }}
        />
        <div 
          className="absolute inset-0 bg-gradient-to-r from-transparent via-blue-500/10 to-transparent"
          style={{
            transform: `translateX(${mousePosition.x - 50}px)`,
            transition: 'transform 0.2s ease-out',
          }}
        />
        <div className="absolute inset-0 bg-[url('/noise.png')] opacity-[0.015] mix-blend-overlay" />
      </div>
      <div className="absolute inset-0 -z-10 h-full w-full bg-[radial-gradient(circle_500px_at_50%_200px,rgba(120,119,198,0.1),transparent)]" />
    </>
  )
}