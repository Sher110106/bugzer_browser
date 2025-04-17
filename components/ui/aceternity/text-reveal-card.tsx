"use client";
import React, { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

export const TextRevealCard = ({
  text,
  revealText,
  className,
}: {
  text: string;
  revealText: string;
  className?: string;
}) => {
  const [isHovered, setIsHovered] = useState(false);
  const [textWidth, setTextWidth] = useState(0);
  const [revealTextWidth, setRevealTextWidth] = useState(0);
  const textRef = useRef<HTMLDivElement>(null);
  const revealTextRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (textRef.current) {
      setTextWidth(textRef.current.offsetWidth);
    }
    if (revealTextRef.current) {
      setRevealTextWidth(revealTextRef.current.offsetWidth);
    }
  }, [text, revealText]);

  return (
    <div
      className={cn(
        "relative overflow-hidden w-full max-w-sm py-4 px-6 rounded-lg bg-slate-800 cursor-pointer",
        className
      )}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <motion.div
        ref={textRef}
        initial={{ x: 0 }}
        animate={{ x: isHovered ? -textWidth - 16 : 0 }}
        transition={{ duration: 0.5, ease: "easeInOut" }}
        className="text-white"
      >
        {text}
      </motion.div>
      <motion.div
        ref={revealTextRef}
        initial={{ x: textWidth + 16 }}
        animate={{ x: isHovered ? 0 : textWidth + 16 }}
        transition={{ duration: 0.5, ease: "easeInOut" }}
        className="absolute top-4 left-6 text-white"
      >
        {revealText}
      </motion.div>
    </div>
  );
};

