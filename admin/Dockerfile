ARG NODE_VERSION=${NODE_VERSION:-"20"}

FROM node:${NODE_VERSION}-alpine AS front-builder

# Import project's dependencies
WORKDIR /app

COPY package.json ./
COPY yarn.lock ./

RUN yarn install --network-timeout 1000000000

# Copy source files
COPY . .

# react-scripts 4 (webpack 4) calls Node's crypto.createHash('md4'), which
# OpenSSL 3 (Node >=17) rejects by default - react-scripts is unmaintained
# and won't fix this, so opt back into the legacy provider for the build step
ENV NODE_OPTIONS=--openssl-legacy-provider
RUN yarn build

FROM caddy:2-alpine AS runtime

# Set build arguments
ARG VERSION
ARG BUILD
ARG NOW

# Copy the built frontend and Caddy config
COPY --from=front-builder /app/build /opt/osat/www
COPY Caddyfile /etc/caddy/Caddyfile

# Container configuration
EXPOSE 80
VOLUME /opt/osat/www

# Set container labels
LABEL name="osat-admin" \
    version="$VERSION" \
    build="$BUILD" \
    architecture="x86_64" \
    build_date="$NOW" \
    vendor="osat" \
    url="https://github.com/osat.io/osat-docker" \
    summary="SeoZ project with Docker" \
    description="SeoZ project with Docker" \
    vcs-type="git" \
    vcs-url="https://github.com/osat.io/osat-docker" \
    vcs-ref="$VERSION" \
    distribution-scope="public"
