import json
import requests
import logging
import time

from config import CRICKET_CHANNELS

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def subscribe_to_channel(channel_id, callback_url):
    """Subscribe to a YouTube channel's updates"""
    try:
        hub_url = 'https://pubsubhubbub.appspot.com/subscribe'
        topic_url = f'https://www.youtube.com/xml/feeds/videos.xml?channel_id={channel_id}'
        
        # Updated request format
        data = {
            'hub.callback': callback_url,
            'hub.topic': topic_url,
            'hub.verify': 'async',  # Changed to async
            'hub.mode': 'subscribe',
            'hub.verify_token': 'cricket_videos',  # Added verification token
            'hub.lease_seconds': '432000'  # 5 days lease
        }
        
        # Log request details
        logger.info(f"Subscribing to channel {channel_id}")
        logger.info(f"Callback URL: {callback_url}")
        logger.info(f"Topic URL: {topic_url}")
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        response = requests.post(hub_url, data=data, headers=headers)
        
        # Log response details
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response body: {response.text}")
        
        # Handle different status codes
        if response.status_code == 202:
            logger.info(f"Successfully subscribed to channel: {channel_id}")
            return True
        elif response.status_code == 409:
            logger.info(f"Subscription already exists for channel: {channel_id}")
            return True
        else:
            logger.error(f"Failed to subscribe to channel: {channel_id}. Status: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error subscribing to channel {channel_id}: {e}")
        return False

def lambda_handler(event, context):
    """AWS Lambda handler"""
    try:
        # Get API Gateway URL from environment or event
        callback_url = 'https://582w4jjp90.execute-api.us-east-2.amazonaws.com/prod/webhook'
        
        # Log callback URL
        logger.info(f"Using callback URL: {callback_url}")
        
        results = {}
        for channel_name, channel_id in CRICKET_CHANNELS.items():
            logger.info(f"Processing channel: {channel_name} ({channel_id})")
            success = subscribe_to_channel(channel_id, callback_url)
            results[channel_name] = 'Success' if success else 'Failed'
            time.sleep(1)  # Delay between requests
        
        # Count successes and failures
        successes = sum(1 for result in results.values() if result == 'Success')
        failures = len(results) - successes
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Processed {len(results)} channels. {successes} succeeded, {failures} failed.',
                'details': results
            })
        }
        
    except Exception as e:
        logger.error(f"Error in lambda function: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }

if __name__ == "__main__":
    # For local testing
    lambda_handler(None, None) 