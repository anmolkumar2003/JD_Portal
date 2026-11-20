import { ApiStatus } from "@/components/api-status";

export default function HomePage() {
  return (
    <div className="mx-auto max-w-xl space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">HR Recruitment Portal</h1>
        <p className="text-muted-foreground">
          Development scaffold. The card below checks the API health endpoint.
        </p>
      </div>
      <ApiStatus />
    </div>
  );
}
