# Estágio 1: Build da aplicação React
FROM node:22-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Estágio 2: Nginx de alta performance para servir o frontend e fazer proxy reverso para o backend
FROM nginx:alpine-slim

# Copia a configuração do Nginx com proxy para /api/
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copia os arquivos estáticos gerados no build
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
