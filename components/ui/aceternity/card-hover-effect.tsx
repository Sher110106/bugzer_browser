"use client";

import { useState, useRef, useEffect } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

export const HoverEffect = ({
  items,
  className,
}: {
  items: {
    title: string;
    description: string;
    icon: string;
  }[];
  className?: string;
}) => {
  let [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  return (
    <div
      className={cn(
        "grid grid-cols-1 md:grid-cols-2  lg:grid-cols-3  py-10",
        className
      )}
    >
      {items.map((item, idx) => (
        <div
          key={item.title}
          className="relative group  block p-2 h-full w-full"
          onMouseEnter={() => setHoveredIndex(idx)}
          onMouseLeave={() => setHoveredIndex(null)}
        >
          <motion.div
            className="absolute inset-0 rounded-lg bg-slate-800 dark:bg-slate-800/[0.8] opacity-0 group-hover:opacity-100 transition duration-300"
            initial={false}
            animate={{
              scale: hoveredIndex === idx ? 1 : 0.95,
            }}
          />
          <div className="relative z-10 p-5">
            <div className="text-4xl mb-2">{item.icon}</div>
            <motion.div
              initial={false}
              animate={{
                scale: hoveredIndex === idx ? 1.05 : 1,
              }}
              transition={{
                duration: 0.3,
              }}
            >
              <h3 className="font-bold text-xl mb-2">{item.title}</h3>
              <p className="text-sm text-slate-300 mb-2">{item.description}</p>
            </motion.div>
          </div>
        </div>
      ))}
    </div>
  );
};

