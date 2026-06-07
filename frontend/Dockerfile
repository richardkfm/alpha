FROM node:20-slim

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

EXPOSE 3000

# BACKEND_ORIGIN (set in docker-compose) tells Vite where to proxy /api & /health.
CMD ["npm", "run", "dev"]
