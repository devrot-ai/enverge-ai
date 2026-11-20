import { NextResponse } from 'next/server';

const TEMPLATES = [
  'task_manager_api', 'data_pipeline', 'flask_app', 'express_api', 'django_app',
  'typescript_api', 'go_service', 'react_app', 'spring_service', 'config_manager',
  'browser_automation', 'database_query', 'api_integration', 'dsl'
];

export async function GET() {
  return NextResponse.json({ templates: TEMPLATES });
}
