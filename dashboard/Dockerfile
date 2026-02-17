# Stage 1: Build
FROM node:20-alpine AS builder
WORKDIR /app

# Install dependencies based on preferred package manager
COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

# Next.js collects completely anonymous telemetry data about general usage.
# Learn more here: https://nextjs.org/telemetry
# Uncomment the following line in case you want to disable telemetry during the build.
# ENV NEXT_TELEMETRY_DISABLED 1

RUN npm run build

# Stage 2: Production
FROM nginx:alpine
WORKDIR /usr/share/nginx/html

# Copy the build output from the builder stage
# For Next.js static export:
# COPY --from=builder /app/out .

# For Next.js standalone (requires more config, using public for now as prototype)
# We will use Nginx to serve the static assets and proxy requests
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/static ./.next/static
# Note: This is an initial scaffolding. For a real Next.js production app 
# with App Router, we usually run a Node server. 
# However, for this dashboard architecture, we'll start with a minimal setup.

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
