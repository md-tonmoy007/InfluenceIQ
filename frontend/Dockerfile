# Stage 1: Build
FROM node:24.16.0-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Runner
FROM node:24.16.0-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

# Copy necessary files for standalone output or standard build
COPY --from=builder /app/next.config.ts ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

EXPOSE 3000
CMD ["npm", "start"]
