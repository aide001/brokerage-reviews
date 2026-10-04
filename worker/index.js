// Static assets are matched first; this only runs for paths with no exact file.
// Folder URLs ("/", "/blog/") serve their index.html. Short URLs without ".html"
// ("/blog", "/blog/headlines") redirect to the real page; anything else 404s.
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;
    if (path.endsWith("/")) {
      url.pathname = path + "index.html";
      return env.ASSETS.fetch(new Request(url, request));
    }
    const last = path.slice(path.lastIndexOf("/") + 1);
    if (!last.includes(".")) {
      for (const candidate of [path + ".html", path + "/index.html"]) {
        url.pathname = candidate;
        const res = await env.ASSETS.fetch(new Request(url, { method: "HEAD" }));
        if (res.ok) return Response.redirect(url.toString(), 301);
      }
    }
    return env.ASSETS.fetch(request);
  },
};
