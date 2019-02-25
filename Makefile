SUDO=sudo

all: build

build:
	${SUDO} docker build . -t wolnosciowiec/reverse-networking
