FROM node:20-alpine AS build

WORKDIR /app

ARG REACT_APP_API_URL=/api
ARG PACKAGE_OPTION=prod
ENV REACT_APP_API_URL=${REACT_APP_API_URL}
ENV PACKAGE_OPTION=${PACKAGE_OPTION}

COPY frontend/package*.json ./

RUN npm ci

COPY frontend/ .

RUN npx webpack --mode production --env packageOption=${PACKAGE_OPTION}

FROM nginxinc/nginx-unprivileged:stable-alpine

COPY deployment/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]