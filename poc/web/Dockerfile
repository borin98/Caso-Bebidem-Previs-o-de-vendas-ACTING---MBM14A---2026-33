# Imagem só da web Next.js do POC. Contexto de build: poc/web.
FROM oven/bun:1.4.0 AS build

WORKDIR /app
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

COPY . .
# As rewrites /api/v1/* são resolvidas no build do modo standalone: aponta para o serviço
# `api` da rede interna do compose.
ARG INTERNAL_API_URL=http://api:8000
ENV INTERNAL_API_URL=$INTERNAL_API_URL \
    NEXT_TELEMETRY_DISABLED=1
RUN mkdir -p public && bun run build

FROM node:22-alpine AS runtime

WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
COPY --from=build --chown=node:node /app/public ./public

USER node
EXPOSE 3000
CMD ["node", "server.js"]
