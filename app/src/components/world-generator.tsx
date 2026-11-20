'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { generateWorld, getTemplates, getMutations } from '@/lib/api';

export default function WorldGeneratorSection() {
  const [templates, setTemplates] = useState<string[]>([]);
  const [mutations, setMutations] = useState<any[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [selectedMutation, setSelectedMutation] = useState('');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([getTemplates(), getMutations()]).then(([t, m]) => {
      setTemplates(t);
      setMutations(m);
      if (t.length > 0) setSelectedTemplate(t[0]);
    }).catch(() => {});
  }, []);

  const handleGenerate = async () => {
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const data = await generateWorld(selectedTemplate, selectedMutation || null);
      setResult(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>World Generator</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <label className="text-sm font-medium">Template</label>
            <select
              value={selectedTemplate}
              onChange={(e) => setSelectedTemplate(e.target.value)}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background"
            >
              {templates.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Mutation (optional)</label>
            <select
              value={selectedMutation}
              onChange={(e) => setSelectedMutation(e.target.value)}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background"
            >
              <option value="">Auto-select</option>
              {mutations.map((m) => (
                <option key={m.mutation_id} value={m.mutation_id}>
                  {m.name || m.mutation_id}
                </option>
              ))}
            </select>
          </div>
        </div>
        <Button onClick={handleGenerate} disabled={loading || !selectedTemplate}>
          {loading ? 'Generating...' : 'Generate World'}
        </Button>
        {error && (
          <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
            {error}
          </div>
        )}
        {result && (
          <div className="rounded-md bg-muted p-4">
            <div className="mb-2 flex items-center gap-2">
              <Badge variant="default">✓ Generated</Badge>
              <span className="font-mono text-sm">{result.world_id}</span>
            </div>
            <pre className="max-h-60 overflow-auto text-xs font-mono">
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
