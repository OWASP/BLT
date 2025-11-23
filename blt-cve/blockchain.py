"""
Simple blockchain implementation for decentralized CVE storage.
This provides immutability and resiliency for CVE data.
"""
import hashlib
import json
import time
from typing import List, Dict, Any, Optional


class Block:
    """Represents a block in the blockchain containing CVE data."""
    
    def __init__(self, index: int, timestamp: float, data: Dict[str, Any], 
                 previous_hash: str, nonce: int = 0):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        """Calculate the hash of the block."""
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def mine_block(self, difficulty: int) -> None:
        """Mine the block with proof of work."""
        target = "0" * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert block to dictionary."""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash
        }


class Blockchain:
    """Blockchain for storing CVE data in a decentralized manner."""
    
    def __init__(self, difficulty: int = 4):
        self.chain: List[Block] = []
        self.difficulty = difficulty
        self.pending_cves: List[Dict[str, Any]] = []
        self.create_genesis_block()
    
    def create_genesis_block(self) -> None:
        """Create the first block in the chain."""
        genesis_block = Block(0, time.time(), {
            "type": "genesis",
            "message": "BLT-CVE Genesis Block - Decentralized CVE Database"
        }, "0")
        genesis_block.mine_block(self.difficulty)
        self.chain.append(genesis_block)
    
    def get_latest_block(self) -> Block:
        """Get the most recent block in the chain."""
        return self.chain[-1]
    
    def add_cve(self, cve_data: Dict[str, Any]) -> None:
        """Add a CVE to the pending list."""
        self.pending_cves.append(cve_data)
    
    def mine_pending_cves(self) -> Block:
        """Mine all pending CVEs into a new block."""
        if not self.pending_cves:
            return None
        
        block = Block(
            index=len(self.chain),
            timestamp=time.time(),
            data={
                "type": "cve_batch",
                "cves": self.pending_cves,
                "count": len(self.pending_cves)
            },
            previous_hash=self.get_latest_block().hash
        )
        
        block.mine_block(self.difficulty)
        self.chain.append(block)
        self.pending_cves = []
        return block
    
    def is_chain_valid(self) -> bool:
        """Verify the integrity of the blockchain."""
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]
            
            # Verify current block's hash
            if current_block.hash != current_block.calculate_hash():
                return False
            
            # Verify link to previous block
            if current_block.previous_hash != previous_block.hash:
                return False
        
        return True
    
    def get_all_cves(self) -> List[Dict[str, Any]]:
        """Extract all CVEs from the blockchain."""
        all_cves = []
        for block in self.chain:
            if block.data.get("type") == "cve_batch":
                all_cves.extend(block.data.get("cves", []))
        return all_cves
    
    def find_cve_by_id(self, cve_id: str) -> Optional[Dict[str, Any]]:
        """Find a specific CVE by its ID."""
        for cve in self.get_all_cves():
            if cve.get("id") == cve_id or cve.get("cve_id") == cve_id:
                return cve
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert blockchain to dictionary."""
        return {
            "length": len(self.chain),
            "difficulty": self.difficulty,
            "chain": [block.to_dict() for block in self.chain],
            "pending_cves": len(self.pending_cves)
        }
    
    def save_to_file(self, filename: str) -> None:
        """Save blockchain to a JSON file."""
        with open(filename, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load_from_file(cls, filename: str, difficulty: int = 4) -> 'Blockchain':
        """Load blockchain from a JSON file."""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            blockchain = cls(difficulty)
            blockchain.chain = []
            
            for block_data in data['chain']:
                block = Block(
                    index=block_data['index'],
                    timestamp=block_data['timestamp'],
                    data=block_data['data'],
                    previous_hash=block_data['previous_hash'],
                    nonce=block_data['nonce']
                )
                block.hash = block_data['hash']
                blockchain.chain.append(block)
            
            return blockchain
        except FileNotFoundError:
            return cls(difficulty)
