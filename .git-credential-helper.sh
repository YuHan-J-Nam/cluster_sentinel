#!/bin/bash
source ~/.env

if [ "$1" = "get" ]; then
  echo "username=$GITHUB_USERNAME"
  echo "password=$GITHUB_PAT"
fi
