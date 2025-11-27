#!/bin/bash
if [ -f ".env" ]; then
  source .env
fi

if [ "$1" = "get" ]; then
  echo "username=$GITHUB_USERNAME"
  echo "password=$GITHUB_PAT"
fi
