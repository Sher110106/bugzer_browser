import { createClient } from "@/utils/supabase/server";
import { redirect } from "next/navigation";
import ReportsHistory from "@/components/ReportsHistory";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

export default async function ReportsPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) {
    redirect("/sign-in");
  }

  try {
    // Fetch reports directly from Supabase
    const { data: reports } = await supabase
      .from('reports')
      .select('*, tests(*)')
      .eq('user_id', user.id);
    
    if (!reports || reports.length === 0) {
      return (
        <>
          <Header />
          <div className="container mx-auto py-20 px-4">
            <h1 className="text-3xl font-bold mb-8">No reports found</h1>
            <p>Create a test to generate reports.</p>
          </div>
          <Footer />
        </>
      );
    }

    return (
      <>
        <Header />
        <ReportsHistory reports={reports} />
        <Footer />
      </>
    );
  } catch (error) {
    console.error("Error fetching reports:", error);
    return (
      <>
        <Header />
        <div className="container mx-auto py-20 px-4">
          <h1 className="text-3xl font-bold mb-8">Error loading reports</h1>
          <p>There was an error loading your reports. Please try again later.</p>
        </div>
        <Footer />
      </>
    );
  }
}
