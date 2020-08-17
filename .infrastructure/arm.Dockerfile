FROM balenalib/armv7hf-debian:buster

ENV TUNMAN_CONFIG=/config \
    # Secret prefix in the URL ex. https://your-app.org/super-hiper-secret-here/health
    TUNMAN_SECRET_PREFIX= \
    # Environment, options: dev, prod
    TUNMAN_ENV=prod

COPY /.infrastructure/docker-entrypoint.sh /
COPY . /home/tunman/app
COPY .git /home/tunman/app/.git

RUN [ "cross-build-start" ]
RUN apt-get update \
    && apt-get install -y bash git sshpass autossh openssh-client netcat grep make python3-nacl python-yaml python3-dev python3-pip build-essential libffi-dev libssl-dev \
    && apt-get clean \
    && mkdir -p /home/tunman \
    && useradd -m -s /bin/bash -u 1000 tunman \
    && chown -R tunman:tunman /home/tunman \
    && pip3 install setuptools \
    && pip3 install -r /home/tunman/app/requirements.txt \
    \
    && cd /home/tunman/app \
    && ./setup.py install \
    && apt-get remove -y gcc musl-dev python3-dev libffi-dev libssl-dev build-essential
RUN [ "cross-build-end" ]

VOLUME "/home/tunman/.ssh"
VOLUME "/config"

ENTRYPOINT ["/docker-entrypoint.sh"]
WORKDIR "/home/tunman/tunman/app"
CMD ["tunman start"]
