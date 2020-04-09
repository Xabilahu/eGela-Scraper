#!/bin/bash

setup() {
    virtualenv --python=python3 env
    source env/bin/activate
    pip install -r res/requirements.txt
    deactivate
}

if [ -z "$(dpkg -l | grep virtualenv)" ]; then
    sudo apt install virtualenv
fi

if [ -z "$(ls env 2> /dev/null)" ]; then
    setup
fi

source env/bin/activate
python3 src/scrap.py "$@"
deactivate