FROM ghcr.io/bitwarden/bws:2.0.0 AS bws-cli

FROM docker.io/postgres:18

COPY ./compose/production/postgres/maintenance /usr/local/bin/maintenance
RUN chmod +x /usr/local/bin/maintenance/*
RUN mv /usr/local/bin/maintenance/* /usr/local/bin \
    && rmdir /usr/local/bin/maintenance

COPY --from=bws-cli /bin/bws /usr/local/bin/bws

COPY ./compose/production/postgres/entrypoint /entrypoint
RUN chmod +x /entrypoint

ENTRYPOINT ["/entrypoint"]
