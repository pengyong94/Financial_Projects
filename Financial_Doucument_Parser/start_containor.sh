#!/bin/bash
# 根据镜像ID创建容器，开放端口8008-8010，挂载/data目录
docker run -it \
  --name document_parser \
  -p 8008:8008 \
  -p 8009:8009 \
  -p 8010:8010 \
  -v /data:/data \
  --restart unless-stopped \
  a5d7930b60cc \
  /bin/bash
