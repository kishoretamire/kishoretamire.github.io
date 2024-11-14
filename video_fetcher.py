import json
import os
import logging
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import CRICKET_CHANNELS
from key_manager import YouTubeKeyManager
import time
import isodate

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_existing_json(file_path):
    """Load existing JSON file if it exists"""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load existing file {file_path}: {e}")
    return []

def merge_videos(existing_videos, new_videos):
    """Merge new videos with existing ones, avoiding duplicates"""
    # Create a dictionary of existing videos by ID
    existing_dict = {video['id']: video for video in existing_videos}
    
    # Add or update videos
    for video in new_videos:
        existing_dict[video['id']] = video
    
    # Convert back to list and sort by upload date
    merged = list(existing_dict.values())
    merged.sort(key=lambda x: x['upload_date'], reverse=True)
    return merged

def is_short(video_details):
    """Check if video is a YouTube Short"""
    try:
        duration_str = video_details['contentDetails']['duration']
        duration = isodate.parse_duration(duration_str)
        if duration.total_seconds() <= 60:
            return True

        title = video_details['snippet']['title'].lower()
        if any(indicator in title for indicator in ['#shorts', '#short', '#ytshorts']):
            return True

        return False
    except Exception as e:
        logger.error(f"Error checking if video is short: {e}")
        return False

def get_best_thumbnail(video):
    """Get the best quality thumbnail URL"""
    thumbnails = video['snippet']['thumbnails']
    for quality in ['maxres', 'high', 'medium', 'default']:
        if quality in thumbnails:
            return thumbnails[quality]['url']
    return f"https://i.ytimg.com/vi/{video['id']}/hqdefault.jpg"

def get_team_variations():
    """Get variations of team names"""
    return {
        'australia': ['australia', 'aussies', 'aus'],
        'india': ['india', 'ind', 'bcci', 'team india'],
        'england': ['england', 'eng', 'english'],
        'pakistan': ['pakistan', 'pak', 'pcb'],
        'south africa': ['south africa', 'sa', 'proteas'],
        'new zealand': ['new zealand', 'nz', 'black caps', 'blackcaps'],
        'west indies': ['west indies', 'wi', 'windies', 'caribbean'],
        'sri lanka': ['sri lanka', 'sl', 'lanka'],
        'bangladesh': ['bangladesh', 'ban', 'tigers']
    }

def extract_teams_from_text(text):
    """Extract team names from text using variations"""
    teams = set()
    text_lower = text.lower()
    team_variations = get_team_variations()
    
    for team, variations in team_variations.items():
        if any(variation in text_lower for variation in variations):
            teams.add(team.title())
    
    return list(teams)

def categorize_video(title, description='', channel_id=''):
    """Categorize video based on title and description"""
    title_lower = title.lower()
    description_lower = description.lower() if description else ''
    
    # Extract teams from both title and description
    teams = extract_teams_from_text(f"{title_lower} {description_lower}")
    
    # Check for live videos first - these go to 'other' category
    if 'live' in title_lower:
        return 'other', teams
    
    # Pakistan Cricket channel - only use title
    if channel_id == 'UCiWrjBhlICf_L_RK5y6Vrxw':  # Pakistan Cricket channel ID
        # Match Highlights - ONLY check title
        highlight_indicators = [
            'highlights', 'match highlights', 'innings highlights',
            'batting highlights', 'bowling highlights'
        ]
        
        # Check for highlights in title only
        if any(indicator in title_lower for indicator in highlight_indicators):
            if any(indicator in title_lower for indicator in ['classic', 'archive', 'throwback', 'on this day']):
                return 'classic', teams
            return 'matches', teams
        
        # Press/Interviews - title only
        interview_indicators = [
            'interview', 'press conference', 'press', 'conference',
            'speaks to media', 'media session', 'presser', 'media briefing'
        ]
        if any(indicator in title_lower for indicator in interview_indicators):
            return 'interviews', teams
        
        # Classic/Archive - title only
        classic_indicators = [
            'classic', 'archive', 'throwback', 'on this day',
            'vintage', 'retro', 'from the vault', 'memories'
        ]
        if any(indicator in title_lower for indicator in classic_indicators):
            return 'classic', teams
    
        
        return 'other', teams
    
    # England Cricket channel - only use title
    if channel_id == 'UCz1D0n02BR3t51KuBOPmfTQ':  # England Cricket channel ID
        # Match Highlights - ONLY check title
        highlight_indicators = [
            'highlights', 'match highlights', 'innings highlights',
            'batting highlights', 'bowling highlights'
        ]
        
        # Check for highlights in title only
        if any(indicator in title_lower for indicator in highlight_indicators):
            if any(indicator in title_lower for indicator in ['classic', 'archive', 'throwback', 'on this day']):
                return 'classic', teams
            return 'matches', teams
        
        # Press/Interviews - title only
        interview_indicators = [
            'interview', 'press conference', 'press', 'conference',
            'speaks to media', 'media session', 'presser', 'media briefing'
        ]
        if any(indicator in title_lower for indicator in interview_indicators):
            return 'interviews', teams
        
        # Classic/Archive - title only
        classic_indicators = [
            'classic', 'archive', 'throwback', 'on this day',
            'vintage', 'retro', 'from the vault', 'memories'
        ]
        if any(indicator in title_lower for indicator in classic_indicators):
            return 'classic', teams
    
        
        return 'other', teams
    
# West Indies Cricket channel - only use title
    if channel_id == 'UC2MHTOXktfTK26aDKyQs3cQ':  # West Indies Cricket channel ID
        # Match Highlights - ONLY check title
        highlight_indicators = [
            'highlights', 'match highlights', 'innings highlights',
            'batting highlights', 'bowling highlights'
        ]
        
        # Check for highlights in title only
        if any(indicator in title_lower for indicator in highlight_indicators):
            if any(indicator in title_lower for indicator in ['classic', 'archive', 'throwback', 'on this day']):
                return 'classic', teams
            return 'matches', teams
        
        # Press/Interviews - title only
        interview_indicators = [
            'interview', 'press conference', 'press', 'conference',
            'speaks to media', 'media session', 'presser', 'media briefing'
        ]
        if any(indicator in title_lower for indicator in interview_indicators):
            return 'interviews', teams
        
        # Classic/Archive - title only
        classic_indicators = [
            'classic', 'archive', 'throwback', 'on this day',
            'vintage', 'retro', 'from the vault', 'memories'
        ]
        if any(indicator in title_lower for indicator in classic_indicators):
            return 'classic', teams

        # Additional match indicators - only if not already categorized
        match_indicators = [
            ' vs ', ' v ', 'test match', 't20', 'odi', 
            'final', 'semi final', 'quarter final'
        ]
        if any(indicator in title_lower for indicator in match_indicators):
            if any(indicator in title_lower for indicator in classic_indicators):
                return 'classic', teams
            return 'matches', teams
        
        return 'other', teams
    
    # For all other channels, use both title and description
    # Match Highlights - ONLY check title for highlights
    highlight_indicators = [
        'highlights', 'match highlights', 'innings highlights',
        'batting highlights', 'bowling highlights'
    ]
    
    # Check for highlights in title only
    if any(indicator in title_lower for indicator in highlight_indicators):
        if any(indicator in title_lower for indicator in ['classic', 'archive', 'throwback', 'on this day']):
            return 'classic', teams
        return 'matches', teams
    
    # For other categories, check both title and description
    combined_text = f"{title_lower} {description_lower}"
    
    # Press/Interviews
    interview_indicators = [
        'interview', 'press conference', 'press', 'conference',
        'speaks to media', 'media session', 'presser', 'media briefing',
        'post match press', 'pre match press'
    ]
    
    # Classic/Archive
    classic_indicators = [
        'classic', 'archive', 'throwback', 'on this day',
        'vintage', 'retro', 'from the vault', 'memories'
    ]
    
    if any(indicator in combined_text for indicator in interview_indicators):
        return 'interviews', teams
    
    if any(indicator in combined_text for indicator in classic_indicators):
        return 'classic', teams
    
    # Additional match indicators - only if not already categorized
    match_indicators = [
        ' vs ', ' v ', 'test match', 't20', 'odi', 
        'final', 'semi final', 'quarter final'
    ]
    if any(indicator in combined_text for indicator in match_indicators):
        if any(indicator in combined_text for indicator in classic_indicators):
            return 'classic', teams
        return 'matches', teams
    
    # If no specific category is found
    return 'other', teams

class VideoFetcher:
    def __init__(self, api_keys, base_path=None):
        self.key_manager = YouTubeKeyManager(api_keys)
        self.youtube = None
        
        # Use base_path if provided, otherwise use default
        self.base_path = base_path or '.'
        
        # Create static/data directory if it doesn't exist
        os.makedirs(f'{self.base_path}/static/data', exist_ok=True)
    
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
                maxResults=400,
                type="video"
            )
            response = request.execute()
            
            videos = []
            video_ids = [item['id']['videoId'] for item in response.get('items', [])]
            
            if not video_ids:
                return []
            
            # Get detailed video information
            video_response = self.youtube.videos().list(
                part="snippet,contentDetails,statistics,status",
                id=','.join(video_ids)
            ).execute()
            
            for video in video_response.get('items', []):
                if (video['status'].get('embeddable', False) and 
                    video['status'].get('privacyStatus') == 'public' and 
                    not is_short(video)):
                    try:
                        # Get category and teams using both title and description
                        category, teams = categorize_video(
                            video['snippet']['title'],
                            video['snippet'].get('description', ''),
                            video['snippet'].get('channelId', '')
                        )
                        
                        video_data = {
                            'id': video['id'],
                            'title': video['snippet']['title'],
                            'thumbnail_src': get_best_thumbnail(video),
                            'thumbnail_url': get_best_thumbnail(video),
                            'duration': video['contentDetails']['duration'],
                            'views': video['statistics'].get('viewCount', 'N/A'),
                            'category': category,
                            'teams': teams,
                            'channel_id': channel_id,
                            'channel_name': channel_name,
                            'upload_date': video['snippet']['publishedAt']
                        }
                        videos.append(video_data)
                        
                        if len(videos) >= 200:
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
    
    def fetch_classic_matches(self):
        try:
            self.youtube = self.get_youtube_service()
            
            # Search for classic cricket match highlights
            request = self.youtube.search().list(
                part="id",
                q="classic cricket match highlights",
                order="viewCount",  # Changed to viewCount to prioritize popular videos
                maxResults=200,
                type="video",
                videoDuration="medium"  # Filter for medium length videos
            )
            response = request.execute()
            
            videos = []
            video_ids = [item['id']['videoId'] for item in response.get('items', [])]
            
            if not video_ids:
                return []
            
            # Get detailed video information
            video_response = self.youtube.videos().list(
                part="snippet,contentDetails,statistics,status",
                id=','.join(video_ids)
            ).execute()
            
            for video in video_response.get('items', []):
                if (video['status'].get('embeddable', False) and 
                    video['status'].get('privacyStatus') == 'public' and 
                    not is_short(video)):
                    try:
                        # Check if video has at least 100k views
                        view_count = int(video['statistics'].get('viewCount', '0'))
                        if view_count < 100000:
                            continue
                            
                        video_data = {
                            'id': video['id'],
                            'title': video['snippet']['title'],
                            'thumbnail_src': get_best_thumbnail(video),
                            'thumbnail_url': get_best_thumbnail(video),
                            'duration': video['contentDetails']['duration'],
                            'views': video['statistics'].get('viewCount', 'N/A'),
                            'category': 'classic',
                            'teams': extract_teams_from_text(video['snippet']['title'] + ' ' + video['snippet'].get('description', '')),
                            'channel_id': video['snippet']['channelId'],
                            'channel_name': video['snippet']['channelTitle'],
                            'upload_date': video['snippet']['publishedAt']
                        }
                        videos.append(video_data)
                        
                        if len(videos) >= 100:
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
                return self.fetch_classic_matches()
            raise
    
    def update_json_files(self, new_videos):
        """Update JSON files with new videos"""
        try:
            # Update category-specific files
            categories = ['matches', 'interviews', 'classic', 'other']
            for category in categories:
                file_path = f'{self.base_path}/static/data/{category}_videos.json'
                existing_videos = load_existing_json(file_path)
                
                # Filter new videos for this category
                new_category_videos = [v for v in new_videos if v['category'] == category]
                
                if new_category_videos:
                    merged_videos = merge_videos(existing_videos, new_category_videos)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(merged_videos, f, ensure_ascii=False, indent=2)
                    logger.info(f"Updated {category}_videos.json with {len(merged_videos)} videos")
            
            # Update all_videos.json
            all_videos_path = f'{self.base_path}/static/data/all_videos.json'
            existing_all = load_existing_json(all_videos_path)
            merged_all = merge_videos(existing_all, new_videos)
            with open(all_videos_path, 'w', encoding='utf-8') as f:
                json.dump(merged_all, f, ensure_ascii=False, indent=2)
            logger.info(f"Updated all_videos.json with {len(merged_all)} total videos")
            
            # Update team stats
            teams_path = f'{self.base_path}/static/data/teams.json'
            team_stats = {}
            
            for video in merged_all:
                for team in video.get('teams', []):
                    if team not in team_stats:
                        team_stats[team] = {
                            'name': team,
                            'video_count': 0,
                            'matches': 0,
                            'latest_video': None
                        }
                    
                    team_stats[team]['video_count'] += 1
                    if video['category'] == 'matches':
                        team_stats[team]['matches'] += 1
                    
                    if not team_stats[team]['latest_video'] or \
                       video['upload_date'] > team_stats[team]['latest_video']['upload_date']:
                        team_stats[team]['latest_video'] = {
                            'id': video['id'],
                            'title': video['title'],
                            'thumbnail_url': video['thumbnail_url'],
                            'upload_date': video['upload_date']
                        }
            
            with open(teams_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'teams': list(team_stats.values()),
                    'variations': get_team_variations()
                }, f, ensure_ascii=False, indent=2)
            logger.info(f"Updated teams.json with {len(team_stats)} teams")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating JSON files: {e}")
            return False
    
    def fetch_all_videos(self):
        all_new_videos = []
        
        # First fetch classic matches from general YouTube search
        logger.info("Fetching classic matches from YouTube")
        try:
            classic_videos = self.fetch_classic_matches()
            all_new_videos.extend(classic_videos)
            logger.info(f"Fetched {len(classic_videos)} classic matches")
        except Exception as e:
            logger.error(f"Error fetching classic matches: {e}")
        
        # Then fetch other categories from specific channels
        for channel_name, channel_id in CRICKET_CHANNELS.items():
            logger.info(f"Fetching new videos for {channel_name}")
            try:
                channel_videos = self.fetch_channel_videos(channel_id, channel_name)
                # Filter out classic matches as we already have them
                channel_videos = [v for v in channel_videos if v['category'] != 'classic']
                all_new_videos.extend(channel_videos)
                logger.info(f"Fetched {len(channel_videos)} new videos from {channel_name}")
            except Exception as e:
                logger.error(f"Error fetching videos for {channel_name}: {e}")
            
            time.sleep(1)
        
        # Update JSON files
        if all_new_videos:
            success = self.update_json_files(all_new_videos)
            if success:
                logger.info(f"Successfully updated JSON files with {len(all_new_videos)} new videos")
            else:
                logger.error("Failed to update JSON files")
        else:
            logger.info("No new videos found")
        
        return all_new_videos

if __name__ == "__main__":
    from config import get_api_keys
    
    api_keys = get_api_keys()
    if not any(api_keys):
        logger.error("No API keys configured")
        exit(1)
    
    fetcher = VideoFetcher(api_keys)
    videos = fetcher.fetch_all_videos()
    
    if not videos:
        logger.error("Failed to fetch any videos")
        exit(1) 