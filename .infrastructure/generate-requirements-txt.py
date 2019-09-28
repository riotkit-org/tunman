#!/usr/bin/env python3

import os
from json import loads as json_loads

assert os.path.isfile('Pipfile.lock')

requirements = ""

with open('./Pipfile.lock', 'rb') as f:
    piplock = f.read()

for package_name, details in json_loads(piplock)['default'].items():
    requirements += package_name + details['version'] + "\n"

with open('./requirements.txt', 'wb') as f:
    f.write(requirements.encode('utf-8'))
