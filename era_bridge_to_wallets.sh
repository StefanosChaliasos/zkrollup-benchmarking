#!/bin/bash

file="$1"
counter=1

while IFS=, read -r priv addr
do
  priv=$(echo "$priv" | tr -d '\r\n')
  addr=$(echo "$addr" | tr -d '\r\n')
  echo "Processing $counter: $addr"
  npx zksync-cli bridge deposit --to $addr \
          --amount 10000 \
          --token 0x0000000000000000000000000000000000000000 \
          --pk 0x7726827caac94a7f9e1b160f7ea819f172f7b6f9d2a97f992c38edeab82d4110 \
          --chain dockerized-node < /dev/null
  ((counter++))
done < "$file"
