"use client";

import { useEffect, useRef } from "react";
import { motion, useAnimationFrame } from "framer-motion";

export const InfiniteMovingCards = ({
  items,
  direction = "left",
  speed = "fast",
  pauseOnHover = true,
}: {
  items: {
    title: string;
    description: string;
    icon: string;
  }[];
  direction?: "left" | "right";
  speed?: "fast" | "normal" | "slow";
  pauseOnHover?: boolean;
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useAnimationFrame(() => {
    if (!containerRef.current || !scrollRef.current) return;
    
    const scrollSpeed = {
      slow: 0.5,
      normal: 1,
      fast: 2,
    }[speed];

    const currentScroll = scrollRef.current.scrollLeft;
    const maxScroll = scrollRef.current.scrollWidth - scrollRef.current.clientWidth;
    
    if (direction === "left") {
      if (currentScroll <= 0) {
        scrollRef.current.scrollLeft = maxScroll;
      } else {
        scrollRef.current.scrollLeft -= scrollSpeed;
      }
    } else {
      if (currentScroll >= maxScroll) {
        scrollRef.current.scrollLeft = 0;
      } else {
        scrollRef.current.scrollLeft += scrollSpeed;
      }
    }
  });

  return (
    <div ref={containerRef} className="relative overflow-hidden">
      <div 
        ref={scrollRef}
        className="flex gap-4 overflow-x-hidden w-full py-4 scrollbar-none"
        style={{ 
          maskImage: 'linear-gradient(to right, transparent, black 10%, black 90%, transparent)',
          WebkitMaskImage: 'linear-gradient(to right, transparent, black 10%, black 90%, transparent)'
        }}
      >
        <div className="flex gap-4 min-w-full">
          {[...items, ...items, ...items].map((item, idx) => (
            <motion.div
              key={idx}
              className="relative flex-shrink-0 w-[280px] sm:w-[320px] rounded-xl border border-neutral-700 bg-slate-800 p-6 cursor-pointer group"
              whileHover={{ scale: 1.02 }}
              transition={{ duration: 0.2 }}
              style={{
                transformStyle: "preserve-3d",
              }}
            >
              <div className="relative z-10">
                <div className="text-4xl mb-4 transform transition-transform group-hover:scale-110">
                  {item.icon}
                </div>
                <h3 className="font-bold text-xl mb-2 text-white">
                  {item.title}
                </h3>
                <p className="text-sm text-gray-300 line-clamp-3">
                  {item.description}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
};

