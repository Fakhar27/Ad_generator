"""
Whisper Audio Transcription Client
=================================

Sends audio files to the ngrok-exposed Whisper notebook service for transcription.
Just handles HTTP requests - all audio processing is done by the notebook service.

Based on the pattern used in video_manager.py and langchain_service.py.
"""

import os
import logging
import base64
import requests
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class WhisperProcessor:
    """
    Client for sending audio to ngrok-exposed Whisper notebook service
    """
    
    def __init__(self, ngrok_url: str = None):
        """Initialize Whisper client with ngrok service URL"""
        
        logger.info("Initializing Whisper client...")
        
        # Set the ngrok URL for the Whisper service
        self.ngrok_url = ngrok_url
        if not self.ngrok_url:
            # Try to get from environment or use default
            self.ngrok_url = os.getenv("WHISPER_NGROK_URL")
            if not self.ngrok_url:
                logger.warning("No ngrok URL provided. You'll need to set it manually.")
        
        # Endpoint for audio processing
        self.process_endpoint = f"{self.ngrok_url}/process_audio" if self.ngrok_url else None
        
        logger.info(f"Whisper service endpoint: {self.process_endpoint}")
        
        # Track temporary files for cleanup
        self.temp_files = []
    
    def transcribe_audio(self, audio_path: str) -> Dict:
        """
        Transcribe audio file by sending to ngrok Whisper service
        Similar to get_synchronized_subtitles in video_manager.py
        
        Args:
            audio_path (str): Path to audio file (MP3, WAV, etc.)
            
        Returns:
            dict: Whisper transcription data with word_level and line_level timing
        """
        
        logger.info(f"Starting transcription of: {audio_path}")
        
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        if not self.process_endpoint:
            raise ValueError("No Whisper service endpoint configured. Set ngrok_url during initialization.")
        
        try:
            # Step 1: Read audio file and encode to base64 (like video_manager does)
            logger.info("Reading and encoding audio file...")
            with open(audio_path, 'rb') as audio_file:
                audio_bytes = audio_file.read()
                audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            logger.info(f"Audio file size: {len(audio_bytes)/1024:.2f} KB")
            
            # Step 2: Send request to ngrok Whisper service
            logger.info(f"Sending request to Whisper service: {self.process_endpoint}")
            
            payload = {
                "audio_data": audio_base64
            }
            
            response = requests.post(
                self.process_endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=120  # 2 minute timeout for processing
            )
            
            if response.status_code != 200:
                error_text = response.text
                logger.error(f"Whisper service error: {error_text}")
                raise Exception(f"Whisper service returned status {response.status_code}: {error_text}")
            
            # Step 3: Parse response from notebook service
            service_result = response.json()
            
            logger.info("Received response from Whisper service")
            
            if not service_result:
                logger.error("Received empty transcription data")
                raise Exception("Empty transcription data received")
            
            if 'word_level' not in service_result:
                logger.error(f"Missing word_level in response. Keys: {service_result.keys()}")
                raise Exception("Invalid transcription data: missing word_level")
            
            # Step 4: Extract and format data
            word_level_data = service_result.get('word_level', [])
            line_level_data = service_result.get('line_level', [])
            
            # Calculate derived fields
            total_duration = max([word.get('end', 0) for word in word_level_data]) if word_level_data else 0
            full_text = ' '.join([word.get('word', '') for word in word_level_data])
            
            result = {
                'full_text': full_text,
                'word_level': word_level_data,
                'line_level': line_level_data,
                'total_duration': total_duration,
                'language': service_result.get('detected_language', 'unknown'),
                'language_probability': service_result.get('language_probability', 0.0),
                'segments_count': len(line_level_data),
                'words_count': len(word_level_data)
            }
            
            logger.info(f"Transcription summary:")
            logger.info(f"   Words: {len(word_level_data)}")
            logger.info(f"   Lines: {len(line_level_data)}")
            logger.info(f"   Duration: {total_duration:.1f}s")
            logger.info(f"   Language: {result['language']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise
    
    def set_ngrok_url(self, ngrok_url: str):
        """Update the ngrok URL for the Whisper service"""
        self.ngrok_url = ngrok_url
        self.process_endpoint = f"{ngrok_url}/process_audio"
        logger.info(f"Updated Whisper service endpoint: {self.process_endpoint}")
    
    def cleanup(self):
        """Cleanup method for consistency - no temp files to clean since notebook handles everything"""
        logger.debug("Whisper processor cleanup complete")


# Test function for standalone usage
if __name__ == "__main__":
    # Test with Angelo's audio file
    ngrok_url = input("Enter ngrok URL for Whisper service (e.g., https://abc123.ngrok.io): ").strip()
    processor = WhisperProcessor(ngrok_url=ngrok_url)
    
    audio_file = "demovideo1.mp3"
    if os.path.exists(audio_file):
        try:
            result = processor.transcribe_audio(audio_file)
            print(f"Transcription successful!")
            print(f"Text: {result['full_text'][:100]}...")
            print(f"Words: {result['words_count']}")
            print(f"Duration: {result['total_duration']:.1f}s")
            print(f"Language: {result['language']}")
        except Exception as e:
            print(f"Transcription failed: {e}")
        finally:
            processor.cleanup()
    else:
        print(f"Test file not found: {audio_file}")