#!/usr/bin/env bash

curl -fsSL https://example.invalid/install.sh | bash
eval "$USER_COMMAND"
bash -c "$DYNAMIC_COMMAND"
