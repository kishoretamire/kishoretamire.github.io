import json
import os
import logging
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import CRICKET_CHANNELS, IPL_VIDEO_BASE_URL, IPL_DISCLAIMER, BCCI_VIDEO_BASE_URL, BCCI_DISCLAIMER
from key_manager import YouTubeKeyManager
import time
import isodate
import requests
from bs4 import BeautifulSoup

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
    """Merge new videos with existing ones, avoiding duplicates and sorting by upload date"""
    # Create a dictionary of existing videos by ID and external_url
    existing_dict = {}
    for video in existing_videos:
        existing_dict[video['id']] = video
        # Also index by external_url for IPL/BCCI videos
        if video.get('source') in ['IPL', 'BCCI'] and video.get('external_url'):
            existing_dict[video['external_url']] = video
    
    # Add or update videos
    for video in new_videos:
        # For IPL/BCCI videos, check both ID and external_url
        if video.get('source') in ['IPL', 'BCCI']:
            # Skip if video already exists by external_url
            if video.get('external_url') in existing_dict:
                logger.debug(f"Skipping duplicate {video.get('source')} video: {video.get('title')}")
                continue
            # Skip if video already exists by ID
            if video['id'] in existing_dict:
                logger.debug(f"Skipping duplicate {video.get('source')} video by ID: {video.get('title')}")
                continue
        else:
            # For YouTube videos, just check ID
            if video['id'] in existing_dict:
                logger.debug(f"Skipping duplicate video: {video.get('title')}")
                continue
        
        # Add new video
        existing_dict[video['id']] = video
        if video.get('source') in ['IPL', 'BCCI'] and video.get('external_url'):
            existing_dict[video['external_url']] = video
    
    # Convert back to list and remove any duplicates
    merged = list({v['id']: v for v in existing_dict.values()}.values())
    
    # Parse dates for sorting
    def parse_date(video):
        try:
            date_str = video.get('upload_date', '')
            if not date_str:
                return datetime.min
                
            if ',' in date_str:  # IPL/BCCI format (e.g., "2nd Nov, 2024")
                parts = date_str.split(',')
                year = parts[1].strip()
                month_day = parts[0].strip().split(' ')
                month = month_day[1]
                day = month_day[0].replace('th', '').replace('nd', '').replace('rd', '').replace('st', '')
                return datetime.strptime(f"{day} {month} {year}", "%d %b %Y")
            elif 'T' in date_str:  # YouTube ISO format with time (e.g., "2022-07-28T21:41:27Z")
                return datetime.strptime(date_str.split('T')[0], "%Y-%m-%d")
            else:  # Simple date format (e.g., "2022-07-28")
                return datetime.strptime(date_str, "%Y-%m-%d")
        except Exception as e:
            logger.error(f"Error parsing date '{date_str}': {e}")
            return datetime.min  # Default to oldest date if parsing fails
    
    # Sort by upload date, newest first
    merged.sort(key=lambda x: parse_date(x), reverse=True)
    
    logger.info(f"Merged videos: {len(merged)} total, {len(new_videos)} new")
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
                maxResults=1000,
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
                        
                        if len(videos) >= 500:
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
                channel_videos = [v for v in channel_videos if v['category'] != 'classic']
                all_new_videos.extend(channel_videos)
                logger.info(f"Fetched {len(channel_videos)} new videos from {channel_name}")
            except Exception as e:
                logger.error(f"Error fetching videos for {channel_name}: {e}")
            time.sleep(1)
        
        # Fetch IPL videos
        logger.info("Fetching IPL videos")
        try:
            ipl_videos = self.fetch_ipl_videos()
            if ipl_videos:
                all_new_videos.extend(ipl_videos)
                logger.info("Successfully fetched IPL videos")
        except Exception as e:
            logger.error(f"Error fetching IPL videos: {e}")
        
        # Fetch BCCI videos
        logger.info("Fetching BCCI videos")
        try:
            bcci_videos = self.fetch_bcci_videos()
            if bcci_videos:
                all_new_videos.extend(bcci_videos)
                logger.info("Successfully fetched BCCI videos")
        except Exception as e:
            logger.error(f"Error fetching BCCI videos: {e}")
        
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
    
    def fetch_ipl_videos(self):
        """Fetch IPL video information by scraping the website"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Cookie': 'BCCI_COOKIE_CONSENT=Y'
            }
            
            response = requests.get(IPL_VIDEO_BASE_URL, headers=headers)
            logger.info(f"IPL response status: {response.status_code}")
            
            if not response.ok:
                logger.error(f"Failed to fetch IPL page: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            video_elements = soup.find_all('a', class_='ap-watch-btn playerpopup')
            logger.info(f"Found {len(video_elements)} IPL video elements")
            
            videos = []
            for element in video_elements:
                try:
                    # Extract data from attributes
                    video_data = {
                        'id': f"ipl_{element['data-videoid']}",
                        'title': element['data-title'],
                        'thumbnail_url': element['data-thumbnile'],
                        'external_url': element['data-share'],
                        'category': 'matches',
                        'teams': self.extract_ipl_teams(element['data-title']),
                        'source': 'IPL',
                        'upload_date': element['data-videodate'],  # Use data-videodate directly
                        'disclaimer': IPL_DISCLAIMER,
                        'channel_name': 'IPL',
                        'views': element['data-videoview']
                    }
                    videos.append(video_data)
                    logger.debug(f"Successfully processed IPL video: {video_data['title']}")
                    
                except Exception as e:
                    logger.error(f"Error processing IPL video element: {e}")
                    continue
            
            logger.info(f"Successfully processed {len(videos)} IPL videos")
            return videos
            
        except Exception as e:
            logger.error(f"Error fetching IPL videos: {e}")
            return []

    def extract_ipl_teams(self, title):
        """Extract team names from IPL video title"""
        # Add logic to extract team names from title
        # Example: "CSK vs MI Highlights" -> ["CSK", "MI"]
        teams = []
        ipl_teams = {
            'CSK': 'Chennai Super Kings',
            'MI': 'Mumbai Indians',
            'RCB': 'Royal Challengers Bangalore',
            'KKR': 'Kolkata Knight Riders',
            'DC': 'Delhi Capitals',
            'PBKS': 'Punjab Kings',
            'RR': 'Rajasthan Royals',
            'SRH': 'Sunrisers Hyderabad',
            'GT': 'Gujarat Titans',
            'LSG': 'Lucknow Super Giants'
        }
        
        for short_name in ipl_teams:
            if short_name in title:
                teams.append(ipl_teams[short_name])
        
        return teams or ['IPL']  # Return ['IPL'] if no teams found

    def parse_ipl_date(self, date_str):
        """Convert IPL date format to ISO format"""
        try:
            # Add date parsing logic based on IPL's date format
            # Return in ISO format: YYYY-MM-DD
            return datetime.strptime(date_str, '%d %B %Y').strftime('%Y-%m-%d')
        except:
            return datetime.now().strftime('%Y-%m-%d')

    def fetch_bcci_videos(self):
        """Fetch BCCI video information by scraping the website"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5'
            }
            
            logger.info(f"Fetching BCCI videos from: {BCCI_VIDEO_BASE_URL}")
            response = requests.get(BCCI_VIDEO_BASE_URL, headers=headers)
            logger.info(f"BCCI response status: {response.status_code}")
            
            if not response.ok:
                logger.error(f"Failed to fetch BCCI page: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            video_elements = soup.find_all('a', class_='playerpopup')
            logger.info(f"Found {len(video_elements)} BCCI video elements")
            
            videos = []
            for element in video_elements:
                try:
                    # Generate video URL from data-videoslug if data-share is missing
                    video_url = element.get('data-share') or f"https://www.bcci.tv/videos/{element.get('data-videoslug', '')}"
                    
                    video_data = {
                        'id': f"bcci_{element['data-videoid']}",
                        'title': element['data-title'],
                        'thumbnail_url': element['data-thumbnile'],
                        'external_url': video_url,  # Use generated URL if data-share is missing
                        'category': 'matches',
                        'teams': extract_teams_from_text(element['data-title']),
                        'source': 'BCCI',
                        'upload_date': element['data-videodate'],
                        'disclaimer': BCCI_DISCLAIMER,
                        'channel_name': 'BCCI',
                        'views': element['data-videoview']
                    }
                    videos.append(video_data)
                    logger.debug(f"Successfully processed BCCI video: {video_data['title']}")
                    
                except Exception as e:
                    logger.error(f"Error processing BCCI video element: {e}")
                    continue
            
            logger.info(f"Successfully processed {len(videos)} BCCI videos")
            return videos
            
        except Exception as e:
            logger.error(f"Error fetching BCCI videos: {e}")
            return []

    def parse_bcci_date(self, date_str):
        """Convert BCCI date format to ISO format"""
        try:
            # Example: "2nd Nov, 2024" -> "2024-11-02"
            return datetime.strptime(date_str, '%dth %b, %Y').strftime('%Y-%m-%d')
        except:
            try:
                # Try alternate format: "2 Nov, 2024" -> "2024-11-02"
                return datetime.strptime(date_str, '%d %b, %Y').strftime('%Y-%m-%d')
            except:
                return datetime.now().strftime('%Y-%m-%d')

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