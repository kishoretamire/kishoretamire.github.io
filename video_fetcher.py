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
import re

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
    """Get variations of team names with more precise matching"""
    return {
        'australia': ['australia', 'aussies'],
        'india': ['india', 'ind'],
        'england': ['england', 'eng'],
        'pakistan': ['pakistan', 'pak'],
        'south africa': ['south africa', 'proteas'],
        'new zealand': ['new zealand', 'nz', 'blackcaps'],
        'west indies': ['west indies', 'windies'],  # Removed 'wi' as it's too ambiguous
        'sri lanka': ['sri lanka', 'lanka'],
        'bangladesh': ['bangladesh', 'ban'],
        'afghanistan': ['afghanistan', 'afg'],
        'ireland': ['ireland', 'ire'],
        'zimbabwe': ['zimbabwe', 'zim']
    }

def extract_teams_from_text(text):
    """Extract team names from text using variations with more precise matching"""
    teams = set()
    text_lower = text.lower()
    team_variations = get_team_variations()
    
    # First check for explicit match patterns with word boundaries
    vs_patterns = [
        r'\b(\w+(?:\s+\w+)*)\s+(?:vs|v|versus)\s+(\w+(?:\s+\w+)*)\b',  # normal vs pattern
        r'\b(\w+(?:\s+\w+)*)\s+(?:vs|v|versus)\s+(\w+(?:\s+\w+)*)\b',  # with extra spaces
        r'(\w+(?:\s+\w+)*)\s*\|\s*(\w+(?:\s+\w+)*)'  # pattern with | separator
    ]
    
    # Try each pattern to find the teams
    matched_teams = []
    for pattern in vs_patterns:
        matches = re.findall(pattern, text_lower)
        if matches:
            # Take only the first match as it's usually the main teams
            team1, team2 = matches[0][0].strip(), matches[0][1].strip()
            matched_teams = [team1, team2]
            break
    
    if not matched_teams:
        return []  # If no vs pattern found, return empty list
    
    # Now check each team variation against ONLY the matched teams
    for team, variations in team_variations.items():
        for matched_team in matched_teams:
            # Clean up the variation and add word boundaries
            for variation in variations:
                var_pattern = r'\b' + re.escape(variation.strip()) + r'\b'
                if re.search(var_pattern, matched_team):
                    # Check if it's a women's team
                    is_womens = any(w in text_lower for w in [' women', ' w vs', 'vs w', 'w xi'])
                    # Check if it's U19/Under-19
                    is_u19 = any(u in text_lower for u in ['u19', 'under-19', 'under 19'])
                    # Check if it's A team
                    is_a_team = any(a in text_lower for a in ['-a team', ' a vs', 'a xi'])
                    
                    base_team = team.title()
                    if is_womens:
                        teams.add(f"{base_team} Women")
                    elif is_u19:
                        teams.add(f"{base_team} U19")
                    elif is_a_team:
                        teams.add(f"{base_team} A")
                    else:
                        teams.add(base_team)
                    break
    
    return list(teams)

def categorize_video(title, description='', channel_id='', source=''):
    """Categorize video based on title and description"""
    title_lower = title.lower()
    description_lower = description.lower() if description else ''
    
    # Extract teams from both title and description
    teams = extract_teams_from_text(f"{title_lower} {description_lower}")
    
    # For BCCI videos, use strict highlights check
    if source == 'BCCI':
        # Must explicitly contain 'highlights' keyword
        if 'highlights' not in title_lower:
            return 'other', teams
            
        # Check for non-match highlight types
        non_match_highlights = [
            'practice', 'training', 'tour', 'ceremony', 'celebration',
            'event', 'press conference', 'interview', 'preview',
            'behind the scenes', 'dressing room', 'trophy', 'award',
            'fan', 'journey', 'story', 'memories', 'reaction'
        ]
        
        if any(phrase in title_lower for phrase in non_match_highlights):
            return 'other', teams
            
        return 'matches', teams
    
    # For other sources, use existing categorization logic
    # Check for live videos first - these go to 'other' category
    if 'live' in title_lower:
        return 'other', teams
    
    # Common indicators
    highlight_indicators = [
        'highlights', 'match highlights', 'innings highlights',
        'batting highlights', 'bowling highlights', ' vs ', ' v ',
        'match summary', 'key moments', 'match report',
        'day 1 highlights', 'day 2 highlights', 'day 3 highlights',
        'day 4 highlights', 'day 5 highlights'
    ]
    
    domestic_indicators = [
        'domestic', 'county', 'shield', 'trophy', 'cup',
        'ranji', 'irani', 'syed mushtaq', 'vijay hazare',
        'super50', 'plunket shield', 'sheffield', 'marsh',
        'royal london', 't20 blast', 'vitality blast',
        'cpl', 'bbl', 'psl', 'bpl', 'lanka premier', 'hundred'
    ]
    
    international_indicators = [
        'test match', 'test series', 'odi series', 't20i',
        'world cup', 'champions trophy', 'asia cup',
        'bilateral', 'tri-series', 'tri series',
        'international', ' vs ', ' v '
    ]
    
    # Check for highlights in title
    if any(indicator in title_lower for indicator in highlight_indicators):
        # Check if it's domestic or international
        is_domestic = any(indicator in f"{title_lower} {description_lower}" 
                        for indicator in domestic_indicators)
        
        if is_domestic:
            return 'domestic', teams
            
        if any(indicator in f"{title_lower} {description_lower}" 
               for indicator in international_indicators):
            return 'matches', teams
            
        # Default to matches if we can't determine
        return 'matches', teams
    
    # Rest of your existing categorization logic...
    # ... (keep the interview and classic detection logic)
    
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
                        # Pass source as channel name for categorization
                        category, teams = categorize_video(
                            video['snippet']['title'],
                            video['snippet'].get('description', ''),
                            video['snippet'].get('channelId', ''),
                            channel_name  # Add source parameter
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
                            'source': channel_name,  # Add source field
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
    
    def is_recent_relevant_video(self, video_title, upload_date):
        """
        Check if video is recent and relevant (not archive)
        """
        title_lower = video_title.lower()
        
        # Filter out archive videos
        if 'archive' in title_lower:
            return False
        
        # Check for years in title (like 2023, 2022, etc)
        years = re.findall(r'20\d{2}', title_lower)
        if years:
            # If any year mentioned is before 2025, filter it out
            if any(int(year) < 2025 for year in years):
                return False
        
        # Convert upload_date to datetime for comparison
        if upload_date:
            try:
                upload_datetime = datetime.strptime(upload_date, '%Y-%m-%d')
                # Filter videos uploaded before 2025
                if upload_datetime.year < 2025:
                    return False
            except ValueError:
                pass
            
        return True

    def is_classic_video(self, video_title, upload_date):
        """
        Check if video should be categorized as classic (pre-2023)
        """
        title_lower = video_title.lower()
        
        # Check for explicit classic indicators
        classic_indicators = [
            'classic', 'vintage', 'retro', 'throwback',
            'memorable', 'history', 'historical', 'legend'
        ]
        
        # First check if it has classic indicators and years before 2023
        if any(indicator in title_lower for indicator in classic_indicators):
            years = re.findall(r'20\d{2}|19\d{2}', title_lower)
            if years:
                # If any year mentioned is before 2023, consider it classic
                if any(int(year) < 2023 for year in years):
                    return True
                else:
                    return False  # More recent years should go to matches even if marked as classic
        
        # Check for years in title (like 2022, 2021, etc)
        years = re.findall(r'20\d{2}|19\d{2}', title_lower)
        if years:
            # If any year mentioned is before 2023, consider it classic
            if any(int(year) < 2023 for year in years):
                return True
        
        # Check upload date
        if upload_date:
            try:
                upload_datetime = datetime.strptime(upload_date.split('T')[0], '%Y-%m-%d')
                # If uploaded before 2023, consider it classic
                if upload_datetime.year < 2023:
                    return True
            except ValueError:
                pass
            
        return False

    def update_json_files(self, new_videos):
        """Update JSON files with new videos"""
        try:
            # Process videos - filter BCCI non-highlights and handle classics
            processed_videos = []
            for video in new_videos:
                # For BCCI videos, apply strict highlights check
                if video.get('source') == 'BCCI':
                    if not self.is_bcci_highlight_video(video['title']):
                        video['category'] = 'other'  # Move non-highlights to other
                
                # Re-extract teams from title
                video['teams'] = extract_teams_from_text(video['title'])
                
                # Handle classic categorization
                if self.is_classic_video(video['title'], video.get('upload_date')):
                    video['category'] = 'classic'
                elif video['category'] == 'matches':
                    if not self.is_classic_video(video['title'], video.get('upload_date')):
                        processed_videos.append(video)
                    continue
                processed_videos.append(video)
            
            categories = ['matches', 'domestic', 'interviews', 'classic', 'other']
            for category in categories:
                file_path = f'{self.base_path}/static/data/{category}_videos.json'
                existing_videos = load_existing_json(file_path)
                
                # Filter and update existing videos
                filtered_existing = []
                for video in existing_videos:
                    # Re-extract teams from title for existing videos
                    video['teams'] = extract_teams_from_text(video['title'])
                    
                    # For BCCI videos, apply strict highlights check
                    if video.get('source') == 'BCCI':
                        if not self.is_bcci_highlight_video(video['title']):
                            video['category'] = 'other'  # Move non-highlights to other
                    
                    # Handle classic categorization
                    if self.is_classic_video(video['title'], video.get('upload_date')):
                        video['category'] = 'classic'
                    
                    # Only include videos that belong in this category
                    if video['category'] == category:
                        filtered_existing.append(video)
                
                # Filter new videos for this category
                new_category_videos = [v for v in processed_videos if v['category'] == category]
                
                if new_category_videos or filtered_existing:
                    merged_videos = merge_videos(filtered_existing, new_category_videos)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(merged_videos, f, ensure_ascii=False, indent=2)
                    logger.info(f"Updated {category}_videos.json with {len(merged_videos)} videos")
            
            # Update all_videos.json with reprocessed teams
            all_videos_path = f'{self.base_path}/static/data/all_videos.json'
            existing_all = load_existing_json(all_videos_path)
            
            # Reprocess all existing videos
            for video in existing_all:
                # Re-extract teams
                video['teams'] = extract_teams_from_text(video['title'])
                
                # Update categorization
                if self.is_classic_video(video['title'], video.get('upload_date')):
                    video['category'] = 'classic'
                elif video.get('source') == 'BCCI' and not self.is_bcci_highlight_video(video['title']):
                    video['category'] = 'other'
            
            merged_all = merge_videos(existing_all, processed_videos)
            with open(all_videos_path, 'w', encoding='utf-8') as f:
                json.dump(merged_all, f, ensure_ascii=False, indent=2)
            logger.info(f"Updated all_videos.json with {len(merged_all)} total videos")
            
            # Update team stats with domestic matches
            teams_path = f'{self.base_path}/static/data/teams.json'
            team_stats = {}
            
            for video in merged_all:
                for team in video.get('teams', []):
                    if team not in team_stats:
                        team_stats[team] = {
                            'name': team,
                            'video_count': 0,
                            'matches': 0,
                            'domestic_matches': 0,  # Add counter for domestic matches
                            'latest_video': None
                        }
                    
                    team_stats[team]['video_count'] += 1
                    
                    # Count both international and domestic matches
                    if video['category'] == 'matches':
                        team_stats[team]['matches'] += 1
                    elif video['category'] == 'domestic':
                        team_stats[team]['domestic_matches'] += 1
                    
                    # Update latest video if current video is newer
                    if not team_stats[team]['latest_video'] or \
                       video['upload_date'] > team_stats[team]['latest_video']['upload_date']:
                        team_stats[team]['latest_video'] = {
                            'id': video['id'],
                            'title': video['title'],
                            'thumbnail_url': video['thumbnail_url'],
                            'upload_date': video['upload_date'],
                            'category': video['category']  # Add category to latest video info
                        }
            
            # Create a new structure for teams.json that includes domestic teams
            teams_data = {
                'international_teams': [],
                'domestic_teams': [],
                'variations': get_team_variations(),
                'domestic_tournaments': {
                    'india': ['ranji trophy', 'vijay hazare', 'syed mushtaq ali', 'duleep trophy'],
                    'england': ['county championship', 't20 blast', 'royal london cup', 'the hundred'],
                    'australia': ['sheffield shield', 'marsh cup', 'big bash'],
                    'west_indies': ['super50 cup', 'regional 4-day', 'cpl'],
                    'south_africa': ['4-day series', 'csa t20', 'momentum cup'],
                    'new_zealand': ['plunket shield', 'ford trophy', 'super smash'],
                    'pakistan': ['quaid-e-azam trophy', 'pakistan cup', 'national t20'],
                    'bangladesh': ['national cricket league', 'bangladesh premier league'],
                    'sri_lanka': ['premier league tournament', 'lanka premier league']
                }
            }
            
            # Categorize teams as international or domestic
            for team_data in team_stats.values():
                if self.is_international_team(team_data['name']):
                    teams_data['international_teams'].append(team_data)
                else:
                    teams_data['domestic_teams'].append(team_data)
            
            # Sort teams by video count
            teams_data['international_teams'].sort(key=lambda x: x['video_count'], reverse=True)
            teams_data['domestic_teams'].sort(key=lambda x: x['video_count'], reverse=True)
            
            with open(teams_path, 'w', encoding='utf-8') as f:
                json.dump(teams_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Updated teams.json with {len(teams_data['international_teams'])} international teams and {len(teams_data['domestic_teams'])} domestic teams")
            
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
                    title = element['data-title']
                    
                    # Strict highlights check
                    is_highlight = self.is_bcci_highlight_video(title)
                    
                    # Only process if it's a proper match highlight
                    if is_highlight:
                        video_url = element.get('data-share') or f"https://www.bcci.tv/videos/{element.get('data-videoslug', '')}"
                        
                        video_data = {
                            'id': f"bcci_{element['data-videoid']}",
                            'title': title,
                            'thumbnail_url': element['data-thumbnile'],
                            'external_url': video_url,
                            'category': 'matches',
                            'teams': extract_teams_from_text(title),
                            'source': 'BCCI',
                            'upload_date': element['data-videodate'],
                            'disclaimer': BCCI_DISCLAIMER,
                            'channel_name': 'BCCI',
                            'views': element['data-videoview']
                        }
                        videos.append(video_data)
                        logger.debug(f"Added BCCI highlight video: {title}")
                    else:
                        logger.debug(f"Skipped non-highlight BCCI video: {title}")
                    
                except Exception as e:
                    logger.error(f"Error processing BCCI video element: {e}")
                    continue
            
            logger.info(f"Successfully processed {len(videos)} BCCI highlight videos")
            return videos
            
        except Exception as e:
            logger.error(f"Error fetching BCCI videos: {e}")
            return []

    def is_bcci_highlight_video(self, title):
        """
        Determine if a BCCI video is a highlights video - very strict version
        Only allow videos that explicitly contain 'highlights' in the title
        """
        title_lower = title.lower()
        
        # Must contain 'highlights' explicitly
        if 'highlights' not in title_lower:
            return False
        
        # Even if it has 'highlights', check it's not one of these non-match highlight types
        non_match_highlights = [
            'practice highlights',
            'training highlights',
            'tour highlights',
            'ceremony highlights',
            'celebration highlights',
            'event highlights',
            'press conference highlights',
            'interview highlights',
            'preview highlights',
            'behind the scenes highlights',
            'dressing room highlights',
            'trophy highlights',
            'award highlights',
            'fan highlights',
            'journey highlights',
            'story highlights',
            'memories highlights',
            'reaction highlights'
        ]
        
        # If it contains any of the non-match highlight phrases, reject it
        if any(phrase in title_lower for phrase in non_match_highlights):
            return False
        
        # Additional check to ensure it's a match highlight
        match_indicators = [
            'match highlights',
            'innings highlights',
            'day 1 highlights',
            'day 2 highlights',
            'day 3 highlights',
            'day 4 highlights',
            'day 5 highlights',
            'test highlights',
            'odi highlights',
            't20 highlights',
            't20i highlights'
        ]
        
        # Must contain at least one match indicator
        return any(indicator in title_lower for indicator in match_indicators)

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

    def is_international_team(self, team_name):
        """Determine if a team is an international team"""
        international_teams = set(get_team_variations().keys())
        # Add women's and U19 variations
        for team in list(international_teams):
            international_teams.add(f"{team} Women")
            international_teams.add(f"{team} U19")
            international_teams.add(f"{team} A")
        
        return team_name.lower() in {t.lower() for t in international_teams}

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