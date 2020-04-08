#!/bin/bash

setup() {
    virtualenv --python=python3 env
    source env/bin/activate
    pip install -r res/requirements.txt
}

if [ -z "$(dpkg -l | grep virtualenv)" ]; then
    sudo apt install virtualenv
fi

if [ -z "$(ls env 2> /dev/null)" ]; then
    setup
fi

python3 src/scrap.py "$@"