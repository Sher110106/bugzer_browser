import { createClient } from '@/utils/supabase/server';

const API_BASE_URL = 'https://bugback.onrender.com';

/**
 * API client for server-side operations
 * This is a separate implementation that can run safely in server components
 */
export const serverApiClient = {
  /**
   * Get reports from Supabase directly for server components
   */
  async getAllReports() {
    const supabase = await createClient();
    const { data: reports } = await supabase
      .from('reports')
      .select('*, tests (*)');
    
    return { reports };
  },

  /**
   * Get a specific report from Supabase directly
   */
  async getReport(reportId: string) {
    const supabase = await createClient();
    const { data: report } = await supabase
      .from('reports')
      .select('*, tests (*)')
      .eq('id', reportId)
      .single();
      
    return report;
  },

  /**
   * Delete a report (for server actions)
   */
  async deleteReport(reportId: string) {
    const supabase = await createClient();
    const { error } = await supabase
      .from('reports')
      .delete()
      .eq('id', reportId);
      
    if (error) throw error;
    return { success: true };
  }
};