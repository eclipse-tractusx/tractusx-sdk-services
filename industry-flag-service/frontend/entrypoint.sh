#!/bin/bash

ROOT_DIR=/usr/share/nginx/html

echo "Replacing docker environment constants in JavaScript files"

for file in $ROOT_DIR/static/js/main*.js* $ROOT_DIR/index.html;
do
	echo "Processing $file ...";
	sed -i 's|BACKEND_URL|'${BACKEND_URL}'|g' $file
	sed -i 's|ENDPOINT_GET_MY_FLAGS|'${ENDPOINT_GET_MY_FLAGS}'|g' $file
	sed -i 's|ENDPOINT_SEARCH_FLAGS_BY_BPN|'${ENDPOINT_SEARCH_FLAGS_BY_BPN}'|g' $file
	sed -i 's|ENDPOINT_GET_MY_FLAG_PROOF|'${ENDPOINT_GET_MY_FLAG_PROOF}'|g' $file
	sed -i 's|ENDPOINT_GET_FLAG_PROOF_BY_BPN|'${ENDPOINT_GET_FLAG_PROOF_BY_BPN}'|g' $file
	sed -i 's|API_KEY|'${API_KEY}'|g' $file

done

exec "$@"
