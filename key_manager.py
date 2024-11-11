import time
from typing import Optional

class YouTubeKeyManager:
    def __init__(self, api_keys):
        self.api_keys = api_keys
        self.current_key_index = 0
        self.quota_usage = {key: 0 for key in api_keys}
        self.last_used = {key: 0 for key in api_keys}
        self.daily_quota_limit = 10000  # YouTube's daily quota limit
        
    def get_current_key(self) -> Optional[str]:
        """Get the current usable API key"""
        current_time = time.time()
        
        # Try all keys
        for _ in range(len(self.api_keys)):
            key = self.api_keys[self.current_key_index]
            
            # Reset quota if 24 hours have passed
            if current_time - self.last_used[key] >= 86400:  # 24 hours
                self.quota_usage[key] = 0
                
            # If key has available quota, use it
            if self.quota_usage[key] < self.daily_quota_limit:
                return key
                
            # Try next key
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        
        return None
    
    def next_key(self) -> Optional[str]:
        """Switch to next API key and return it"""
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        return self.get_current_key()
    
    def update_quota_usage(self, key: str, cost: int):
        """Update the quota usage for a key"""
        self.quota_usage[key] += cost
        self.last_used[key] = time.time()
        
        # If quota exceeded, move to next key
        if self.quota_usage[key] >= self.daily_quota_limit:
            self.next_key()
    
    def get_available_quota(self, key: str) -> int:
        """Get remaining quota for a key"""
        return max(0, self.daily_quota_limit - self.quota_usage.get(key, 0))
    
    def is_quota_available(self, key: str, required_quota: int = 1) -> bool:
        """Check if key has enough quota available"""
        return self.get_available_quota(key) >= required_quota