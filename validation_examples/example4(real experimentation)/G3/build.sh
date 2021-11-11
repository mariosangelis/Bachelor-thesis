#!/bin/bash

docker buildx build --platform linux/amd64,linux/arm64 --push -t 192.168.0.151:5000/g3:latest .
