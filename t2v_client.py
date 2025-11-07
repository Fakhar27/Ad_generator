"""
Text-to-Video Client for Angelo's Reel Generator
===============================================

Client for sending text prompts to the ngrok-exposed T2V service (CogVideoX).
Alternative to Pexels API for generating custom business videos.

⚠️ WARNING: T2V generation is VERY SLOW on free T4 GPUs (8 minutes per 5-second video)
"""

import os
import logging
import base64
import requests
from pathlib import Path
from typing import List, Dict, Optional
import time

logger = logging.getLogger(__name__)

class T2VClient:
    """
    Client for generating videos from text prompts using CogVideoX via ngrok
    """
    
    def __init__(self, ngrok_url: str = None):
        """Initialize T2V client with ngrok service URL"""
        
        logger.info("Initializing T2V client...")
        
        self.ngrok_url = ngrok_url
        if not self.ngrok_url:
            self.ngrok_url = os.getenv("T2V_NGROK_URL")
            if not self.ngrok_url:
                logger.warning("No T2V ngrok URL provided. T2V features will be unavailable.")
        
        self.generate_endpoint = f"{self.ngrok_url}/generate_video" if self.ngrok_url else None
        self.status_endpoint = f"{self.ngrok_url}/status" if self.ngrok_url else None
        
        logger.info(f"T2V service endpoint: {self.generate_endpoint}")
        
        self.temp_files = []
        
        if self.ngrok_url:
            self._check_service_status()
    
    def _check_service_status(self):
        """Check if T2V service is ready"""
        try:
            response = requests.get(self.status_endpoint, timeout=10)
            if response.status_code == 200:
                status_data = response.json()
                logger.info(f"T2V service status: {status_data['status']}")
                logger.info(f"GPU available: {status_data['gpu_available']}")
                if status_data.get('gpu_name'):
                    logger.info(f"GPU: {status_data['gpu_name']}")
            else:
                logger.warning(f"T2V service status check failed: {response.status_code}")
        except Exception as e:
            logger.warning(f"Could not check T2V service status: {e}")
    
    def generate_videos_from_prompts(self, prompts: List[Dict], target_duration: float) -> List[str]:
        """
        Generate business videos from prompt list using T2V
        
        Args:
            prompts (List[Dict]): List of prompt dictionaries with structure:
                [{"prompt": "...", "purpose": "...", "duration": 5}, ...]
            target_duration (float): Target total duration (seconds)
            
        Returns:
            List[str]: Paths to generated video files
        """
        
        if not self.generate_endpoint:
            logger.error("No T2V service URL configured")
            return []
        
        logger.info(f"Generating {len(prompts)} videos via T2V service")
        logger.warning(f"⚠️ ESTIMATED TIME: {len(prompts) * 8} minutes ({len(prompts)} videos × 8 min each)")
        
        video_files = []
        total_duration = 0
        
        for i, prompt_data in enumerate(prompts):
            if total_duration >= target_duration:
                logger.info(f"✅ Target duration {target_duration:.1f}s reached with {total_duration:.1f}s")
                break
                
            try:
                prompt = prompt_data['prompt']
                purpose = prompt_data.get('purpose', f'video_{i+1}')
                
                logger.info(f"Generating video {i+1}/{len(prompts)}: {purpose}")
                logger.info(f"Prompt: '{prompt}'")
                logger.info(f"⏱️ Expected time: 8 minutes for 5-second clip...")
                
                video_path = self._generate_single_video(prompt, i, purpose)
                
                if video_path:
                    video_files.append(video_path)
                    self.temp_files.append(video_path)
                    
                    estimated_duration = 5.0
                    total_duration += estimated_duration
                    
                    logger.info(f"✅ Video {i+1} generated successfully")
                    logger.info(f"📊 Progress: {total_duration:.1f}s/{target_duration:.1f}s ({len(video_files)} videos)")
                else:
                    logger.error(f"❌ Video {i+1} generation failed")
                    
            except Exception as e:
                logger.error(f"Error generating video {i+1}: {e}")
                continue
        
        logger.info(f"🎬 T2V Generation Complete: {len(video_files)}/{len(prompts)} videos ({total_duration:.1f}s total)")
        return video_files
    
    def _generate_single_video(self, prompt: str, index: int, purpose: str) -> Optional[str]:
        """Generate a single video from a prompt"""
        
        start_time = time.time()
        
        payload = {
            "prompt": prompt,
            "negative_prompt": "blurry, low quality, distorted, text, watermark, amateur, unprofessional",
            "num_inference_steps": 20,  # Balanced speed vs quality  
            "num_frames": 25,  # ~5 seconds at 8fps (CogVideoX standard)
            "guidance_scale": 6.5,
            "seed": 42 + index  # Different seed for variety
        }
        
        logger.info(f"⚙️ Sending T2V request for: {purpose}")
        
        try:
            response = requests.post(
                self.generate_endpoint,
                json=payload,
                timeout=900  # 15 minute timeout (8 mins expected + buffer)
            )
            
            if response.status_code != 200:
                error_text = response.text
                logger.error(f"T2V service error: {error_text}")
                return None
            
            result = response.json()
            
            if 'error' in result:
                logger.error(f"T2V generation error: {result['error']}")
                return None
            
            video_base64 = result['video_data']
            video_bytes = base64.b64decode(video_base64)
            
            output_path = f"temp_t2v_{index}_{purpose}_{int(time.time())}.mp4"
            with open(output_path, 'wb') as f:
                f.write(video_bytes)
            
            generation_time = time.time() - start_time
            file_size = len(video_bytes)
            
            logger.info(f"✅ Generated in {generation_time:.1f}s")
            logger.info(f"   File: {output_path} ({file_size/1024:.1f} KB)")
            
            if not self._validate_video_quality(output_path):
                logger.warning(f"⚠️ Video quality check failed for {purpose}")
                # Don't return None, use it anyway for POC
            
            return output_path
            
        except requests.exceptions.Timeout:
            logger.error(f"❌ T2V request timed out (15 minutes) for: {purpose}")
            logger.error("   GPU may be overwhelmed or generation is very slow")
            return None
        except Exception as e:
            logger.error(f"❌ T2V request failed for {purpose}: {e}")
            return None
    
    def _validate_video_quality(self, video_path: str) -> bool:
        """Basic validation for common T2V failures"""
        try:
            if not os.path.exists(video_path):
                return False
            
            file_size = os.path.getsize(video_path)
            if file_size < 10000:  # Less than 10KB is probably broken
                logger.warning(f"Video file very small: {file_size} bytes")
                return False
            
            # TODO: Could add more sophisticated checks:
            
            return True
            
        except Exception as e:
            logger.warning(f"Video validation error: {e}")
            return False
    
    def set_ngrok_url(self, ngrok_url: str):
        """Update the ngrok URL for the T2V service"""
        self.ngrok_url = ngrok_url
        self.generate_endpoint = f"{ngrok_url}/generate_video"
        self.status_endpoint = f"{ngrok_url}/status"
        logger.info(f"Updated T2V service endpoint: {self.generate_endpoint}")
        self._check_service_status()
    
    def cleanup(self):
        """Cleanup temporary video files"""
        cleaned = 0
        logger.info(f"Starting cleanup of {len(self.temp_files)} T2V temp files...")
        
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    cleaned += 1
                    logger.info(f"Removed temp T2V video: {temp_file}")
                else:
                    logger.warning(f"Temp file already missing: {temp_file}")
            except Exception as e:
                logger.warning(f"Could not remove temp file {temp_file}: {e}")
        
        if cleaned > 0:
            logger.info(f"Successfully cleaned up {cleaned} temporary T2V video files")
        else:
            logger.info("No T2V temp files to clean up")
        
        self.temp_files.clear()


if __name__ == "__main__":
    ngrok_url = input("Enter ngrok URL for T2V service (e.g., https://abc123.ngrok.io): ").strip()
    
    if ngrok_url:
        client = T2VClient(ngrok_url=ngrok_url)
        
        test_prompts = [
            {"prompt": "Professional handshake between businesspeople in modern office", "purpose": "introduction", "duration": 5},
            {"prompt": "Executive presenting charts to team in bright conference room", "purpose": "presentation", "duration": 5},
            {"prompt": "Business team collaborating around glass table", "purpose": "teamwork", "duration": 5}
        ]
        
        print(f"\n🎬 Testing T2V generation with {len(test_prompts)} prompts")
        print(f"⚠️ This will take approximately {len(test_prompts) * 8} minutes on T4 GPU!")
        
        confirm = input("Continue? (y/N): ").strip().lower()
        if confirm == 'y':
            try:
                video_files = client.generate_videos_from_prompts(test_prompts, 15.0)
                print(f"\n✅ Generated {len(video_files)} videos:")
                for video in video_files:
                    print(f"  - {video}")
            except Exception as e:
                print(f"❌ Test failed: {e}")
            finally:
                client.cleanup()
        else:
            print("Test cancelled")
    else:
        print("❌ No ngrok URL provided")