#!/bin/bash

ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"/..
cd $ROOT/server

pwd
PYTHONPATH=$ROOT/pkdiagram/_pkdiagram/build/_pkdiagram:$ROOT/vedanaprivate/build/_vedanaprivate FLASK_APP=app.py $ROOT/.direnv/python-3.7.8/bin/flask run --host=0.0.0.0 --port=8888

# PATH=$PATH:/home/patrick/vendor/sysroot-dev/bin FLASK_APP=app.py PYTHONPATH=../_cutil:.. /home/patrick/vendor/sysroot-dev/bin/flask run --port=8888
# .direnv/python-3.7.8/bin/python
