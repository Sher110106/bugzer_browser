'use client';

import { signInAction } from "@/app/actions";
import { FormMessage, Message } from "@/components/form-message";
import { SubmitButton } from "@/components/submit-button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import Link from "next/link";
import { motion } from "framer-motion";
import { AnimatedBackground } from "@/components/ui/aceternity/animated-background";
import { useState, useEffect } from "react";

export default function Login(props: { searchParams: Promise<Message> }) {
  const [searchParams, setSearchParams] = useState<Message | null>(null);

  useEffect(() => {
    async function fetchSearchParams() {
      const params = await props.searchParams;
      setSearchParams(params);
    }
    fetchSearchParams();
  }, [props.searchParams]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center py-12 px-4 relative">
      <AnimatedBackground />
      
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 w-full max-w-md"
      >
        <motion.div 
          className="backdrop-blur-sm bg-gray-900/40 border border-gray-800/50 rounded-lg shadow-xl p-8"
          whileHover={{ boxShadow: "0 0 20px rgba(120,119,198,0.3)" }}
          transition={{ duration: 0.3 }}
        >
          <motion.h1 
            className="text-3xl font-bold mb-2 bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2, duration: 0.5 }}
          >
            Sign in
          </motion.h1>
          <motion.p 
            className="text-sm text-foreground mb-6"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3, duration: 0.5 }}
          >
            Don't have an account?{" "}
            <Link className="text-blue-400 font-medium hover:text-blue-300 transition-colors duration-300" href="/sign-up">
              Sign up
            </Link>
          </motion.p>
          
          <form className="flex flex-col space-y-5">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.4, duration: 0.5 }}
            >
              <Label htmlFor="email" className="text-gray-300">Email</Label>
              <Input 
                name="email" 
                placeholder="you@example.com" 
                required 
                className="mt-1 bg-gray-800/50 border-gray-700 focus:border-blue-500 transition-colors duration-300"
              />
            </motion.div>
            
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.5, duration: 0.5 }}
              className="space-y-1"
            >
              <div className="flex justify-between items-center">
                <Label htmlFor="password" className="text-gray-300">Password</Label>
                <Link
                  className="text-xs text-blue-400 hover:text-blue-300 transition-colors duration-300"
                  href="/forgot-password"
                >
                  Forgot Password?
                </Link>
              </div>
              <Input
                type="password"
                name="password"
                placeholder="Your password"
                required
                className="bg-gray-800/50 border-gray-700 focus:border-blue-500 transition-colors duration-300"
              />
            </motion.div>
            
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6, duration: 0.5 }}
              whileHover={{ scale: 1.02 }}
            >
              <SubmitButton 
                pendingText="Signing In..." 
                formAction={signInAction}
                className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 transition-all duration-300"
              >
                Sign in
              </SubmitButton>
            </motion.div>
            
            {searchParams && <FormMessage message={searchParams} />}
          </form>
        </motion.div>
      </motion.div>
    </div>
  );
}
