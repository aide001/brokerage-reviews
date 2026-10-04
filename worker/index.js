// Static assets are matched first; this only runs for paths with no exact file.
// It serves index.html for folder URLs ("/", "/blog/") and otherwise 404s.
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname.endsWith("/")) {
      url.pathname += "index.html";
      return env.ASSETS.fetch(new Request(url, request));
    }
    return env.ASSETS.fetch(request);
  },
};
