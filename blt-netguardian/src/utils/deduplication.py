"""Task deduplication utilities."""
import hashlib
import json
from typing import Dict, Any


class TaskDeduplicator:
    """Handles task deduplication to prevent redundant scanning."""
    
    def __init__(self):
        self.seen_hashes = set()
    
    def generate_task_hash(self, task) -> str:
        """Generate a unique hash for a task based on its key attributes."""
        # Create hash from target_id, task_type combination
        hash_input = f"{task.target_id}:{task.task_type}"
        return hashlib.sha256(hash_input.encode()).hexdigest()
    
    async def is_duplicate(self, task, task_queue) -> bool:
        """Check if a task is a duplicate of an existing task."""
        task_hash = self.generate_task_hash(task)
        
        # Check if we've seen this hash in recent memory
        if task_hash in self.seen_hashes:
            return True
        
        # Check if similar task exists in queue (within last 24 hours)
        # This would query the KV store for existing tasks
        # For now, we'll just mark as seen
        self.seen_hashes.add(task_hash)
        
        # In production, also check persistent storage:
        # existing_task = await task_queue.get(task_hash)
        # if existing_task:
        #     task_data = json.loads(existing_task.value)
        #     # Check if task is still active/recent
        #     return task_data.get('status') in ['queued', 'running']
        
        return False
    
    def clear_cache(self):
        """Clear the in-memory deduplication cache."""
        self.seen_hashes.clear()
