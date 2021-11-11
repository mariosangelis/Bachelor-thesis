#!/bin/bash

docker buildx build --platform linux/amd64,linux/arm64 --push -t 192.168.1.103:5000/g3:latest .
