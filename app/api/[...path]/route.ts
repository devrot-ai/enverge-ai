import { NextRequest, NextResponse } from 'next/server';

// On Vercel, the Python api/index.py handles /api/* and /health routes directly
// This route handler is for local development fallback

export async function GET(request: NextRequest) {
  return NextResponse.json(
    { error: 'API not available. Deploy on Vercel or run Python backend separately.' },
    { status: 502 }
  );
}

export async function POST(request: NextRequest) {
  return NextResponse.json(
    { error: 'API not available. Deploy on Vercel or run Python backend separately.' },
    { status: 502 }
  );
}
