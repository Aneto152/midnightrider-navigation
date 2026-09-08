FROM node:22-alpine
WORKDIR /app
COPY package.json .
COPY servers/ servers/
COPY lib/ lib/
ARG SERVER=astronomical
RUN addgroup -g 1000 mcp && adduser -u 1000 -G mcp -s /sbin/nologin -D mcp
USER mcp
ENV INFLUX_BUCKET=midnight_rider
CMD node servers/${SERVER}.js
