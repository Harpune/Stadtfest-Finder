# Image stadtfest-edge (build context infra/edge): Caddy with the routing of the stack and the
# static deep-link site (fallback pages, App Links / Universal Links files, legal pages).
# Configuration only through the environment (LINK_HOST, API_HOST, MCP_HOST_NAME, IMAGES_HOST,
# S3_BUCKET, ANDROID_CERT_SHA256, APPLE_TEAM_ID, IMPRINT_*), see infra/komodo-environment.example.
FROM caddy:2.11-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY public /srv/deeplinks
RUN mkdir -p /data /config \
 && chown -R 1000:1000 /data /config \
 && caddy fmt --diff /etc/caddy/Caddyfile >/dev/null
ENV XDG_DATA_HOME=/data XDG_CONFIG_HOME=/config
USER 1000:1000
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1:2019/config/ || exit 1
LABEL org.opencontainers.image.source="https://github.com/Harpune/Stadtfest-Finder"
