import { NextResponse } from 'next/server';

const ENDPOINTS = [
  { method: 'GET', path: '/api/health', description: 'Health check' },
  { method: 'GET', path: '/api/v1/templates', description: 'List all templates' },
  { method: 'GET', path: '/api/v1/mutations', description: 'List all mutations' },
  { method: 'POST', path: '/api/v1/worlds/generate', description: 'Generate a broken repo' },
  { method: 'GET', path: '/api/v1/experiments', description: 'List preset experiments' },
  { method: 'GET', path: '/api/v1/benchmark', description: 'Benchmark stats' },
  { method: 'GET', path: '/api/v1/docs', description: 'API documentation' },
];

export async function GET() {
  return NextResponse.json({ endpoints: ENDPOINTS });
}
