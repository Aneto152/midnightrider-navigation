FROM node:22-alpine

# Install curl and bash
RUN apk add --no-cache curl bash

# Create app directory
WORKDIR /app

# Copy scripts
COPY scripts/astronomical-data.sh /app/
COPY scripts/init-astronomical-data.sh /app/
COPY scripts/package.json /app/
COPY scripts/package-lock.json /app/

# Install dependencies
RUN npm install

# Make scripts executable
RUN chmod +x /app/astronomical-data.sh /app/init-astronomical-data.sh

# Default command: run init script
CMD ["/app/init-astronomical-data.sh"]
