"use client";

import { Search } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useState, useTransition, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import type { PublicJobFilters } from "@/types/api";

interface CareersFiltersProps {
  options: PublicJobFilters;
  initial: { q: string; department_id: string; location_id: string };
}

export function CareersFilters({ options, initial }: CareersFiltersProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [pending, startTransition] = useTransition();
  const [q, setQ] = useState(initial.q);
  const [department, setDepartment] = useState(initial.department_id);
  const [location, setLocation] = useState(initial.location_id);

  const navigate = (next: { q: string; department_id: string; location_id: string }) => {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(next)) {
      if (value.trim()) params.set(key, value.trim());
    }
    const query = params.toString();
    startTransition(() =>
      router.push(query ? `${pathname}?${query}` : pathname, { scroll: false }),
    );
  };

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    navigate({ q, department_id: department, location_id: location });
  };

  return (
    <form
      role="search"
      onSubmit={onSubmit}
      className="glass grid gap-3 rounded-xl p-3 sm:grid-cols-2 lg:grid-cols-[1fr_200px_200px_auto]"
      aria-busy={pending}
    >
      <div className="relative sm:col-span-2 lg:col-span-1">
        <Search
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
          aria-hidden
        />
        <label htmlFor="careers-q" className="sr-only">
          Search roles
        </label>
        <Input
          id="careers-q"
          type="search"
          placeholder="Search by job title"
          className="pl-9"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
      </div>
      <div>
        <label htmlFor="careers-department" className="sr-only">
          Department
        </label>
        <Select
          id="careers-department"
          value={department}
          onChange={(e) => {
            setDepartment(e.target.value);
            navigate({ q, department_id: e.target.value, location_id: location });
          }}
        >
          <option value="">All departments</option>
          {options.departments.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </Select>
      </div>
      <div>
        <label htmlFor="careers-location" className="sr-only">
          Location
        </label>
        <Select
          id="careers-location"
          value={location}
          onChange={(e) => {
            setLocation(e.target.value);
            navigate({ q, department_id: department, location_id: e.target.value });
          }}
        >
          <option value="">All locations</option>
          {options.locations.map((l) => (
            <option key={l.id} value={l.id}>
              {l.name}
            </option>
          ))}
        </Select>
      </div>
      <Button type="submit" className="sm:col-span-2 lg:col-span-1" disabled={pending}>
        Search
      </Button>
    </form>
  );
}
