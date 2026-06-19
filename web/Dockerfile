# NaturaScreen web (Next.js). Dev-oriented image: the compose stack runs `npm run dev`
# with the source bind-mounted, so this layer exists to provision node_modules. A
# production build uses `output: "standalone"` (next.config) for a slim runner.
FROM node:22-alpine

WORKDIR /app

# Dependency layer first for caching.
COPY package.json ./
RUN npm install

COPY . .

EXPOSE 3000
CMD ["npm", "run", "dev"]
