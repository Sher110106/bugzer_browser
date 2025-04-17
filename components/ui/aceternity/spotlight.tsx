"use client";
import React, { useRef, useState, useEffect } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

export const Spotlight = ({
  className = "",
  fill = "white",
}: {
  className?: string;
  fill?: string;
}) => {
  const divRef = useRef<HTMLDivElement>(null);
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [isHovered, setIsHovered] = useState(false);

  useEffect(() => {
    const handleMouseMove = (event: MouseEvent) => {
      if (divRef.current) {
        const rect = divRef.current.getBoundingClientRect();
        setMousePosition({
          x: event.clientX - rect.left,
          y: event.clientY - rect.top,
        });
      }
    };

    const handleMouseEnter = () => {
      setIsHovered(true);
    };

    const handleMouseLeave = () => {
      setIsHovered(false);
    };

    const div = divRef.current;
    if (div) {
      div.addEventListener("mousemove", handleMouseMove);
      div.addEventListener("mouseenter", handleMouseEnter);
      div.addEventListener("mouseleave", handleMouseLeave);
    }

    return () => {
      if (div) {
        div.removeEventListener("mousemove", handleMouseMove);
        div.removeEventListener("mouseenter", handleMouseEnter);
        div.removeEventListener("mouseleave", handleMouseLeave);
      }
    };
  }, []);

  return (
    <div
      ref={divRef}
      className={cn(
        "h-full w-full absolute inset-0 z-0 overflow-hidden",
        className
      )}
    >
      <motion.div
        className="absolute inset-0 opacity-0"
        animate={{
          opacity: isHovered ? 1 : 0,
        }}
        transition={{
          duration: 0.3,
        }}
      >
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: `radial-gradient(circle at ${mousePosition.x}px ${mousePosition.y}px, ${fill}, transparent 80%)`,
          }}
        />
      </motion.div>
    </div>
  );
};

