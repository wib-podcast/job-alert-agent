import "server-only";

/**
 * Whether each secret is configured — never the value.
 *
 * dashboard.py let you paste API keys into a form and wrote them to `.env`.
 * That can't work here and shouldn't pretend to: the scheduled run reads
 * GitHub Secrets, so a key saved in this app would look stored and never be
 * used by the thing that needs it. The board reports status and says where to
 * set it instead.
 */
export interface SecretStatus {
  key: string;
  label: string;
  configured: boolean;
  where: string;
  why: string;
}

export function secretStatuses(): SecretStatus[] {
  return [
    {
      key: "ANTHROPIC_API_KEY",
      label: "Anthropic API key",
      configured: Boolean(process.env.ANTHROPIC_API_KEY),
      where: "GitHub → Settings → Secrets → Actions",
      why: "Scores every scraped job. Without it, scraping still works and every job stays at 0.0.",
    },
    {
      key: "RESEND_API_KEY",
      label: "Resend API key",
      configured: Boolean(process.env.RESEND_API_KEY),
      where: "GitHub → Settings → Secrets → Actions",
      why: "Sends the digest. Without it the run scrapes and scores, then skips the email.",
    },
    {
      key: "GITHUB_DISPATCH_TOKEN",
      label: "GitHub dispatch token",
      configured: Boolean(process.env.GITHUB_DISPATCH_TOKEN),
      where: "Vercel → Project → Environment Variables",
      why: "Lets the Run Agent button trigger the workflow. A fine-grained token with Actions: write on this repo only.",
    },
  ];
}

export const GITHUB_REPO = process.env.GITHUB_REPO ?? "wib-podcast/job-alert-agent";
