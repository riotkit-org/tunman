
.SILENT:
PUSH=true
SUDO=sudo
SHELL=/bin/bash
QUAY_REPO=quay.io/riotkit/reverse-networking

build: ## Build and push (args: PUSH, ARCH, GIT_TAG)
	set -e; DOCKER_TAG="latest-dev-${ARCH}"; \
	\
	if [[ "${GIT_TAG}" != '' ]]; then \
		DOCKER_TAG=${GIT_TAG}-${ARCH}; \
	fi; \
	\
	${SUDO} docker build . -f ./${ARCH}.Dockerfile -t ${QUAY_REPO}:$${DOCKER_TAG}; \
	${SUDO} docker tag ${QUAY_REPO}:$${DOCKER_TAG} ${QUAY_REPO}:$${DOCKER_TAG}-$$(date '+%Y-%m-%d'); \
	\
	if [[ "${PUSH}" == "true" ]]; then \
		${SUDO} docker push ${QUAY_REPO}:$${DOCKER_TAG}-$$(date '+%Y-%m-%d'); \
		${SUDO} docker push ${QUAY_REPO}:$${DOCKER_TAG}; \
	fi
