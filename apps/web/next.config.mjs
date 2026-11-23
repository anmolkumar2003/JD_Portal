/** @type {import('next').NextConfig} */
const internalApi = process.env.INTERNAL_API_URL ?? "http://localhost:8001";

const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  output: "standalone",
  // The browser talks to the API on the same origin, so the refresh cookie is first-party.
  // In production Caddy routes /api/* straight to the API and this proxy is not used.
  async rewrites() {
    return [
      { source: "/api/v1/:path*", destination: `${internalApi}/api/v1/:path*` },
      { source: "/health", destination: `${internalApi}/health` },
    ];
  },
};

export default nextConfig;
