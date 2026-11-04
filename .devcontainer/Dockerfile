FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

# This npm-only project does not use the inherited Yarn apt feed. Its stale
# signing key breaks apt update during Playwright's OS dependency setup.
# Remove that unused feed, not apt's signature verification.
RUN rm -f /etc/apt/sources.list.d/yarn.list
