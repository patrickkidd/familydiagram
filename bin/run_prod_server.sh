#!/bin/bash

cd /var/www/database.familydiagram.com/server

FLASK_CONFIG=production FLASK_APP=app.py PYTHONPATH=../pkdiagram/_pkdiagram:.. flask run --port=8888
