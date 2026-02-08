FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install --legacy-peer-deps

COPY . .

# .env.production 파일에서 NEXT_PUBLIC_* 변수를 읽어 빌드에 포함
RUN npm run build

# --- Production Stage ---
FROM node:20-alpine AS runner

WORKDIR /app
ENV NODE_ENV=production

# standalone 출력물 복사
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

ENV PORT=8080
EXPOSE 8080

CMD ["node", "server.js"]
