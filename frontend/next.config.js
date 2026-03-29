/** @type {import('next').NextConfig} */
const isProd = process.env.NODE_ENV === 'production'

const nextConfig = {
  // 'export' for S3/CloudFront in prod, 'standalone' for Docker in dev
  output: isProd ? 'export' : 'standalone',
  images: {
    // next/image doesn't work with static export — use unoptimized
    unoptimized: isProd,
    domains: ['logo.clearbit.com', 'unavatar.io'],
  },
  // Ensure trailing slash for S3 routing
  trailingSlash: isProd,
}

module.exports = nextConfig
