/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  images: {
    domains: ['logo.clearbit.com', 'unavatar.io'],
  },
}

module.exports = nextConfig
