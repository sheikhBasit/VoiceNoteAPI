# Stage 1: Build
FROM node:20-alpine AS builder
WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Install dependencies
COPY pnpm-lock.yaml* ./
COPY package.json ./
RUN pnpm install --frozen-lockfile

COPY . .

# Disable telemetry
ENV NEXT_TELEMETRY_DISABLED 1

RUN pnpm run build

# Stage 2: Production
FROM nginx:alpine
WORKDIR /usr/share/nginx/html

# Copy the build output
# In Next.js with static export, the output is in 'out' directory
COPY --from=builder /app/out .

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
