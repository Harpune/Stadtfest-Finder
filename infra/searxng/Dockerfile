# Image stadtfest-searxng (build context infra/searxng): SearXNG with the settings of the AI
# search's web search tool baked in (ADR 0013). Internal only; the secret comes from
# SEARXNG_SECRET at runtime. Bump the base tag together with infra/compose.dev.yaml.
FROM docker.io/searxng/searxng:2026.10.2-19ffbcd30
COPY --chown=searxng:searxng settings.yml /etc/searxng/settings.yml
USER searxng
HEALTHCHECK --interval=30s --timeout=5s --retries=5 \
  CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1
LABEL org.opencontainers.image.source="https://github.com/Harpune/Stadtfest-Finder"
