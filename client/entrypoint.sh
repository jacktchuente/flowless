#!/bin/sh

echo "window.env = {" > /usr/share/nginx/html/assets/environment/env.js

env | grep '^CLIENT_' | while IFS= read -r line; do
  full_key=$(echo "$line" | cut -d '=' -f 1)
  value=$(echo "$line" | cut -d '=' -f 2-)
  key=$(echo "$full_key" | sed 's/^CLIENT_//')
  echo "  $key: '$value'," >> /usr/share/nginx/html/assets/environment/env.js
done

echo "};" >> /usr/share/nginx/html/assets/environment/env.js
