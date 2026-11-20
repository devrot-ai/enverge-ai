import { NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json({
    templates: 14,
    mutations: 37,
    agents: 6,
    tests: 612,
    experiments: 7,
  });
}
