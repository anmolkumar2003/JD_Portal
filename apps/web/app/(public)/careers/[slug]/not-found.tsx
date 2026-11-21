import { FileQuestion } from "lucide-react";
import Link from "next/link";

import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";

export default function JobNotFound() {
  return (
    <div className="container py-14">
      <EmptyState
        icon={FileQuestion}
        title="This role is no longer open"
        description="It may have been filled or closed. Take a look at our other open roles."
        action={
          <Button asChild>
            <Link href="/careers">See open roles</Link>
          </Button>
        }
      />
    </div>
  );
}
