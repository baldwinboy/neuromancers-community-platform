FROM ghcr.io/bitwarden/bws:2.1.0 AS bws-cli

FROM docker.io/postgres:18

RUN apt-get update && apt-get install --no-install-recommends -y ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY ./compose/production/postgres/maintenance /usr/local/bin/maintenance
RUN chmod +x /usr/local/bin/maintenance/*
RUN mv /usr/local/bin/maintenance/* /usr/local/bin \
    && rmdir /usr/local/bin/maintenance

COPY --from=bws-cli /bin/bws /usr/local/bin/bws

COPY ./compose/production/postgres/entrypoint /entrypoint
RUN chmod +x /entrypoint

ENTRYPOINT ["/entrypoint"]
