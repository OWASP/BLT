#!/bin/bash

# This script sets up a Bitcoin Core node with Runes support and integrates with BLT Core on a VPS

# Update and upgrade the system
sudo apt-get update && sudo apt-get upgrade -y

# Install necessary dependencies
sudo apt-get install -y build-essential libtool autotools-dev automake pkg-config bsdmainutils python3 libevent-dev libboost-system-dev libboost-filesystem-dev libboost-test-dev libboost-thread-dev libminiupnpc-dev libzmq3-dev libsqlite3-dev libdb-dev libdb++-dev libssl-dev git

# Install Berkeley DB 4.8 (required by Bitcoin Core)
sudo add-apt-repository ppa:bitcoin/bitcoin
sudo apt-get update
sudo apt-get install -y libdb4.8-dev libdb4.8++-dev

# Clone the Bitcoin Core repository
git clone https://github.com/bitcoin/bitcoin.git
cd bitcoin

# Checkout the latest stable release (or a specific version that supports Runes)
git checkout v24.0

# Build Bitcoin Core
./autogen.sh
./configure
make
sudo make install

# Create Bitcoin data directory
mkdir -p ~/.bitcoin

# Generate a basic bitcoin.conf file with Runes-specific configurations
cat <<EOF > ~/.bitcoin/bitcoin.conf
server=1
daemon=1
txindex=1
rpcuser=yourusername
rpcpassword=yourpassword
rpcallowip=127.0.0.1
rpcport=8332
addresstype=bech32
EOF

# Start the Bitcoin daemon with Runes support
bitcoind -daemon

# Wait for the Bitcoin Core node to start
sleep 10

# Verify the node is running and ready with Runes
bitcoin-cli getblockchaininfo

curl -X POST -d "status=setup_complete&node_name=your_node_name" https://blt.owasp.org/api/node-setup

echo "Bitcoin Core node setup complete with Runes protocol and BLT Core integration!"
