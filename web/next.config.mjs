/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Transpile the three.js ecosystem for the App Router.
  transpilePackages: ["three"],
  output: "standalone",
};

export default nextConfig;
