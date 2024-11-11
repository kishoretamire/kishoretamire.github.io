import sqlite3
import json
import os
import logging
from datetime import datetime

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

def convert_db_to_json():
    """Convert videos database to JSON files, updating only new content"""
    try:
        logger.info("Starting database to JSON conversion")
        
        # Create static/data directory if it doesn't exist
        os.makedirs('static/data', exist_ok=True)
        
        with sqlite3.connect('videos.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get latest videos from database
            cursor.execute('SELECT * FROM videos ORDER BY upload_date DESC')
            new_videos = [dict(row) for row in cursor.fetchall()]
            
            if not new_videos:
                logger.warning("No videos found in database")
                return False
            
            # Update all_videos.json
            all_videos_path = 'static/data/all_videos.json'
            existing_all = load_existing_json(all_videos_path)
            merged_all = merge_videos(existing_all, new_videos)
            with open(all_videos_path, 'w', encoding='utf-8') as f:
                json.dump(merged_all, f, ensure_ascii=False, indent=2)
            logger.info(f"Updated all_videos.json with {len(merged_all)} total videos")
            
            # Update category-specific files
            categories = ['matches', 'interviews', 'classic', 'other']
            for category in categories:
                category_path = f'static/data/{category}_videos.json'
                existing_category = load_existing_json(category_path)
                new_category_videos = [v for v in new_videos if v['category'] == category]
                merged_category = merge_videos(existing_category, new_category_videos)
                
                with open(category_path, 'w', encoding='utf-8') as f:
                    json.dump(merged_category, f, ensure_ascii=False, indent=2)
                logger.info(f"Updated {category}_videos.json with {len(merged_category)} videos")
            
            # Update team stats
            teams_path = 'static/data/teams.json'
            existing_teams_data = load_existing_json(teams_path)
            existing_teams = existing_teams_data.get('teams', []) if existing_teams_data else []
            
            team_stats = {}
            # First, load existing team stats
            for team in existing_teams:
                team_stats[team['name']] = team
            
            # Update with new videos
            for video in new_videos:
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
                    
                    # Update latest video if newer
                    if not team_stats[team]['latest_video'] or \
                       video['upload_date'] > team_stats[team]['latest_video']['upload_date']:
                        team_stats[team]['latest_video'] = {
                            'id': video['id'],
                            'title': video['title'],
                            'thumbnail_url': video['thumbnail_url'],
                            'upload_date': video['upload_date']
                        }
            
            # Save updated team stats
            with open(teams_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'teams': list(team_stats.values()),
                    'variations': get_team_variations()
                }, f, ensure_ascii=False, indent=2)
            logger.info(f"Updated teams.json with {len(team_stats)} teams")
            
            logger.info("JSON conversion completed successfully")
            return True
            
    except Exception as e:
        logger.error(f"Error converting database to JSON: {e}")
        return False

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

if __name__ == "__main__":
    success = convert_db_to_json()
    if not success:
        exit(1) 