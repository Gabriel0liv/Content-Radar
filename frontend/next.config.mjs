/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // We can add redirect from / to /content here
  async redirects() {
    return [
      {
        source: "/",
        destination: "/content",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
