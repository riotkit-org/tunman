FROM balenalib/armv7hf-debian:buster

COPY ./ /rn

RUN [ "cross-build-start" ]
RUN apt-get update \
    && apt-get install -y bash autossh openssh-client netcat grep \
    && apt-get clean \
    && mkdir -p /home/revproxy \
    && groupadd -g 1005 revproxy \
    && useradd -ms /bin/bash revproxy -d /home/revproxy -g revproxy -u 1005 \
    && chown -R revproxy:revproxy /home/revproxy
RUN [ "cross-build-end" ]  

VOLUME "/rn/conf.d"
VOLUME "/home/revproxy/.ssh"
WORKDIR "/rn"

ENTRYPOINT ["/rn/docker-entrypoint.sh"]
CMD ["/rn/bin/bind-network.sh --healthcheck-loop"]
