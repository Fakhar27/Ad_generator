"""
Pexels Video Search Client
=========================

Searches Pexels for portrait corporate/business/motivational videos using extracted keywords.
Downloads videos and prepares them for concatenation.

Uses Pexels API native filters for orientation, duration, and quality
to get exactly what we need for TikTok-style vertical videos.
"""

import os
import logging
import requests
import tempfile
import random
from typing import List, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class PexelsClient:
    """
    Handle Pexels video search and download for corporate/business/motivational content
    """
    
    def __init__(self):
        """Initialize Pexels client with API key"""
        
        load_dotenv()
        
        self.api_key = os.getenv("PEXELS_API_KEY")
        if not self.api_key:
            raise ValueError("PEXELS_API_KEY not found in environment variables")
        
        # Pexels API endpoints
        self.base_url = "https://api.pexels.com/videos"
        self.headers = {"Authorization": self.api_key}
        
        # Track downloaded files for cleanup
        self.temp_video_files = []
        
        logger.info("Pexels client initialized")
    
    def search_portrait_videos(self, keywords: List[str], target_duration: float) -> List[Dict]:
        """
        Search Pexels for portrait corporate/business/motivational videos matching keywords
        
        Args:
            keywords (List[str]): Search keywords from transcript analysis
            target_duration (float): Target total duration (seconds)
            
        Returns:
            List[Dict]: Video segments ready for concatenation
        """
        
        logger.info(f"Searching Pexels for videos...")
        logger.info(f"   Keywords: {keywords}")
        logger.info(f"   Target duration: {target_duration:.1f} seconds")
        
        video_segments = []
        used_video_ids = set()  # Track used video IDs to avoid duplicates
        duration_per_video = max(6, target_duration / len(keywords))  # At least 6 seconds each
        
        for keyword in keywords:
            try:
                # DYNAMIC QUERY GENERATION: No hardcoded patterns
                strict_query = self._generate_dynamic_query(keyword)
                logger.info(f"Searching with dynamic query: '{strict_query}'")
                videos = self._search_videos(
                    query=strict_query,
                    orientation="portrait",
                    min_duration=int(duration_per_video),
                    max_duration=int(duration_per_video) + 5  # Some flexibility
                )
                
                if videos:
                    # Log all available videos for transparency
                    logger.info(f"Found {len(videos)} videos for keyword '{keyword}':")
                    for i, vid in enumerate(videos[:3]):  # Log first 3
                        logger.info(f"  Option {i+1}: ID={vid.get('id', 'N/A')}, Duration={vid.get('duration', 'N/A')}s")
                        # Sanitize username to avoid Unicode errors
                        username = vid.get('user', {}).get('name', 'Unknown')
                        try:
                            safe_username = username.encode('ascii', 'ignore').decode('ascii')
                            logger.info(f"    User: {safe_username}")
                        except:
                            logger.info(f"    User: [Non-ASCII username]")
                        logger.info(f"    URL: {vid.get('url', 'N/A')}")
                    
                    # Select the best video with business-focused filtering, avoiding duplicates
                    video = self._select_best_business_video(videos, keyword, used_video_ids)
                    
                    # Find the best quality portrait video file
                    video_file = self._select_best_video_file(video)
                    
                    if video_file:
                        segment = {
                            'keyword': keyword,
                            'duration': video['duration'],
                            'width': video_file['width'],
                            'height': video_file['height'],
                            'url': video_file['link'],
                            'quality': video_file['quality'],
                            'video_id': video['id']
                        }
                        
                        video_segments.append(segment)
                        used_video_ids.add(video['id'])  # Track this video ID as used
                        logger.info(f"Found video for '{keyword}': {video['duration']}s")
                    else:
                        logger.warning(f"No suitable video file found for '{keyword}'")
                else:
                    logger.warning(f"No videos found for keyword: '{keyword}'")
                    
            except Exception as e:
                logger.error(f"Error searching for '{keyword}': {e}")
                continue
        
        # If we don't have enough videos, search for generic corporate/business content
        if len(video_segments) < 3:
            logger.warning("Not enough specific videos found, adding generic corporate/business videos...")
            video_segments.extend(self._get_fallback_videos(target_duration))
        
        logger.info(f"Found {len(video_segments)} video segments")
        return video_segments[:5]  # Limit to 5 videos max
    
    def _generate_dynamic_query(self, keyword: str) -> str:
        """
        Generate dynamic search queries without hardcoded patterns
        Analyzes keyword context and builds relevant business queries
        """
        
        # Business context words - dynamically selected based on keyword
        business_contexts = [
            "corporate", "business", "professional", "office", 
            "executive", "team", "workplace", "meeting",
            "collaboration", "leadership", "strategy", "entrepreneur",
            "boardroom", "conference", "presentation", "handshake"
        ]
        
        # Industry modifiers that make searches more specific
        industry_modifiers = [
            "modern", "contemporary", "successful", "innovative",
            "diverse", "focused", "dynamic", "strategic"
        ]
        
        # Randomly select 2-3 business context words to avoid repetitive queries
        selected_contexts = random.sample(business_contexts, random.randint(2, 3))
        
        # Sometimes add an industry modifier for variety
        if random.random() > 0.5:  # 50% chance
            modifier = random.choice(industry_modifiers)
            query_parts = [keyword] + selected_contexts + [modifier]
        else:
            query_parts = [keyword] + selected_contexts
        
        # Shuffle the order for even more variety
        random.shuffle(query_parts)
        
        return " ".join(query_parts)
    
    def _search_videos(self, query: str, orientation: str = "portrait", 
                      min_duration: int = 5, max_duration: int = 15) -> List[Dict]:
        """
        Search Pexels videos with specific filters
        Uses native Pexels API filters - no custom logic needed!
        """
        
        url = f"{self.base_url}/search"
        
        # AGGRESSIVE VARIETY: Max API limits for huge video pool
        random_page = random.randint(1, 10)  # Pages 1-10 = 10x more variety
        
        params = {
            'query': query,
            'orientation': orientation,  # portrait for vertical videos
            'size': 'large',  # HD quality
            'min_duration': min_duration,
            'max_duration': max_duration,
            'per_page': 80,  # Maximum allowed by API = 5x more videos
            'page': random_page  # Random page for massive variety
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            return data.get('videos', [])
            
        except requests.RequestException as e:
            logger.error(f"Pexels API request failed: {e}")
            return []
    
    def _select_best_video_file(self, video: Dict) -> Optional[Dict]:
        """
        Select the best quality video file that's in portrait orientation
        """
        
        video_files = video.get('video_files', [])
        
        # Prefer portrait videos (height > width)
        portrait_files = [
            f for f in video_files 
            if f.get('height', 0) > f.get('width', 0)
        ]
        
        if not portrait_files:
            # If no portrait, take the highest resolution
            portrait_files = sorted(
                video_files,
                key=lambda f: (f.get('width', 0) * f.get('height', 0)),
                reverse=True
            )
        
        # Prefer HD quality
        hd_files = [f for f in portrait_files if f.get('quality') == 'hd']
        if hd_files:
            return hd_files[0]
        
        # Fallback to any available file
        return portrait_files[0] if portrait_files else None
    
    def _select_best_business_video(self, videos: List[Dict], keyword: str, used_video_ids: set = None) -> Dict:
        """Select the most business-appropriate video from search results"""
        
        # Business-related keywords to prioritize
        business_indicators = [
            'office', 'business', 'corporate', 'professional', 'meeting', 
            'conference', 'executive', 'team', 'workplace', 'boardroom',
            'presentation', 'handshake', 'suit', 'desk', 'computer',
            'collaboration', 'strategy', 'leadership', 'entrepreneur'
        ]
        
        # Keywords that indicate non-business content to avoid
        avoid_keywords = [
            'farm', 'agriculture', 'food', 'kitchen', 'cooking', 'recipe',
            'juice', 'drink', 'beverage', 'fruit', 'garden', 'plant',
            'sport', 'fitness', 'gym', 'workout', 'exercise', 'outdoor',
            'beach', 'vacation', 'travel', 'party', 'celebration'
        ]
        
        scored_videos = []
        if used_video_ids is None:
            used_video_ids = set()
        
        # Filter out already used videos first
        available_videos = [v for v in videos if v.get('id') not in used_video_ids]
        
        if not available_videos:
            logger.warning(f"All videos for '{keyword}' were already used, using original list")
            available_videos = videos  # Fallback to original list if all were used
        
        for video in available_videos:
            score = 0
            video_url = video.get('url', '')
            user_name = video.get('user', {}).get('name', '').lower()
            
            # Get video tags/keywords if available (this might not be in Pexels API response)
            # We'll work with the URL and user info
            video_text = f"{video_url} {user_name}".lower()
            
            # Positive scoring for business indicators
            for indicator in business_indicators:
                if indicator in video_text:
                    score += 2
                    logger.debug(f"Video {video['id']}: +2 points for '{indicator}'")
            
            # Negative scoring for non-business content
            for avoid in avoid_keywords:
                if avoid in video_text:
                    score -= 3
                    logger.debug(f"Video {video['id']}: -3 points for '{avoid}'")
            
            # Prefer videos with higher duration (within reason)
            duration = video.get('duration', 0)
            if 8 <= duration <= 15:  # Good duration range
                score += 1
            
            scored_videos.append((score, video))
            logger.debug(f"Video {video['id']} score: {score}")
        
        # Sort by score (highest first) and add randomization among top videos
        if scored_videos:
            scored_videos.sort(key=lambda x: x[0], reverse=True)
            
            # QUICK FIX: Pick randomly from top 3 scored videos instead of always #1
            top_videos = scored_videos[:3]
            best_score, best_video = random.choice(top_videos)
            logger.info(f"Selected video {best_video['id']} with score {best_score} for keyword '{keyword}'")
            return best_video
        
        # Fallback to first video if no scoring worked
        logger.warning(f"No scored videos found, using first video for keyword '{keyword}'")
        return videos[0]
    
    def _get_fallback_videos(self, target_duration: float) -> List[Dict]:
        """Get generic corporate/business/motivational videos when keyword search fails"""
        
        # DYNAMIC FALLBACK: Generate varied queries instead of hardcoded list
        fallback_base_terms = ["business", "corporate", "professional", "office", "team"]
        fallback_videos = []
        
        # Generate 5 different dynamic queries for variety
        for i in range(5):
            base_term = random.choice(fallback_base_terms)
            query = self._generate_dynamic_query(base_term)
            try:
                logger.info(f"Fallback search with dynamic query: '{query}'")
                videos = self._search_videos(query, min_duration=8, max_duration=12)
                if videos:
                    # Random selection from available videos
                    video = random.choice(videos)
                    video_file = self._select_best_video_file(video)
                    
                    if video_file:
                        segment = {
                            'keyword': f'fallback_{i+1}',
                            'duration': video['duration'],
                            'width': video_file['width'],
                            'height': video_file['height'],
                            'url': video_file['link'],
                            'quality': video_file['quality'],
                            'video_id': video['id']
                        }
                        fallback_videos.append(segment)
                        
                        if len(fallback_videos) >= 2:  # Limit fallbacks
                            break
                            
            except Exception as e:
                logger.warning(f"Dynamic fallback search failed for '{query}': {e}")
                continue
        
        return fallback_videos
    
    def download_video_segment(self, segment: Dict, output_dir: str = None) -> str:
        """
        Download a video segment to local file
        
        Args:
            segment (Dict): Video segment info from search
            output_dir (str): Directory to save video (optional)
            
        Returns:
            str: Path to downloaded video file
        """
        
        if output_dir is None:
            output_dir = tempfile.gettempdir()
        
        # Create filename
        filename = f"pexels_{segment['video_id']}_{segment['keyword']}.mp4"
        output_path = os.path.join(output_dir, filename)
        
        logger.info(f"Downloading video: {segment['keyword']} ({segment['duration']}s)")
        
        try:
            # Download video
            response = requests.get(segment['url'], stream=True)
            response.raise_for_status()
            
            # Save to file
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Track for cleanup
            self.temp_video_files.append(output_path)
            
            # Verify file was created
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"Downloaded: {output_path} ({os.path.getsize(output_path) // 1024} KB)")
                return output_path
            else:
                logger.error(f"Download failed or file is empty: {output_path}")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading video: {e}")
            return None
    
    def download_all_segments(self, video_segments: List[Dict]) -> List[str]:
        """Download all video segments and return list of file paths"""
        
        logger.info(f"Downloading {len(video_segments)} video segments...")
        
        downloaded_files = []
        
        for segment in video_segments:
            try:
                file_path = self.download_video_segment(segment)
                if file_path:
                    downloaded_files.append(file_path)
                else:
                    logger.warning(f"Failed to download video for keyword: {segment['keyword']}")
                    
            except Exception as e:
                logger.error(f"Error downloading segment {segment['keyword']}: {e}")
                continue
        
        logger.info(f"Successfully downloaded {len(downloaded_files)} videos")
        return downloaded_files
    
    def cleanup(self):
        """Remove temporary video files"""
        
        for video_file in self.temp_video_files:
            try:
                if os.path.exists(video_file):
                    os.remove(video_file)
                    logger.debug(f"Removed temp video: {video_file}")
            except Exception as e:
                logger.warning(f"Failed to remove temp video {video_file}: {e}")
        
        self.temp_video_files.clear()


# Test function for standalone usage
if __name__ == "__main__":
    # Test Pexels search
    client = PexelsClient()
    
    # Test search
    keywords = ["business", "corporate", "professional"]
    segments = client.search_portrait_videos(keywords, target_duration=30)
    
    print(f"Found {len(segments)} video segments:")
    for segment in segments:
        print(f"  - {segment['keyword']}: {segment['duration']}s ({segment['width']}x{segment['height']})")
    
    # Test download (uncomment to actually download)
    # if segments:
    #     file_path = client.download_video_segment(segments[0])
    #     print(f"Downloaded: {file_path}")