"use server";

import { revalidatePath } from "next/cache";

import { auth } from "@/lib/auth";
import { isJobStatus, setJobStatus } from "@/lib/jobs";
import { GITHUB_REPO } from "@/lib/env-status";
import {
  isSettingKey,
  saveLinkedInCookies,
  saveSettings,
  type Settings,
} from "@/lib/settings";

/**
 * A server action is its own public endpoint — the page that rendered the form
 * proves nothing about who is calling it. Every action re-checks the session
 * even though `proxy.ts` already gated the route.
 */
async function requireSession() {
  const session = await auth();
  if (!session?.user?.email) throw new Error("Not signed in");
  return session;
}

export async function updateStatus(id: string, status: string) {
  await requireSession();
  if (!isJobStatus(status)) throw new Error(`Unknown status: ${status}`);
  if (!id) throw new Error("Missing job id");

  await setJobStatus(id, status);
  revalidatePath("/");
}

export async function savePreferences(formData: FormData) {
  await requireSession();

  const updates: Partial<Settings> = {};
  for (const [key, value] of formData.entries()) {
    if (isSettingKey(key)) updates[key] = String(value);
  }

  // An unchecked checkbox sends nothing at all, so the toggles have to be
  // written explicitly from the form's hidden companions rather than inferred
  // from what arrived — otherwise turning a source off would never persist.
  for (const key of ["ENABLE_IIMJOBS", "ENABLE_MYCAREERSFUTURE", "ENABLE_LINKEDIN", "ENABLE_GOOGLE_JOBS"] as const) {
    updates[key] = formData.get(key) === "true" ? "true" : "false";
  }

  await saveSettings(updates);
  revalidatePath("/preferences");
  revalidatePath("/run");
  revalidatePath("/alerts");
}

/**
 * Fire the scheduled workflow by hand.
 *
 * dashboard.py ran `subprocess.Popen(main.py)` and streamed stdout. That can't
 * work here — the pipeline drives Playwright for up to 20 minutes, which is not
 * a web request. Triggering the GitHub Actions workflow gets the same outcome
 * through the mechanism that already runs it twice a day.
 */
export async function triggerRun(): Promise<{ ok: boolean; message: string }> {
  await requireSession();

  const token = process.env.GITHUB_DISPATCH_TOKEN;
  if (!token) {
    return {
      ok: false,
      message:
        "No GITHUB_DISPATCH_TOKEN set. Add a fine-grained token with Actions: write on this repo to Vercel's environment variables.",
    };
  }

  const res = await fetch(
    `https://api.github.com/repos/${GITHUB_REPO}/actions/workflows/job_alert.yml/dispatches`,
    {
      method: "POST",
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Bearer ${token}`,
        "X-GitHub-Api-Version": "2022-11-28",
      },
      body: JSON.stringify({ ref: "main" }),
    },
  );

  // 204 No Content is the success case for a workflow dispatch.
  if (res.status === 204) {
    return { ok: true, message: "Run queued. It takes 10–20 minutes; the board updates as it goes." };
  }

  const detail = await res.text().catch(() => "");
  return {
    ok: false,
    message: `GitHub returned ${res.status}. ${detail.slice(0, 200)}`,
  };
}

export async function storeLinkedInCookies(raw: string) {
  await requireSession();
  const result = await saveLinkedInCookies(raw);
  if (result.ok) revalidatePath("/linkedin");
  return result;
}
