"use client";

import { useState, useTransition } from "react";

import { storeLinkedInCookies } from "@/app/actions";

export function CookieForm() {
  const [raw, setRaw] = useState("");
  const [pending, start] = useTransition();
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);

  return (
    <div>
      <label className="block">
        <span className="mb-1.5 block text-xs font-medium text-dim">
          Paste LinkedIn cookies JSON
        </span>
        <textarea
          className="field h-44 w-full resize-y px-3 py-2 font-mono text-xs"
          value={raw}
          onChange={(e) => {
            setRaw(e.target.value);
            setResult(null);
          }}
          placeholder='[{"name": "li_at", "value": "AQE...", "domain": ".linkedin.com"}]'
        />
      </label>

      <button
        type="button"
        disabled={pending || raw.trim() === ""}
        className="btn-primary mt-3 px-5 py-2.5 text-sm"
        onClick={() =>
          start(async () => {
            const r = await storeLinkedInCookies(raw);
            setResult(r);
            if (r.ok) setRaw("");
          })
        }
      >
        {pending ? "Saving…" : "💾 Save Cookies"}
      </button>

      {result ? (
        <p className={`mt-3 text-sm ${result.ok ? "text-[#6ee7b7]" : "text-amber"}`}>
          {result.ok ? "✅ " : "⚠️ "}
          {result.message}
          {result.ok ? " Now enable LinkedIn Jobs in Preferences." : ""}
        </p>
      ) : null}
    </div>
  );
}
