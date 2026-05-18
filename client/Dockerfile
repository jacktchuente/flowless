FROM node:18 as build
WORKDIR /usr/local/app
COPY ./ /usr/local/app/
RUN npm install
RUN npm run build
FROM nginx:1.31.0
RUN apt-get update
COPY --from=build /usr/local/app/dist/client/browser /usr/share/nginx/html
COPY ./proxy_default.conf /etc/nginx/conf.d/default.conf
COPY ./entrypoint.sh /docker-entrypoint.d/99-custom-env.sh

RUN chmod +x /docker-entrypoint.d/99-custom-env.sh

EXPOSE 80
EXPOSE 443
