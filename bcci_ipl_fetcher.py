import json
import boto3
import logging
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from botocore.exceptions import ClientError

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize S3 client
s3 = boto3.client('s3')
BUCKET_NAME = 'latestcrickethighlights-videos'

# Constants
IPL_VIDEO_BASE_URL = "https://www.iplt20.com/videos/highlights"
BCCI_VIDEO_BASE_URL = "https://www.bcci.tv/videos/highlights"
IPL_DISCLAIMER = "IPL videos are available on the official IPLT20.com website. Click to watch on the official platform."
BCCI_DISCLAIMER = "BCCI videos are available on the official BCCI.tv website. Click to watch on the official platform."

# Reusable session for HTTP requests
session = requests.Session()
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5'
}

def fetch_videos(url, source, disclaimer):
    """Generic function to fetch videos from either IPL or BCCI"""
    try:
        response = session.get(url, headers=headers)
        if not response.ok:
            logger.error(f"Failed to fetch {source} page: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        video_elements = soup.find_all('a', class_='playerpopup')
        logger.info(f"Found {len(video_elements)} {source} video elements")
        
        videos = []
        for element in video_elements:
            try:
                video_url = element.get('data-share') or f"https://www.{source.lower()}.tv/videos/{element.get('data-videoslug', '')}"
                
                video_data = {
                    'id': f"{source.lower()}_{element['data-videoid']}",
                    'title': element['data-title'],
                    'thumbnail_url': element['data-thumbnile'],
                    'external_url': video_url,
                    'category': 'matches',
                    'teams': extract_teams_from_text(element['data-title']),
                    'source': source,
                    'upload_date': element['data-videodate'],
                    'disclaimer': disclaimer,
                    'channel_name': source,
                    'views': element.get('data-videoview', 'N/A')
                }
                videos.append(video_data)
            except Exception as e:
                logger.error(f"Error processing {source} video: {e}")
                continue
        
        return videos
    except Exception as e:
        logger.error(f"Error fetching {source} videos: {e}")
        return []

def extract_teams_from_text(text):
    """Extract team names from text"""
    teams = set()
    text_lower = text.lower()
    
    # Use dictionary comprehension for team variations
    team_variations = {
        team: variations for team, variations in {
            'india': ['india', 'ind', 'bcci'],
            'australia': ['australia', 'aus'],
            'england': ['england', 'eng'],
            'pakistan': ['pakistan', 'pak'],
            'south africa': ['south africa', 'sa'],
            'new zealand': ['new zealand', 'nz'],
            'west indies': ['west indies', 'wi'],
            'sri lanka': ['sri lanka', 'sl'],
            'bangladesh': ['bangladesh', 'ban']
        }.items() if any(v in text_lower for v in variations)
    }
    
    teams.update(team_variations.keys())
    return list(map(str.title, teams)) or ['International']

def get_existing_videos(path):
    """Get existing videos from S3 with proper error handling"""
    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key=path)
        return json.loads(response['Body'].read().decode('utf-8'))
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchKey':
            logger.info(f"No existing file found at {path}")
            return []
        else:
            logger.error(f"Error getting {path}: {e}")
            raise
    except Exception as e:
        logger.error(f"Unexpected error getting {path}: {e}")
        return []

def parse_date(video):
    """Parse date from various formats"""
    try:
        date_str = video.get('upload_date', '')
        if not date_str:
            return datetime.min
            
        if ',' in date_str:  # IPL/BCCI format (e.g., "3rd Nov, 2024")
            parts = date_str.split(',')
            year = parts[1].strip()
            month_day = parts[0].strip().split(' ')
            month = month_day[1]
            # Remove ordinal suffixes (st, nd, rd, th)
            day = ''.join(filter(str.isdigit, month_day[0]))
            return datetime.strptime(f"{day} {month} {year}", "%d %b %Y")
        elif 'T' in date_str:  # YouTube ISO format with time
            return datetime.strptime(date_str.split('T')[0], "%Y-%m-%d")
        else:  # Simple date format
            return datetime.strptime(date_str, "%Y-%m-%d")
    except Exception as e:
        logger.error(f"Error parsing date '{date_str}': {e}")
        return datetime.min

def update_json_files(videos):
    """Update JSON files in S3 efficiently"""
    try:
        file_paths = ['static/data/all_videos.json', 'static/data/matches_videos.json']
        
        # Batch get existing files
        existing_videos = {}
        for path in file_paths:
            try:
                response = s3.get_object(Bucket=BUCKET_NAME, Key=path)
                existing_videos[path] = json.loads(response['Body'].read().decode('utf-8'))
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    existing_videos[path] = []
                else:
                    raise
        
        # Process all files in memory first
        updated_files = {}
        for path, existing in existing_videos.items():
            # Create index of existing videos
            video_index = {v['id']: v for v in existing}
            video_index.update({v.get('external_url'): v for v in existing if v.get('external_url')})
            
            # Add new videos
            for video in videos:
                if video['id'] not in video_index and video.get('external_url') not in video_index:
                    video_index[video['id']] = video
            
            # Convert to list and sort by parsed date
            updated_videos = list(video_index.values())
            updated_videos.sort(key=parse_date, reverse=True)
            
            updated_files[path] = updated_videos
        
        # Batch update S3
        for path, content in updated_files.items():
            s3.put_object(
                Bucket=BUCKET_NAME,
                Key=path,
                Body=json.dumps(content, ensure_ascii=False, separators=(',', ':')),
                ContentType='application/json',
                CacheControl='no-cache'
            )
            logger.info(f"Updated {path}")
        
        return True
    except Exception as e:
        logger.error(f"Error updating JSON files: {e}")
        return False

def lambda_handler(event, context):
    try:
        # Fetch videos in parallel using list comprehension
        all_videos = [
            *fetch_videos(IPL_VIDEO_BASE_URL, 'IPL', IPL_DISCLAIMER),
            *fetch_videos(BCCI_VIDEO_BASE_URL, 'BCCI', BCCI_DISCLAIMER)
        ]
        
        if not all_videos:
            return {
                'statusCode': 200,
                'body': 'No new videos found'
            }
        
        success = update_json_files(all_videos)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Successfully processed videos' if success else 'Failed to update files',
                'count': len(all_videos)
            }, separators=(',', ':'))
        }
        
    except Exception as e:
        logger.error(f"Error in lambda function: {e}")
        return {
            'statusCode': 500,
            'body': str(e)
        } 