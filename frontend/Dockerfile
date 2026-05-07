# Next.js 14 standalone build — Railway servis imajı

# ── Stage 1: bağımlılıklar ──────────────────────────────────
FROM node:20-alpine AS deps
WORKDIR /app
RUN apk add --no-cache libc6-compat
COPY package.json package-lock.json* ./
RUN npm ci

# ── Stage 2: build ──────────────────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build sırasında public env değişkenleri client bundle'a yazılır.
# Railway'de "Build Variables" olarak set edilmeli.
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_WS_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_WS_URL=${NEXT_PUBLIC_WS_URL}
ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# ── Stage 3: runtime ───────────────────────────────────────
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Non-root kullanıcı
RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs

# Standalone server + statik varlıklar
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV HOSTNAME=0.0.0.0
ENV PORT=3000

CMD ["node", "server.js"]
