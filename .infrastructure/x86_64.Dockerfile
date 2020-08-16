FROM alpine:3.11

ENV TUNMAN_CONFIG=/config \
    # Secret prefix in the URL ex. https://your-app.org/super-hiper-secret-here/health
    TUNMAN_SECRET_PREFIX= \
    # Environment, options: dev, prod
    TUNMAN_ENV=prod

COPY /.infrastructure/docker-entrypoint.sh /
COPY . /home/tunman/app
COPY .git /home/tunman/app/.git

RUN apk add --update bash git sshpass autossh openssh-client netcat-openbsd grep make py3-pip python3-dev gcc musl-dev libffi-dev openssl-dev \
    && rm -rf /var/cache/apk/* \
    && mkdir -p /home/tunman \
    && addgroup -g 1000 tunman \
    && adduser -D -u 1000 -h /home/tunman -G tunman tunman \
    && chown -R tunman:tunman /home/tunman \
    && pip3 install setuptools \
    && pip3 install -r /home/tunman/app/requirements.txt \
    \
    && cd /home/tunman/app \
    && ./setup.py install \
    && apk del gcc musl-dev python3-dev libffi-dev openssl-dev

VOLUME "/home/tunman/.ssh"
VOLUME "/config"

ENTRYPOINT ["/docker-entrypoint.sh"]
WORKDIR "/home/tunman/tunman/app"
CMD ["tunman start"]
