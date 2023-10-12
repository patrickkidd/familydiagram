#!/bin/bash -v

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

rsync -avz -e "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" --progress vedanamedia.com:/var/www/pkdiagram.vedanamedia.com/server_data $DIR/..


echo "Pulling down production postgres database..."
ssh pkdiagram.vedanamedia.com "pg_dump -Fc --no-acl --no-owner -h localhost familydiagram -U familydiagram" > prod.dump
dropdb familydiagram
createdb familydiagram
pg_restore --verbose -n public --no-acl --no-owner -h localhost -U familydiagram -d familydiagram prod.dump
