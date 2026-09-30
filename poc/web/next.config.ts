import type { NextConfig } from "next";

// Resolved when the server starts the build output; in Docker it is baked at build time.
const apiUrl = process.env.INTERNAL_API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  // `next dev` só: permite abrir o painel em http://127.0.0.1:3000 (mesmo endereço do Docker).
  allowedDevOrigins: ["127.0.0.1"],
  async rewrites() {
    return [{ source: "/api/v1/:path*", destination: `${apiUrl}/api/v1/:path*` }];
  },
};

export default nextConfig;
