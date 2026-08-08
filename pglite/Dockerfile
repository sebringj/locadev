FROM node:20-slim

WORKDIR /app

COPY package.json ./
RUN npm install --omit=dev

COPY server.mjs seed.sql ./

ENV PGLITE_DATA_DIR=/data
ENV PORT=5433
EXPOSE 5433

VOLUME ["/data"]

CMD ["node", "server.mjs"]
