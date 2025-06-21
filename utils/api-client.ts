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
    options: RequestInit = {},
    parseResponse: boolean = true
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
      let errorText = await response.text();
      try {
        // Try to parse the error as JSON
        const errorJson = JSON.parse(errorText);
        throw new Error(errorJson.detail || `API error: ${response.status} ${response.statusText}`);
      } catch (e) {
        // If parsing fails, use the raw error text
        throw new Error(`API error: ${response.status} ${response.statusText} - ${errorText}`);
      }
    }
    
    if (!parseResponse) {
      return { success: true } as T;
    }
    
    // Try to get text content first
    const textResponse = await response.text();
    
    // If the response is empty, return a simple success object
    if (!textResponse || textResponse.trim() === '') {
      return { success: true } as T;
    }
    
    // Try to parse as JSON, but return raw response if that fails
    try {
      return JSON.parse(textResponse);
    } catch (e) {
      return { success: true, message: textResponse } as T;
    }
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
    user_id?: string;
  }) {
    // Format the test_id as a proper UUID if needed
    let formattedTestId = data.test_id;
    
    // Remove any non-UUID characters
    formattedTestId = formattedTestId.replace(/[^a-zA-Z0-9-]/g, '');
    
    // If it's a UUID without dashes but with the right length, format it correctly
    if (formattedTestId.length === 32 && !formattedTestId.includes('-')) {
      formattedTestId = `${formattedTestId.slice(0, 8)}-${formattedTestId.slice(8, 12)}-${formattedTestId.slice(12, 16)}-${formattedTestId.slice(16, 20)}-${formattedTestId.slice(20)}`;
    }
    
    const cleanData = {
      ...data,
      test_id: formattedTestId
    };
    
    // Use enhanced fetch with parseResponse=false to avoid UUID serialization issues
    return this.fetch('/reports', {
      method: 'POST',
      body: JSON.stringify(cleanData),
    }, false);
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