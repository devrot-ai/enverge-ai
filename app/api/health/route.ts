import { NextRequest, NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json({ status: 'ok', version: '0.9.0', environment: process.env.FORGELAB_ENV || 'vercel' });
}
