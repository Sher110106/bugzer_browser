import { createClient } from "@/utils/supabase/server";
import { redirect } from "next/navigation";
import FeedbackForm from "@/components/FeedbackForm";

type Props = {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}

export default async function ReportPage({ params, searchParams }: Props) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) {
    redirect("/sign-in");
  }

  // Since you're using searchParams.id, ensure you await it correctly
  const searchParamsResult = await searchParams;
  const reportId = searchParamsResult.id as string | undefined;
  if (!reportId) {
    redirect("/reports");
  }

  // Verify the report exists and belongs to the user
  const { data: report } = await supabase
    .from('reports')
    .select('*')
    .eq('id', reportId)
    .eq('user_id', user.id)
    .single();

  if (!report) {
    redirect("/reports");
  }

  return <FeedbackForm userId={user.id} reportId={reportId} />;
}
