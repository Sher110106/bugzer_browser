import { createClient as createBrowserClient } from '@/utils/supabase/client';

const API_BASE_URL = 'https://bugback.onrender.com';

/**
 * API client for making requests to the backend (client-side)
 */
export const apiClient = {
  /**
   * Get auth token from Supabase session - client side only
   */
  async getAuthToken(): Promise<string | null> {
    const supabase = createBrowserClient();
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token || null;
  },

  /**
   * Make an authenticated request to the API
   */
  async fetch<T>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<T> {
    const token = await this.getAuthToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }
    
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...options.headers,
    };
    
    const fetchOptions: RequestInit = {
      ...options,
      headers,
      credentials: 'include',
      mode: 'cors',
    };
    
    const response = await fetch(`${API_BASE_URL}${endpoint}`, fetchOptions);
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }
    
    return response.json();
  },

  // Tests API

  async getAllTests() {
    return this.fetch('/tests');
  },

  async getTest(testId: string) {
    return this.fetch(`/tests/${testId}`);
  },

  async createTest(data: { url: string; context: string }) {
    return this.fetch('/tests', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async updateTest(testId: string, data: { url?: string; context?: string; alert_status?: string }) {
    return this.fetch(`/tests/${testId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  async deleteTest(testId: string) {
    return this.fetch(`/tests/${testId}`, {
      method: 'DELETE',
    });
  },

  // Reports API

  async getAllReports() {
    return this.fetch('/reports');
  },

  async getReport(reportId: string) {
    return this.fetch(`/reports?report_id=${reportId}`);
  },

  async createReport(data: { 
    test_id: string; 
    results: any; 
    completed_at?: string; 
    duration?: number;
  }) {
    return this.fetch('/reports', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async deleteReport(reportId: string) {
    return this.fetch(`/reports/${reportId}`, {
      method: 'DELETE',
    });
  },

  // Feedback API (custom extension for updating report feedback)

  async updateReportFeedback(reportId: string, feedback: {
    category: string;
    rating: number;
    title: string;
    description: string;
    created_at: string;
  }) {
    // This would need a corresponding endpoint on your backend
    // For now, using Supabase directly for this operation
    const supabase = createBrowserClient();
    return supabase
      .from('reports')
      .update({ feedback })
      .eq('id', reportId);
  },

  // System API

  async healthCheck() {
    return this.fetch('/health');
  }
};