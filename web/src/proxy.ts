import { auth } from "@/lib/auth";

/**
 * Everything is behind auth except the login page and the auth callbacks
 * themselves. Matcher-based rather than per-route checks so a new route is
 * protected by default — forgetting to add a guard shouldn't open a hole.
 *
 * This is Next 16's `proxy` convention, the rename of what used to be
 * `middleware`. Server actions still re-check the session themselves: this
 * layer is the net, not the lock.
 */
export default auth((req) => {
  if (!req.auth?.user) {
    const url = new URL("/login", req.nextUrl.origin);
    if (req.nextUrl.pathname !== "/") {
      url.searchParams.set("from", req.nextUrl.pathname);
    }
    return Response.redirect(url);
  }
});

export const config = {
  /*
   * Static assets are exempt, images included. Without the extension clause the
   * character portraits in /public are matched by this proxy and redirected to
   * /login, so every <Image> renders as an empty frame — which is exactly what
   * happened. They're anime pictures, not data; serving them unauthenticated is
   * the intended trade.
   */
  matcher: [
    "/((?!api/auth|login|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|avif)$).*)",
  ],
};
