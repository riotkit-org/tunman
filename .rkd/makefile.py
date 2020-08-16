
import os
from rkd.api.syntax import TaskAliasDeclaration as TaskAlias
from rkd.api.syntax import TaskDeclaration
from rkd.api.contract import ArgparseArgument
from rkd.api.contract import TaskInterface
from rkd.api.contract import ExecutionContext
from rkd.standardlib import CallableTask
from rkt_ciutils.docker import GenerateReadmeTask
from rkt_utils.docker import imports as DockerTaggingImports
from rkd_python import imports as PythonBuildingTasks

REPO = 'quay.io/riotkit/reverse-networking'


def build_image(ctx: ExecutionContext, this: TaskInterface) -> bool:
    """ Builds a docker image for given architecture, tags properly and push """
    tag = ctx.get_arg('--git-tag')
    should_push = ctx.get_arg('--push')
    arch = ctx.get_arg('--arch')
    docker_tag = 'latest-dev-' + arch

    if tag:
        docker_tag = arch + '-' + tag

    image_name = '{repo}:{tag}'.format(tag=docker_tag, repo=REPO)

    this.sh('docker build . -f ./.infrastructure/{docker_arch}.Dockerfile -t {image}'
            .format(docker_arch=arch, image=image_name))

    this.sh('docker tag {image} {image}-$(date "+%Y-%m-%d")'.format(image=image_name))

    if should_push:
        this.sh('docker push {image}'.format(image=image_name))
        this.sh('docker push {image}-$(date "+%Y-%m-%d")'.format(image=image_name))

    return True


#
# Single tasks declarations
#
IMPORTS = [
    TaskDeclaration(GenerateReadmeTask()),

    #
    # Builds a Docker image
    #
    TaskDeclaration(CallableTask(
        ':image', build_image, description='Builds a docker image',
        argparse_options=[
            ArgparseArgument(args=['--git-tag'],
                             kwargs={'required': False, 'help': 'Will tag the image considering this version'}),
            ArgparseArgument(args=['--push'],
                             kwargs={'action': 'store_true', 'help': 'Push or only build?'}),
            ArgparseArgument(args=['--arch'],
                             kwargs={'default': 'x86_64', 'help': 'Architecture name'})
        ]
    ))
]

IMPORTS += PythonBuildingTasks() + DockerTaggingImports()

#
# Tasks that are of pipeline-type - one task triggers a chain of other tasks - that are TaskAliases
#
TASKS = [
    TaskAlias(':test', [':sh', '-c', 'tox']),

    #
    # Building
    #
    TaskAlias(':readme', [
        ':docker:generate-readme',
        '--template=README.md.j2',
        '--dockerfile=.infrastructure/x86_64.Dockerfile',
        '--target-path=README.md'
    ]),
    TaskAlias(':clean', [':sh', '-c', 'rm -rf build *.egg-info']),


    #
    # Validation on CI
    #
    TaskAlias(':validate-readme', [':sh', '-c', '''
        current_sum=$(md5sum README.md)
        %RKD% :readme
        
        new_sum=$(md5sum README.md)
        
        if [[ "${current_sum}" != "${new_sum}" ]]; then
            echo " >> THE README.md WAS NOT REGENERATED OR NOT COMMITED TO REPOSITORY AFTER REGENERATION."
            exit 1
        fi
    
    ''']),

    #
    # Release
    #
    TaskAlias(':release:pypi', [
        ':validate-readme',
        ':py:build',
        ':py:publish', '--password=${PYPI_PASSWORD}', '--username=__token__', '--skip-existing'
    ]),

    TaskAlias(':release:docker:x86', [
        ':image', '--push', '--git-tag=${GIT_TAG}', '--arch=x86_64'
    ]),

    TaskAlias(':release:docker:arm', [
        ':image', '--push', '--git-tag=${GIT_TAG}', '--arch=arm',
    ])
]
