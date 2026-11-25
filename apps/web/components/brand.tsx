import { cn } from "@/lib/utils";

function initials(name: string): string {
  const letters = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
  return letters || "HR";
}

interface BrandProps {
  name: string;
  logoUrl: string | null;
  showName?: boolean;
  className?: string;
}

/** Organization logo (or initials) and name, from Settings > Organization. */
export function Brand({ name, logoUrl, showName = true, className }: BrandProps) {
  return (
    <span
      className={cn("flex min-w-0 items-center gap-2.5 font-semibold tracking-tight", className)}
      title={name}
    >
      {logoUrl ? (
        // Data URL from the API; next/image cannot optimise those.
        // Keep natural aspect ratio — mark is wider than tall (circle + dash).
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={logoUrl}
          alt=""
          className="h-9 w-9 shrink-0 object-contain"
        />
      ) : (
        <span
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-control bg-gradient-brand text-sm text-primary-foreground"
          aria-hidden
        >
          {initials(name)}
        </span>
      )}
      {showName && (
        <span className="min-w-0 text-sm leading-snug [overflow-wrap:anywhere]">{name}</span>
      )}
    </span>
  );
}
