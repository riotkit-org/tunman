
.PHONY: help
.SILENT:
PUSH=true
SUDO=sudo
SHELL=/bin/bash
QUAY_REPO=quay.io/riotkit/reverse-networking
RIOTKIT_UTILS_VER=v2.0.0
PARAMS=-c ./example/scenario-1

help:
	@grep -E '^[a-zA-Z\-\_0-9\.@]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

build_pkg: ## Build python package
	./setup.py build

clean: ## Clean up
	rm -rf build *.egg-info

build_image: ## Build and push (args: PUSH, ARCH, GIT_TAG)
	set -e; DOCKER_TAG="latest-dev-${ARCH}"; \
	\
	if [[ "${GIT_TAG}" != '' ]]; then \
		DOCKER_TAG=${GIT_TAG}-${ARCH}; \
	fi; \
	\
	${SUDO} docker build . -f ./.infrastructure/${ARCH}.Dockerfile -t ${QUAY_REPO}:$${DOCKER_TAG}; \
	${SUDO} docker tag ${QUAY_REPO}:$${DOCKER_TAG} ${QUAY_REPO}:$${DOCKER_TAG}-$$(date '+%Y-%m-%d'); \
	\
	if [[ "${PUSH}" == "true" ]]; then \
		${SUDO} docker push ${QUAY_REPO}:$${DOCKER_TAG}-$$(date '+%Y-%m-%d'); \
		${SUDO} docker push ${QUAY_REPO}:$${DOCKER_TAG}; \
	fi

run_latest_dev_image: ## Run latest-dev-x86_64 image
	${SUDO} docker run --name tunman_dev --rm quay.io/riotkit/reverse-networking:latest-dev-x86_64

dev@generate_requirements_txt: ## Generate requirements from frozen Piplock (do it before commit)
	./.infrastructure/generate-requirements-txt.py

dev@shell: ## Start development shell
	pipenv sync
	pipenv shell

dev@start: ## Start tunman with all default params (use PARAMS= to specify params(
	pipenv run ./tunman/__init__.py start ${PARAMS}

### COMMON AUTOMATION

dev@generate_readme: _download_tools ## Renders the README.md from README.md.j2
	RIOTKIT_PATH=./.helpers/current DOCKERFILE_PATH=.infrastructure/x86_64.Dockerfile ./.helpers/current/docker-generate-readme

dev@before_commit: dev@generate_readme dev@generate_requirements_txt ## Git hook before commit
	git add README.md requirements.txt AUTHORS ChangeLog

_download_tools:
	if [[ ! -d ".helpers/${RIOTKIT_UTILS_VER}" ]]; then \
		mkdir -p .helpers/${RIOTKIT_UTILS_VER}; \
		curl -s https://raw.githubusercontent.com/riotkit-org/ci-utils/${RIOTKIT_UTILS_VER}/bin/for-each-github-release      > .helpers/${RIOTKIT_UTILS_VER}/for-each-github-release; \
		curl -s https://raw.githubusercontent.com/riotkit-org/ci-utils/${RIOTKIT_UTILS_VER}/bin/env-to-json                  > .helpers/${RIOTKIT_UTILS_VER}/env-to-json; \
		curl -s https://raw.githubusercontent.com/riotkit-org/ci-utils/${RIOTKIT_UTILS_VER}/bin/docker-generate-readme       > .helpers/${RIOTKIT_UTILS_VER}/docker-generate-readme; \
		curl -s https://raw.githubusercontent.com/riotkit-org/ci-utils/${RIOTKIT_UTILS_VER}/bin/extract-envs-from-dockerfile > .helpers/${RIOTKIT_UTILS_VER}/extract-envs-from-dockerfile; \
		curl -s https://raw.githubusercontent.com/riotkit-org/ci-utils/${RIOTKIT_UTILS_VER}/bin/inject-qemu-bin-into-container > .helpers/${RIOTKIT_UTILS_VER}/inject-qemu-bin-into-container; \
	fi

	rm -f .helpers/current
	ln -s $$(pwd)/.helpers/${RIOTKIT_UTILS_VER} $$(pwd)/.helpers/current
	chmod +x .helpers/*/*

dev@develop: ## Setup development environment, install git hooks
	echo " >> Setting up GIT hooks for development"
	mkdir -p .git/hooks
	echo "#\!/bin/bash" > .git/hooks/pre-commit
	echo "make dev@before_commit" >> .git/hooks/pre-commit
	chmod +x .git/hooks/pre-commit
