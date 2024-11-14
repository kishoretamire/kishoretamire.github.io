import json
import boto3
import logging
from video_fetcher import categorize_video
from config import get_api_keys, CRICKET_CHANNELS
import xml.etree.ElementTree as ET
from googleapiclient.discovery import build
import isodate

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize global clients for connection reuse
s3 = boto3.client('s3')
BUCKET_NAME = 'latestcrickethighlights-videos'
youtube = None

def get_youtube_client():
    """Get or create YouTube client using connection reuse"""
    global youtube
    if youtube is None:
        api_keys = get_api_keys()
        youtube = build('youtube', 'v3', developerKey=api_keys[0], cache_discovery=False)
    return youtube

def is_short(video_details):
    """Optimized short video check"""
    try:
        duration = isodate.parse_duration(video_details['contentDetails']['duration'])
        if duration.total_seconds() <= 60:
            return True

        title = video_details['snippet']['title'].lower()
        return any(tag in title for tag in ['#shorts', '#short', '#ytshorts'])
    except Exception as e:
        logger.error(f"Error checking if video is short: {e}")
        return False

def get_video_details(video_id):
    """Get video details with minimal fields"""
    try:
        client = get_youtube_client()
        response = client.videos().list(
            part="snippet,contentDetails,statistics",
            id=video_id,
            fields="items(id,snippet(title,description,channelId,channelTitle,publishedAt,thumbnails/high/url),contentDetails/duration,statistics/viewCount)"
        ).execute()
        
        if response['items']:
            return response['items'][0]
        return None
    except Exception as e:
        logger.error(f"Error getting video details: {e}")
        return None

def update_json_files(new_video, category):
    """Update JSON files efficiently"""
    try:
        file_paths = {
            'all': 'static/data/all_videos.json',
            category: f'static/data/{category}_videos.json'
        }
        
        updated = False
        for key, path in file_paths.items():
            try:
                # Get existing videos
                response = s3.get_object(Bucket=BUCKET_NAME, Key=path)
                videos = json.loads(response['Body'].read().decode('utf-8'))
            except s3.exceptions.NoSuchKey:
                videos = []
            
            # Check for duplicates
            if not any(v['id'] == new_video['id'] for v in videos):
                videos.insert(0, new_video)  # Add to beginning
                
                # Upload with minimal metadata
                s3.put_object(
                    Bucket=BUCKET_NAME,
                    Key=path,
                    Body=json.dumps(videos, ensure_ascii=False, separators=(',', ':')),
                    ContentType='application/json'
                )
                updated = True
                logger.info(f"Updated {path}")
        
        return updated
    except Exception as e:
        logger.error(f"Error updating JSON files: {e}")
        return False

def lambda_handler(event, context):
    """Optimized Lambda handler"""
    try:
        # Handle verification request quickly
        if event.get('queryStringParameters', {}).get('hub.challenge'):
            return {
                'statusCode': 200,
                'body': event['queryStringParameters']['hub.challenge']
            }
        
        # Parse notification
        body = event.get('body', '')
        if not body:
            return {'statusCode': 400, 'body': 'No body in request'}
        
        # Parse XML efficiently
        root = ET.fromstring(body)
        entry = root.find('{http://www.w3.org/2005/Atom}entry')
        if not entry:
            return {'statusCode': 400, 'body': 'No entry in feed'}
        
        # Get video and channel IDs
        video_id = entry.find('{http://www.youtube.com/xml/schemas/2015}videoId').text
        channel_id = entry.find('{http://www.youtube.com/xml/schemas/2015}channelId').text
        
        # Quick channel validation
        if channel_id not in CRICKET_CHANNELS.values():
            return {'statusCode': 200, 'body': 'Not from monitored channel'}
        
        # Get video details
        video_details = get_video_details(video_id)
        if not video_details:
            return {'statusCode': 400, 'body': 'Could not get video details'}
        
        # Check if short
        if is_short(video_details):
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Ignored short video'})
            }
        
        # Categorize video
        category, teams = categorize_video(
            video_details['snippet']['title'],
            video_details['snippet'].get('description', ''),
            channel_id
        )
        
        # Create video object with minimal data
        new_video = {
            'id': video_id,
            'title': video_details['snippet']['title'],
            'thumbnail_url': video_details['snippet']['thumbnails']['high']['url'],
            'duration': video_details['contentDetails']['duration'],
            'views': video_details['statistics'].get('viewCount', 'N/A'),
            'category': category,
            'teams': teams,
            'channel_id': channel_id,
            'channel_name': video_details['snippet']['channelTitle'],
            'upload_date': video_details['snippet']['publishedAt']
        }
        
        # Update files
        success = update_json_files(new_video, category)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Successfully processed new video' if success else 'Failed to process video',
                'video_id': video_id,
                'category': category
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return {
            'statusCode': 500,
            'body': str(e)
        } 