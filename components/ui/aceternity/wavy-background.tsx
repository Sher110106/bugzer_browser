"use client";
import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

export const WavyBackground = ({
  children,
  className,
  containerClassName,
  colors,
  waveWidth,
  backgroundFill,
  blur = 10,
  speed = "fast",
  waveOpacity = 0.5,
  ...props
}: {
  children?: any;
  className?: string;
  containerClassName?: string;
  colors?: string[];
  waveWidth?: number;
  backgroundFill?: string;
  blur?: number;
  speed?: "slow" | "fast";
  waveOpacity?: number;
  [key: string]: any;
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svgHeight, setSvgHeight] = useState(0);

  useEffect(() => {
    if (containerRef.current) {
      setSvgHeight(containerRef.current.offsetHeight);
    }
  }, []);

  const defaultColors = [
    "#38bdf8",
    "#818cf8",
    "#c084fc",
    "#e879f9",
    "#22d3ee",
  ];

  const waveColors = colors || defaultColors;

  return (
    <div
      className={cn(
        "h-screen flex flex-col items-center justify-center",
        containerClassName
      )}
      ref={containerRef}
      {...props}
    >
      <svg
        className={cn(
          "absolute inset-0 w-full z-0",
          className
        )}
        width="100%"
        height={svgHeight}
        viewBox={`0 0 ${waveWidth || 1000} ${svgHeight}`}
        preserveAspectRatio="none"
      >
        {backgroundFill && (
          <motion.rect
            width="100%"
            height="100%"
            fill={backgroundFill}
          />
        )}
        {[...Array(5)].map((_, index) => (
          <motion.path
            key={index}
            d={`M 0 ${svgHeight} Q 250 ${
              svgHeight - (index + 1) * 50
            } 500 ${svgHeight} T 1000 ${svgHeight} V ${
              svgHeight + 500
            } H 0 V ${svgHeight} Z`}
            fill={waveColors[index % waveColors.length]}
            opacity={waveOpacity}
            animate={{
              d: [
                `M 0 ${svgHeight} Q 250 ${
                  svgHeight - (index + 1) * 50 - 20
                } 500 ${svgHeight} T 1000 ${svgHeight} V ${
                  svgHeight + 500
                } H 0 V ${svgHeight} Z`,
                `M 0 ${svgHeight} Q 250 ${
                  svgHeight - (index + 1) * 50 + 20
                } 500 ${svgHeight} T 1000 ${svgHeight} V ${
                  svgHeight + 500
                } H 0 V ${svgHeight} Z`,
              ],
            }}
            transition={{
              duration: speed === "slow" ? 7 : 3,
              repeat: Infinity,
              repeatType: "reverse",
              ease: "easeInOut",
            }}
          />
        ))}
      </svg>
      <motion.div
        className="relative z-10"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
      >
        {children}
      </motion.div>
    </div>
  );
};

