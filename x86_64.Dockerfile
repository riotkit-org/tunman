FROM alpine:3.9

COPY ./ /rn

RUN apk add --update bash autossh openssh-client netcat-openbsd grep \
    && rm -rf /var/cache/apk/* \
    && mkdir -p /home/revproxy \
    && addgroup -g 1005 revproxy \
    && adduser -D -u 1005 -h /home/revproxy -G revproxy revproxy \
    && chown -R revproxy:revproxy /home/revproxy

VOLUME "/rn/conf.d"
VOLUME "/home/revproxy/.ssh"
WORKDIR "/rn"

ENTRYPOINT ["/rn/docker-entrypoint.sh"]
CMD ["/rn/bin/bind-network.sh --healthcheck-loop"]
