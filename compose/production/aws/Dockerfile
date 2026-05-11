FROM ghcr.io/bitwarden/bws:2.0.0 AS bws-cli

FROM docker.io/amazon/aws-cli:2.34.42

COPY --from=bws-cli /bin/bws /usr/local/bin/bws
COPY ./compose/production/aws/entrypoint /entrypoint
RUN chmod +x /entrypoint

# Clear entrypoint from the base image, otherwise it's always calling the aws CLI
ENTRYPOINT ["/entrypoint"]
CMD ["/bin/bash"]

COPY ./compose/production/aws/maintenance /usr/local/bin/maintenance
COPY ./compose/production/postgres/maintenance/_sourced /usr/local/bin/maintenance/_sourced

RUN chmod +x /usr/local/bin/maintenance/*

RUN mv /usr/local/bin/maintenance/* /usr/local/bin \
    && rmdir /usr/local/bin/maintenance
