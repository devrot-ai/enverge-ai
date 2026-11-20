'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { checkHealth, getBenchmark } from '@/lib/api';

export default function StatsSection() {
  const [health, setHealth] = useState<any>(null);
  const [benchmark, setBenchmark] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.allSettled([checkHealth(), getBenchmark()]).then((results) => {
      if (results[0].status === 'fulfilled') setHealth(results[0].value);
      if (results[1].status === 'fulfilled') setBenchmark(results[1].value);
      setLoading(false);
    });
  }, []);

  const stats = [
    { label: 'Templates', value: benchmark?.templates || '-' },
    { label: 'Mutations', value: benchmark?.mutations || '-' },
    { label: 'Agents', value: benchmark?.agents || '-' },
    { label: 'Tests', value: benchmark?.tests || '-' },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {stats.map((stat) => (
        <Card key={stat.label}>
          <CardContent className="pt-6">
            {loading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <>
                <div className="text-2xl font-bold">{stat.value}</div>
                <div className="text-sm text-muted-foreground">{stat.label}</div>
              </>
            )}
          </CardContent>
        </Card>
      ))}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-2">
            <div
              className={`h-3 w-3 rounded-full ${
                health?.status === 'ok' ? 'bg-green-500' : 'bg-red-500'
              }`}
            />
            <span className="text-sm">
              {health?.status === 'ok' ? 'API Online' : 'API Offline'}
            </span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
