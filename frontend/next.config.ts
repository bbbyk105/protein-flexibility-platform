import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "cdn.rcsb.org",
        port: "",
        pathname: "/images/structures/**",
      },
      {
        protocol: "http",
        hostname: "localhost",
        port: "8080",
        pathname: "/api/dsa/jobs/**",
      },
    ],
  },
};

export default nextConfig;
