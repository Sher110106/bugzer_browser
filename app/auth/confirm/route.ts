import { type EmailOtpType } from '@supabase/supabase-js';
import { type NextRequest } from 'next/server';
import { createClient } from '@/utils/supabase/server';
import { redirect } from 'next/navigation';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);

  // Extract query parameters
  const token_hash = searchParams.get('token_hash');
  const type = searchParams.get('type') as EmailOtpType | null;
  const next = searchParams.get('next') ?? '/';

  if (token_hash && type) {
    const supabase = await createClient();

    // Verify the token with Supabase
    const { error } = await supabase.auth.verifyOtp({
      type,
      token_hash,
    });

    if (!error) {
      // Redirect to the specified `next` URL or the root of your app
      redirect(next);
    } else {
      console.error('Verification failed:', error.message);
    }
  }

  // If the token is invalid or missing, redirect to an error page
  redirect('/auth/auth-code-error');
}
