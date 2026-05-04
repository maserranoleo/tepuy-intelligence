"use client";

import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

export default function TopBar() {
  const router = useRouter();
  const supabase = createClient();

  async function handleSignOut() {
    await supabase.auth.signOut();
    router.push("/login");
    router.refresh();
  }

  return (
    <header className="topbar">
      <div className="topbar-brand">
        <span className="topbar-brand-glyph">◭</span>
        <span>Tepuy Intelligence</span>
      </div>
      <div className="topbar-divider" />
      <div className="topbar-context">
        <span className="topbar-context-region">VEN</span> · Energy Theatre
      </div>
      <button
        type="button"
        className="btn-secondary"
        onClick={handleSignOut}
      >
        Sign Out
      </button>
    </header>
  );
}
