#!/bin/bash
mongorestore --drop -d music /docker-entrypoint-initdb.d/music/
