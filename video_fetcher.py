import os
import json
import sqlite3
from datetime import datetime, timezone
import logging
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import CRICKET_CHANNELS
from key_manager import YouTubeKeyManager
import time
import isodate  # Add this for parsing YouTube duration format

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoDatabaseManager:
    def __init__(self, db_path='videos.db'):
        self.db_path = db_path
        self.init_db()
        
    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS videos (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    thumbnail_url TEXT,
                    duration TEXT,
                    views TEXT,
                    category TEXT,
                    channel_id TEXT,
                    channel_name TEXT,
                    upload_date TIMESTAMP,
                    data JSON
                )
            ''')
            c.execute('CREATE INDEX IF NOT EXISTS idx_upload_date ON videos(upload_date DESC)')
            conn.commit()
    
    def store_videos(self, videos):
        """Store multiple videos in the database"""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            for video in videos:
                try:
                    c.execute('''
                        INSERT OR REPLACE INTO videos 
                        (id, title, thumbnail_url, duration, views, category, 
                         channel_id, channel_name, upload_date, data)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        video['id'],
                        video['title'],
                        video['thumbnail_url'],
                        video['duration'],
                        video['views'],
                        video['category'],
                        video['channel_id'],
                        video['channel_name'],
                        video['upload_date'],
                        json.dumps(video)
                    ))
                except sqlite3.IntegrityError:
                    logger.warning(f"Duplicate video ID: {video['id']}")
            conn.commit()

def is_short(video_details):
    """Check if video is a YouTube Short"""
    try:
        # Check duration
        duration_str = video_details['contentDetails']['duration']
        duration = isodate.parse_duration(duration_str)
        if duration.total_seconds() <= 60:
            return True

        # Check title for shorts indicators
        title = video_details['snippet']['title'].lower()
        if any(indicator in title for indicator in ['#shorts', '#short', '#ytshorts']):
            return True

        return False
    except Exception as e:
        logger.error(f"Error checking if video is short: {e}")
        return False

def categorize_video(title):
    """Categorize video based on its title"""
    title_lower = title.lower()
    if any(term in title_lower for term in ['vs', 'highlights', ' v ', 'match', 'innings']):
        if 'classic' in title_lower or 'archive' in title_lower:
            return 'classic'
        return 'matches'
    if any(term in title_lower for term in ['interview', 'press', 'conference', 'speaks']):
        return 'interviews'
    if any(term in title_lower for term in ['training', 'practice', 'behind the scenes', 'nets']):
        return 'training'
    return 'other'

def get_best_thumbnail(video):
    """Get the best quality thumbnail URL"""
    thumbnails = video['snippet']['thumbnails']
    # Try to get the highest quality thumbnail available
    for quality in ['maxres', 'high', 'medium', 'default']:
        if quality in thumbnails:
            return thumbnails[quality]['url']
    return f"https://i.ytimg.com/vi/{video['id']}/hqdefault.jpg"  # Fallback to HQ default

def is_embeddable(video_details):
    """Check if video can be embedded"""
    try:
        # Check status and embeddable flag
        if 'status' in video_details:
            if video_details['status'].get('embeddable', False) is False:
                return False
            if video_details['status'].get('privacyStatus', '') != 'public':
                return False
        return True
    except Exception as e:
        logger.error(f"Error checking if video is embeddable: {e}")
        return False

class VideoFetcher:
    def __init__(self, api_keys):
        self.key_manager = YouTubeKeyManager(api_keys)
        self.db = VideoDatabaseManager()
        self.youtube = None
    
    def get_youtube_service(self):
        api_key = self.key_manager.get_current_key()
        if not api_key:
            raise Exception("No API keys available")
        return build('youtube', 'v3', developerKey=api_key, cache_discovery=False)
    
    def fetch_channel_videos(self, channel_id, channel_name):
        try:
            self.youtube = self.get_youtube_service()
            
            # Get latest videos from channel
            request = self.youtube.search().list(
                part="id",
                channelId=channel_id,
                order="date",
                maxResults=15,  # Request more to account for filtered videos
                type="video"
            )
            response = request.execute()
            
            videos = []
            video_ids = [item['id']['videoId'] for item in response.get('items', [])]
            
            if not video_ids:
                return []
            
            # Get detailed video information including status
            video_response = self.youtube.videos().list(
                part="snippet,contentDetails,statistics,status",  # Added status part
                id=','.join(video_ids)
            ).execute()
            
            for video in video_response.get('items', []):
                # Check if video is embeddable and public
                if (video['status'].get('embeddable', False) and 
                    video['status'].get('privacyStatus') == 'public' and 
                    not is_short(video)):
                    try:
                        video_data = {
                            'id': video['id'],
                            'title': video['snippet']['title'],
                            'thumbnail_src': get_best_thumbnail(video),
                            'thumbnail_url': get_best_thumbnail(video),
                            'duration': video['contentDetails']['duration'],
                            'views': video['statistics'].get('viewCount', 'N/A'),
                            'category': categorize_video(video['snippet']['title']),
                            'channel_id': channel_id,
                            'channel_name': channel_name,
                            'upload_date': video['snippet']['publishedAt']
                        }
                        videos.append(video_data)
                        
                        if len(videos) >= 5:  # Only keep 5 embeddable non-short videos
                            break
                    except Exception as e:
                        logger.error(f"Error processing video {video.get('id')}: {e}")
                        continue
            
            return videos
            
        except HttpError as e:
            if e.resp.status in [403, 429]:  # Quota exceeded
                logger.warning(f"Quota exceeded for key: {self.youtube._developerKey[:10]}...")
                self.key_manager.update_quota_usage(self.youtube._developerKey, 
                                                  self.key_manager.daily_quota_limit)
                return self.fetch_channel_videos(channel_id, channel_name)
            raise
    
    def fetch_all_videos(self):
        all_new_videos = []
        
        for channel_name, channel_id in CRICKET_CHANNELS.items():
            logger.info(f"Fetching new videos for {channel_name}")
            try:
                channel_videos = self.fetch_channel_videos(channel_id, channel_name)
                all_new_videos.extend(channel_videos)
                logger.info(f"Fetched {len(channel_videos)} new videos from {channel_name}")
            except Exception as e:
                logger.error(f"Error fetching videos for {channel_name}: {e}")
            
            time.sleep(1)
        
        # Store all videos in database
        if all_new_videos:
            self.db.store_videos(all_new_videos)
            logger.info(f"Added {len(all_new_videos)} new videos to storage")
        else:
            logger.info("No new videos found")
        
        return all_new_videos

def main():
    from config import get_api_keys
    
    api_keys = get_api_keys()
    if not any(api_keys):
        logger.error("No API keys configured")
        return
    
    fetcher = VideoFetcher(api_keys)
    videos = fetcher.fetch_all_videos()
    
    if videos:
        logger.info(f"Successfully fetched {len(videos)} videos total")
    else:
        logger.error("Failed to fetch any videos")
        exit(1)

if __name__ == "__main__":
    main() 