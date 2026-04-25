FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install --omit=dev

COPY astronomical-server.js .

RUN chmod +x astronomical-server.js

# Run as non-root user
RUN addgroup -g 1000 mcp && \
    adduser -u 1000 -G mcp -s /sbin/nologin mcp

USER mcp

ENTRYPOINT ["node", "astronomical-server.js"]
