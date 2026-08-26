/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // API 反代:前端 /api/* → FastAPI 后端(开发期)
  async rewrites() {
    return [
      {
        source: "/api/be/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000"}/:path*`,
      },
    ];
  },
};

export default nextConfig;
