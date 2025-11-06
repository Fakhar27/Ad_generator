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
        duration_per_video = max(6, target_duration / len(keywords))  # At least 6 seconds each
        
        for keyword in keywords:
            try:
                # Search for videos with this keyword
                videos = self._search_videos(
                    query=f"{keyword}",
                    orientation="portrait",
                    min_duration=int(duration_per_video),
                    max_duration=int(duration_per_video) + 5  # Some flexibility
                )
                
                if videos:
                    # Take the first suitable video
                    video = videos[0]
                    
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
    
    def _search_videos(self, query: str, orientation: str = "portrait", 
                      min_duration: int = 5, max_duration: int = 15) -> List[Dict]:
        """
        Search Pexels videos with specific filters
        Uses native Pexels API filters - no custom logic needed!
        """
        
        url = f"{self.base_url}/search"
        params = {
            'query': query,
            'orientation': orientation,  # portrait for vertical videos
            'size': 'large',  # HD quality
            'min_duration': min_duration,
            'max_duration': max_duration,
            'per_page': 10  # Get multiple options
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
    
    def _get_fallback_videos(self, target_duration: float) -> List[Dict]:
        """Get generic corporate/business/motivational videos when keyword search fails"""
        
        fallback_queries = ["business meeting", "corporate office", "professional team", "digital marketing", "entrepreneur working"]
        fallback_videos = []
        
        for query in fallback_queries:
            try:
                videos = self._search_videos(query, min_duration=8, max_duration=12)
                if videos:
                    video = videos[0]
                    video_file = self._select_best_video_file(video)
                    
                    if video_file:
                        segment = {
                            'keyword': 'fallback',
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
                logger.warning(f"Fallback search failed for '{query}': {e}")
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