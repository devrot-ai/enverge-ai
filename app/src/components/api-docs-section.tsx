'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { getDocs } from '@/lib/api';

export default function ApiDocsSection() {
  const [endpoints, setEndpoints] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDocs().then((data) => {
      setEndpoints(data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const methodColor = (method: string) => {
    switch (method.toUpperCase()) {
      case 'GET': return 'bg-green-500/10 text-green-500';
      case 'POST': return 'bg-blue-500/10 text-blue-500';
      case 'PUT': return 'bg-yellow-500/10 text-yellow-500';
      case 'DELETE': return 'bg-red-500/10 text-red-500';
      default: return 'bg-gray-500/10 text-gray-500';
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>API Endpoints</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : (
          <div className="space-y-2">
            {endpoints.map((ep, i) => (
              <div
                key={i}
                className="flex items-center gap-3 rounded-lg border p-3 font-mono text-sm"
              >
                <Badge className={methodColor(ep.method)} variant="outline">
                  {ep.method}
                </Badge>
                <span className="flex-1">{ep.path}</span>
                <span className="text-muted-foreground">{ep.description}</span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
