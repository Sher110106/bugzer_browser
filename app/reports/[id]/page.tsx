import { createClient } from "@/utils/supabase/server";
import { redirect } from "next/navigation";
import ReportDetails from "@/components/ReportDetails";

// The specific type Next.js 15 expects
export default async function ReportDetailPage({ 
  params 
}: { 
  params: Promise<{ id: string }>;
}) {
  try {
    // Await the params promise
    const resolvedParams = await params;
    const reportId = resolvedParams.id;

    const supabase = await createClient();
    const { data: { user } } = await supabase.auth.getUser();

    if (!user) {
      return redirect("/sign-in");
    }

    const { data: report } = await supabase
      .from("reports")
      .select("*, tests(*)")
      .match({
        id: reportId,
        user_id: user.id,
      })
      .single();

    if (!report) {
      return redirect("/reports");
    }

    return <ReportDetails report={report} />;
  } catch (error) {
    console.error("Error in ReportDetailPage:", error);
    return <div>Error loading report.</div>;
  }
}