import { NextResponse } from 'next/server';

const EXPERIMENTS = [
  { id: 'A', name: 'Static vs Adaptive Curriculum', description: 'Compare static task selection vs adaptive curriculum.' },
  { id: 'B', name: 'Random vs Validated Environments', description: 'Compare randomly generated vs validated environments.' },
  { id: 'C', name: 'Generic vs Targeted Challenges', description: 'Compare generic tasks vs targeted skill-building tasks.' },
  { id: 'D', name: 'Single-agent vs Independent Verification', description: 'Compare single-agent verification vs independent test execution.' },
  { id: 'ablation_tools', name: 'Tool Ablation Study', description: 'Measure impact of removing tools one by one.' },
  { id: 'difficulty_scaling', name: 'Difficulty Scaling', description: 'Measure agent performance across difficulty levels.' },
  { id: 'cross_template', name: 'Cross-Template Generalization', description: 'Run same agent across all templates.' },
];

export async function GET() {
  return NextResponse.json({ experiments: EXPERIMENTS });
}
