import StatsSection from '@/components/stats-section';
import TemplatesSection from '@/components/templates-section';
import WorldGeneratorSection from '@/components/world-generator';
import ExperimentsSection from '@/components/experiments-section';
import ApiDocsSection from '@/components/api-docs-section';
import { Separator } from '@/components/ui/separator';

export default function Home() {
  return (
    <main className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">ForgeLab</h1>
              <p className="text-sm text-muted-foreground">
                Adaptive Environment Factory for AI Coding Agents
              </p>
            </div>
            <a
              href="https://github.com/devrot-ai/enverge-ai"
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-lg border px-4 py-2 text-sm hover:bg-accent"
            >
              GitHub
            </a>
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="container mx-auto px-4 py-8 space-y-8">
        {/* Hero */}
        <section className="text-center py-8">
          <h2 className="text-4xl font-bold tracking-tight">
            Test AI Agents Against Broken Code
          </h2>
          <p className="mt-4 text-lg text-muted-foreground max-w-2xl mx-auto">
            ForgeLab generates realistic broken code repositories, runs AI agents against them,
            independently verifies fixes, and adapts the curriculum based on results.
          </p>
        </section>

        {/* Stats */}
        <StatsSection />

        <Separator />

        {/* Templates and Experiments */}
        <div className="grid gap-8 lg:grid-cols-2">
          <TemplatesSection />
          <ExperimentsSection />
        </div>

        {/* World Generator */}
        <WorldGeneratorSection />

        {/* API Docs */}
        <ApiDocsSection />

        {/* Footer */}
        <footer className="border-t pt-8 pb-4 text-center text-sm text-muted-foreground">
          <p>
            Built with Next.js, Tailwind CSS, and shadcn/ui •{' '}
            <a href="https://github.com/devrot-ai/enverge-ai" className="text-primary hover:underline">
              Source Code
            </a>
          </p>
        </footer>
      </div>
    </main>
  );
}
