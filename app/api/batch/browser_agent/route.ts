import { NextRequest, NextResponse } from 'next/server';

// Demo user ID for development
const DEMO_USER_ID = 'demo_user';

export async function POST(request: NextRequest) {
  try {
    // Get the request body
    const body = await request.json();
    
    // Add user_id to the request - using demo user for simplicity
    const requestBody = {
      ...body,
      user_id: DEMO_USER_ID
    };
    
    // Get the API URL from environment variables
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    
    // Forward the request to the backend API
    const response = await fetch(`${apiUrl}/api/batch/browser_agent`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });
    
    // Get the response data
    const data = await response.json();
    
    // Return the response
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error in batch browser agent API route:', error);
    
    return NextResponse.json(
      { 
        status: 'error', 
        message: error instanceof Error ? error.message : 'An unexpected error occurred' 
      },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  // Get the test_id from query params
  const searchParams = request.nextUrl.searchParams;
  const testId = searchParams.get('test_id');
  
  if (!testId) {
    return NextResponse.json(
      { status: 'error', message: 'test_id is required' },
      { status: 400 }
    );
  }
  
  try {
    // Get the API URL from environment variables
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    
    // Forward the request to the backend API - using demo user for simplicity
    const response = await fetch(`${apiUrl}/api/batch/status/${testId}?user_id=${DEMO_USER_ID}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    // Get the response data
    const data = await response.json();
    
    // Return the response
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error in batch status API route:', error);
    
    return NextResponse.json(
      { 
        status: 'error', 
        message: error instanceof Error ? error.message : 'An unexpected error occurred' 
      },
      { status: 500 }
    );
  }
} 