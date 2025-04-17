"use client";
import React, { useRef, useEffect, useState } from "react";
import { useMousePosition } from "@/lib/hooks/use-mouse-position";

interface SparklesProps {
  id?: string;
  background?: string;
  minSize?: number;
  maxSize?: number;
  particleDensity?: number;
  className?: string;
  particleColor?: string;
  particleType?: "circle" | "square" | "triangle" | "line";
  speed?: number;
}

export const SparklesCore: React.FC<SparklesProps> = ({
  id = "tsparticles",
  background = "#000",
  minSize = 0.6,
  maxSize = 1.4,
  particleDensity = 100,
  className = "",
  particleColor = "#FFFFFF",
  particleType = "circle",
  speed = 1,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const mousePosition = useMousePosition();
  const [context, setContext] = useState<CanvasRenderingContext2D | null>(null);
  const [particles, setParticles] = useState<any[]>([]);
  const [width, setWidth] = useState(0);
  const [height, setHeight] = useState(0);

  useEffect(() => {
    if (canvasRef.current) {
      const canvas = canvasRef.current;
      const ctx = canvas.getContext("2d");
      setContext(ctx);

      const handleResize = () => {
        if (canvas) {
          setWidth(canvas.offsetWidth);
          setHeight(canvas.offsetHeight);
          canvas.width = canvas.offsetWidth;
          canvas.height = canvas.offsetHeight;
        }
      };

      handleResize();
      window.addEventListener("resize", handleResize);

      return () => {
        window.removeEventListener("resize", handleResize);
      };
    }
  }, []);

  useEffect(() => {
    if (context && width && height) {
      const particleCount = Math.floor((width * height) / 10000) * particleDensity;
      const newParticles = Array.from({ length: particleCount }, () => ({
        x: Math.random() * width,
        y: Math.random() * height,
        size: Math.random() * (maxSize - minSize) + minSize,
        speedX: (Math.random() - 0.5) * speed,
        speedY: (Math.random() - 0.5) * speed,
      }));

      setParticles(newParticles);
    }
  }, [context, width, height, particleDensity, minSize, maxSize, speed]);

  useEffect(() => {
    if (context && particles.length) {
      let animationFrameId: number;

      const animate = () => {
        context.clearRect(0, 0, width, height);
        context.fillStyle = background;
        context.fillRect(0, 0, width, height);

        particles.forEach((particle) => {
          context.beginPath();
          context.fillStyle = particleColor;

          switch (particleType) {
            case "square":
              context.rect(particle.x, particle.y, particle.size, particle.size);
              break;
            case "triangle":
              context.moveTo(particle.x, particle.y);
              context.lineTo(particle.x + particle.size, particle.y);
              context.lineTo(particle.x + particle.size / 2, particle.y - particle.size);
              break;
            case "line":
              context.moveTo(particle.x, particle.y);
              context.lineTo(particle.x + particle.size, particle.y);
              break;
            default:
              context.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
          }

          context.fill();

          particle.x += particle.speedX;
          particle.y += particle.speedY;

          if (particle.x < 0 || particle.x > width) particle.speedX *= -1;
          if (particle.y < 0 || particle.y > height) particle.speedY *= -1;

          const dx = mousePosition.x - particle.x;
          const dy = mousePosition.y - particle.y;
          const distance = Math.sqrt(dx * dx + dy * dy);
          const maxDistance = 100;

          if (distance < maxDistance) {
            const ax = dx / distance;
            const ay = dy / distance;
            const force = (maxDistance - distance) / maxDistance;

            particle.speedX += ax * force * 0.2;
            particle.speedY += ay * force * 0.2;
          }
        });

        animationFrameId = requestAnimationFrame(animate);
      };

      animate();

      return () => {
        cancelAnimationFrame(animationFrameId);
      };
    }
  }, [context, particles, width, height, background, particleColor, particleType, mousePosition]);

  return (
    <canvas
      ref={canvasRef}
      id={id}
      className={className}
      style={{
        width: "100%",
        height: "100%",
        position: "absolute",
        top: 0,
        left: 0,
      }}
    />
  );
};

