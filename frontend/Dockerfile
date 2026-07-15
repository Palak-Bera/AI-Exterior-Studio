# AI Exterior Studio - Frontend (Next.js standalone)

# 1. Dependencies
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install

# 2. Build
FROM node:20-alpine AS builder
WORKDIR /app
# NEXT_PUBLIC_* is inlined at build time. Railway passes matching service
# variables as Docker build-args; local compose passes --build-arg.
ARG NEXT_PUBLIC_API_BASE=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE=$NEXT_PUBLIC_API_BASE
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# 3. Runtime (minimal standalone output)
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    HOSTNAME=0.0.0.0
# PORT defaults to 3000 locally; Railway injects PORT at runtime.
ENV PORT=3000
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
