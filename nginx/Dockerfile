# nginx/Dockerfile

FROM node:22-alpine AS cockpit-builder
WORKDIR /app
COPY cockpit/package*.json ./
RUN npm ci
COPY cockpit/ .
ENV VITE_API_BASE_URL=
RUN npm run build

FROM node:22-alpine AS frontend-builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
ENV VITE_API_ORIGIN=
RUN npm run build

FROM nginx:1.27-alpine

RUN rm /etc/nginx/conf.d/default.conf
COPY nginx/nginx.conf /etc/nginx/nginx.conf

COPY --from=cockpit-builder /app/dist /usr/share/nginx/html/cockpit
COPY --from=frontend-builder /app/dist /usr/share/nginx/html/site

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]