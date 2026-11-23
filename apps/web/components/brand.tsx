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
    <span className={cn("flex min-w-0 items-center gap-2 font-semibold", className)}>
      {logoUrl ? (
        // A data URL from the API; next/image cannot optimise those.
        // eslint-disable-next-line @next/next/no-img-element
        <img src={logoUrl} alt="" className="h-8 w-8 shrink-0 rounded-md object-contain" />
      ) : (
        <span
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary text-sm text-primary-foreground"
          aria-hidden
        >
          {initials(name)}
        </span>
      )}
      {showName && <span className="truncate">{name}</span>}
    </span>
  );
}
