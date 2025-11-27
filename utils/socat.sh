#!/bin/bash
socat TCP-LISTEN:13579,fork,bind=163.180.2.245 TCP:127.0.0.1:13579 &
