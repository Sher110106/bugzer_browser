'use client'
import { useState, useEffect } from "react";
import { signUpAction } from "@/app/actions";
import { FormMessage, Message } from "@/components/form-message";
import { SubmitButton } from "@/components/submit-button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import Link from "next/link";


export default function Signup(props: { searchParams: Promise<Message>; }) {
  const [searchParams, setSearchParams] = useState<Message | null>(null);

  useEffect(() => {
    async function fetchSearchParams() {
      const params = await props.searchParams;
      setSearchParams(params);
    }
    fetchSearchParams();
  }, [props.searchParams]);

  if (searchParams && "message" in searchParams) {
    return (
      <div className="w-full flex-1 flex items-center h-screen sm:max-w-md justify-center gap-2 p-4">
        <FormMessage message={searchParams} />
      </div>
    );
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    try {
      const formData = new FormData(event.target as HTMLFormElement);
      await signUpAction(formData);
    } catch (error) {
      console.error("An error occurred during sign-up:", error);
    }
  };

  return (
    <>
      <form
        onSubmit={handleSubmit}
        className="flex flex-col min-w-64 max-w-64 mx-auto"
      >
        <h1 className="text-2xl font-medium">Sign up</h1>
        <p className="text-sm text text-foreground">
          Already have an account?{" "}
          <Link className="text-primary font-medium underline" href="/sign-in">
            Sign in
          </Link>
        </p>
        <div className="flex flex-col gap-2 [&>input]:mb-3 mt-8">
          <Label htmlFor="email">Email</Label>
          <Input name="email" placeholder="you@example.com" required />
          <Label htmlFor="password">Password</Label>
          <Input
            type="password"
            name="password"
            placeholder="Your password"
            minLength={6}
            required
          />
          <SubmitButton pendingText="Signing up...">
            Sign up
          </SubmitButton>
          {searchParams && <FormMessage message={searchParams} />}
        </div>
      </form>
     
    </>
  );
}