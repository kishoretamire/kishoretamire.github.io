import json
import boto3
import logging
from video_fetcher import VideoFetcher
from config import get_api_keys
import os

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize S3 client
s3 = boto3.client('s3')
BUCKET_NAME = 'latestcrickethighlights-videos'  # Your S3 bucket name

def download_existing_files():
    """Download existing JSON files from S3 to local /tmp directory"""
    try:
        # Create tmp/static/data directory
        os.makedirs('/tmp/static/data', exist_ok=True)
        
        # List of files to download
        files = [
            'all_videos.json',
            'matches_videos.json',
            'interviews_videos.json',
            'classic_videos.json',
            'other_videos.json',
            'teams.json'
        ]
        
        for file_name in files:
            try:
                s3_path = f'static/data/{file_name}'
                local_path = f'/tmp/static/data/{file_name}'
                
                # Download file from S3
                s3.download_file(BUCKET_NAME, s3_path, local_path)
                logger.info(f"Downloaded {file_name} from S3")
            except s3.exceptions.NoSuchKey:
                # Create empty file if it doesn't exist in S3
                with open(local_path, 'w') as f:
                    json.dump([], f)
                logger.info(f"Created new empty file {file_name}")
            except Exception as e:
                logger.error(f"Error downloading {file_name}: {e}")
                
    except Exception as e:
        logger.error(f"Error setting up local files: {e}")
        raise

def upload_to_s3():
    """Upload updated JSON files from local /tmp to S3"""
    try:
        files = [
            'all_videos.json',
            'matches_videos.json',
            'interviews_videos.json',
            'classic_videos.json',
            'other_videos.json',
            'teams.json'
        ]
        
        for file_name in files:
            try:
                local_path = f'/tmp/static/data/{file_name}'
                s3_path = f'static/data/{file_name}'
                
                # Upload file to S3
                s3.upload_file(
                    local_path,
                    BUCKET_NAME,
                    s3_path,
                    ExtraArgs={
                        'ContentType': 'application/json',
                        'CacheControl': 'no-cache'
                    }
                )
                logger.info(f"Uploaded {file_name} to S3")
            except Exception as e:
                logger.error(f"Error uploading {file_name}: {e}")
                
    except Exception as e:
        logger.error(f"Error uploading files to S3: {e}")
        raise

def lambda_handler(event, context):
    try:
        logger.info("Starting video update process")
        
        # Download existing files from S3
        download_existing_files()
        
        # Initialize video fetcher with tmp path
        api_keys = get_api_keys()
        fetcher = VideoFetcher(api_keys, base_path='/tmp')
        
        # Fetch and update videos
        # This will automatically update the local JSON files in /tmp
        new_videos = fetcher.fetch_all_videos()
        
        if new_videos:
            # Upload updated files to S3
            upload_to_s3()
            
            logger.info(f"Successfully processed {len(new_videos)} new videos")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Successfully updated videos',
                    'new_videos_count': len(new_videos)
                })
            }
        else:
            logger.info("No new videos found")
            return {
                'statusCode': 200,
                'body': json.dumps('No new videos to update')
            }
        
    except Exception as e:
        logger.error(f"Error in lambda function: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error updating videos: {str(e)}')
        }

if __name__ == "__main__":
    lambda_handler(None, None) 