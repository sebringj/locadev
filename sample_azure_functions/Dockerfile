# Functions-style worker (native arm64/amd64) using Azurite for queue I/O.
# Mirrors Azure Functions storage-binding patterns without the amd64-only
# Microsoft Functions image (which crashes under QEMU on Apple Silicon).
FROM node:20-slim

WORKDIR /app

COPY package.json ./
RUN npm install --omit=dev

COPY server.mjs ./
COPY host.json ./
COPY src ./src
COPY local.settings.json ./

ENV PORT=80 \
    FUNCTIONS_WORKER_RUNTIME=node

EXPOSE 80
CMD ["node", "server.mjs"]
