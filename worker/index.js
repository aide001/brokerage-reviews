// Every request runs through this script first (run_worker_first in wrangler.jsonc).
// 1. One address per page: http, www and /index.html redirect (301) to
//    https://<CANONICAL_HOST>/... so search engines see a single version.
// 2. Folder URLs ("/", "/blog/") serve their index.html. Short URLs without
//    ".html" ("/blog", "/brokers/ig") redirect to the real page; else 404.
// 3. The *.workers.dev address is marked noindex (it duplicates the site).
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const canonical = env.CANONICAL_HOST;
    const onWorkersDev = url.hostname.endsWith(".workers.dev");
    if (canonical && !onWorkersDev &&
        (url.protocol === "http:" || url.hostname !== canonical || url.pathname === "/index.html")) {
      url.protocol = "https:";
      url.hostname = canonical;
      if (url.pathname === "/index.html") url.pathname = "/";
      return Response.redirect(url.toString(), 301);
    }
    const res = await serve(request, env, url);
    if (!onWorkersDev) return res;
    const tagged = new Response(res.body, res);
    tagged.headers.set("X-Robots-Tag", "noindex");
    return tagged;
  },
};

async function serve(request, env, url) {
  const res = await env.ASSETS.fetch(request);
  if (res.status !== 404) return res;
  const path = url.pathname;
  if (path.endsWith("/")) {
    url.pathname = path + "index.html";
    return env.ASSETS.fetch(new Request(url, request));
  }
  const last = path.slice(path.lastIndexOf("/") + 1);
  if (!last.includes(".")) {
    for (const candidate of [path + ".html", path + "/index.html"]) {
      url.pathname = candidate;
      const found = await env.ASSETS.fetch(new Request(url, { method: "HEAD" }));
      if (found.ok) return Response.redirect(url.toString(), 301);
    }
  }
  return res;
}
