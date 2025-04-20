import os
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_api_keys() -> List[str]:
    """Get API keys from environment variables"""
    keys = []
    for i in range(1, 6):  # For 5 API keys
        key = os.getenv(f'YOUTUBE_API_KEY_{i}')
        if key:
            keys.append(key)
    return keys

# YouTube Channels Configuration
CRICKET_CHANNELS = {
    'Cricket Australia': 'UCkBY0aHJP9BwjZLDYxAQrKg',
    'England Cricket': 'UCz1D0n02BR3t51KuBOPmfTQ',
    'Pakistan Cricket': 'UCiWrjBhlICf_L_RK5y6Vrxw',
    'West Indies Cricket': 'UC2MHTOXktfTK26aDKyQs3cQ',
    'Sri Lanka Cricket': 'UCJA-NQ4MtcRIog66wziD8fA',
    'PakistanSuperLeague': 'UCpNzXJ5jpcJojC5mHQvGA8w'
}

# Add IPL configuration
IPL_VIDEO_BASE_URL = "https://www.iplt20.com/videos/highlights"
IPL_DISCLAIMER = "IPL videos are available on the official IPLT20.com website. Click to watch on the official platform."

# Add BCCI configuration
BCCI_VIDEO_BASE_URL = "https://www.bcci.tv/videos/highlights"
BCCI_DISCLAIMER = "BCCI videos are available on the official BCCI.tv website. Click to watch on the official platform."

# Constants
IPL_VIDEO_BASE_URL = "https://www.iplt20.com/videos/highlights"
BCCI_VIDEO_BASE_URL = "https://www.bcci.tv/videos/highlights"
IPL_DISCLAIMER = "IPL videos are available on the official IPLT20.com website. Click to watch on the official platform."
BCCI_DISCLAIMER = "BCCI videos are available on the official BCCI.tv website. Click to watch on the official platform."

# S3 Configuration
BUCKET_NAME = 'latestcrickethighlights-videos'