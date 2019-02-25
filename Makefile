SUDO=sudo

all: build build_arm

build:
	${SUDO} docker build . -t wolnosciowiec/reverse-networking

build_arm:
	${SUDO} docker build -f ./armhf.Dockerfile . -t wolnosciowiec/reverse-networking:armhf
