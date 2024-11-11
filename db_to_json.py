import sqlite3
import json
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def convert_db_to_json():
    """Convert videos database to JSON files"""
    try:
        logger.info("Starting database to JSON conversion")
        
        # Create static/data directory if it doesn't exist
        os.makedirs('static/data', exist_ok=True)
        
        with sqlite3.connect('videos.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get all videos
            cursor.execute('SELECT * FROM videos ORDER BY upload_date DESC')
            all_videos = [dict(row) for row in cursor.fetchall()]
            
            logger.info(f"Found {len(all_videos)} videos in database")
            
            # Write all videos to a single file
            with open('static/data/all_videos.json', 'w', encoding='utf-8') as f:
                json.dump(all_videos, f, ensure_ascii=False, indent=2)
            logger.info("Wrote all_videos.json")
            
            # Write category-specific files
            categories = ['matches', 'interviews', 'training', 'classic', 'other']
            for category in categories:
                category_videos = [v for v in all_videos if v['category'] == category]
                with open(f'static/data/{category}_videos.json', 'w', encoding='utf-8') as f:
                    json.dump(category_videos, f, ensure_ascii=False, indent=2)
                logger.info(f"Wrote {category}_videos.json with {len(category_videos)} videos")
            
            # Generate teams data
            teams = {}
            match_videos = [v for v in all_videos if v['category'] == 'matches']
            for video in match_videos:
                video_teams = extract_teams(video['title'])
                for team in video_teams:
                    if team not in teams:
                        teams[team] = {
                            'name': team,
                            'video_count': 0,
                            'latest_video': None
                        }
                    teams[team]['video_count'] += 1
                    
                    if not teams[team]['latest_video'] or \
                       video['upload_date'] > teams[team]['latest_video']['upload_date']:
                        teams[team]['latest_video'] = {
                            'id': video['id'],
                            'title': video['title'],
                            'upload_date': video['upload_date']
                        }
            
            # Save teams data
            with open('static/data/teams.json', 'w', encoding='utf-8') as f:
                json.dump(list(teams.values()), f, ensure_ascii=False, indent=2)
            logger.info(f"Wrote teams.json with {len(teams)} teams")
            
            logger.info("JSON conversion completed successfully")
            return True
            
    except Exception as e:
        logger.error(f"Error converting database to JSON: {e}")
        return False

def extract_teams(title):
    """Extract team names from video title"""
    teams = set()
    title_lower = title.lower()
    
    team_names = [
        'australia', 'india', 'england', 'pakistan', 
        'south africa', 'new zealand', 'west indies', 
        'sri lanka', 'bangladesh', 'zimbabwe'
    ]
    
    for team in team_names:
        if team in title_lower:
            teams.add(team.title())
    
    return list(teams)

if __name__ == "__main__":
    success = convert_db_to_json()
    if not success:
        exit(1) 