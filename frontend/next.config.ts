import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'cdn.rcsb.org',
        port: '',
        pathname: '/images/structures/**',
      },
    ],
  },
};

export default nextConfig;
