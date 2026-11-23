import { redirect } from "next/navigation";

// The portal is staff-only; signed-out visitors are sent on to /login by the portal layout.
export default function HomePage() {
  redirect("/dashboard");
}
