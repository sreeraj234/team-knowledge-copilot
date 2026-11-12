FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

# The base image ships a Yarn apt source with an outdated signing key,
# which makes apt-get update fail. We don't need it, so remove it first.
RUN rm -f /etc/apt/sources.list.d/yarn.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*
