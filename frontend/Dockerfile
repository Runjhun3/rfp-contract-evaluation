# The React UI: built with Node, served by nginx, which also forwards /api to the API.
# Build context: frontend/
FROM node:22-bookworm-slim AS build
WORKDIR /ui
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY security-headers.conf /etc/nginx/snippets/security-headers.conf
COPY --from=build /ui/dist /usr/share/nginx/html
EXPOSE 80
