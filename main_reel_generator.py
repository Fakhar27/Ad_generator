"""
Angelo's Reel Generation POC - Main Orchestrator
==================================================

This is the main file that coordinates the entire reel generation process:
1. Transcribe Italian audio with Whisper
2. Extract keywords using Cohere LLM 
3. Search Pexels for portrait corporate/business videos
4. Concatenate videos and add audio layers
5. Burn Italian subtitles
6. Export final vertical reel

Usage:
    python main_reel_generator.py

Author: Generated for Angelo's TikTok automation project
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

from whisper_processor import WhisperProcessor
from keyword_extractor import KeywordExtractor  
from pexels_client import PexelsClient
from video_assembler import VideoAssembler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("reel_generation.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ReelGenerator:
    """
    Main class that orchestrates the entire reel generation pipeline
    """
    
    def __init__(self):
        """Initialize the reel generator with all required components"""
        
        load_dotenv()
        
        self._validate_env()
        
        logger.info("Initializing reel generation components...")
        
        whisper_ngrok_url = os.getenv("WHISPER_NGROK_URL")
        if not whisper_ngrok_url:
            logger.warning("WHISPER_NGROK_URL not set. You'll need to set it manually.")
        
        self.whisper_processor = WhisperProcessor(ngrok_url=whisper_ngrok_url)
        self.keyword_extractor = KeywordExtractor()
        self.pexels_client = PexelsClient()
        self.video_assembler = VideoAssembler()
        
        logger.info("All components initialized successfully")
    
    def _validate_env(self):
        """Ensure all required environment variables are set"""
        required_vars = ['CO_API_KEY', 'PEXELS_API_KEY']
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"Missing environment variables: {missing_vars}")
            logger.error("Please check your .env file")
            sys.exit(1)
    
    def generate_reel(self, italian_audio_path: str, output_filename: str = None) -> str:
        """
        Main method to generate a complete reel from Italian audio
        
        Args:
            italian_audio_path (str): Path to Angelo's Italian audio file
            output_filename (str): Optional custom output filename
            
        Returns:
            str: Path to the generated video file
        """
        
        logger.info(f"Starting reel generation for: {italian_audio_path}")
        
        try:
            logger.info("Step 1: Transcribing Italian audio...")
            transcript_data = self.whisper_processor.transcribe_audio(italian_audio_path)
            logger.info(f"Transcription complete: {len(transcript_data['word_level'])} words detected")
            
            logger.info("Step 2: Extracting keywords for video search...")
            keywords = self.keyword_extractor.extract_keywords(transcript_data['full_text'])
            logger.info(f"Keywords extracted: {keywords}")
            
            logger.info("Step 3: Searching for relevant videos...")
            video_segments = self.pexels_client.search_portrait_videos(
                keywords=keywords,
                target_duration=transcript_data['total_duration']
            )
            logger.info(f"Found {len(video_segments)} video segments")
            
            logger.info("Step 3.5: Downloading video files...")
            video_files = self.pexels_client.download_all_segments(video_segments)
            logger.info(f"Downloaded {len(video_files)} video files")
            
            logger.info("Step 4: Assembling final video...")
            final_video_path = self.video_assembler.create_final_reel(
                video_files=video_files, 
                original_audio_path=italian_audio_path,
                transcript_data=transcript_data,
                output_filename=output_filename
            )
            logger.info(f"Final video created: {final_video_path}")
            
            logger.info("Step 5: Cleaning up temporary files...")
            self._cleanup_temp_files()
            
            logger.info(f"REEL GENERATION COMPLETE! Output: {final_video_path}")
            return final_video_path
            
        except Exception as e:
            logger.error(f"Error during reel generation: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            raise
    
    def _cleanup_temp_files(self):
        """Clean up any temporary files created during processing"""
        try:
            self.pexels_client.cleanup()
            self.whisper_processor.cleanup()
            logger.info("Temporary files cleaned up")
        except Exception as e:
            logger.warning(f"Error during cleanup: {str(e)}")


def main():
    """Main function to run the reel generator with Angelo's audio"""
    
    print("Angelo's Reel Generation POC")
    print("=" * 50)
    
    generator = ReelGenerator()
    
    audio_file = "demovideo1.mp3"
    
    # Check if audio file exists
    if not os.path.exists(audio_file):
        print(f"Audio file not found: {audio_file}")
        print("Please ensure demovideo1.mp3 is in the current directory")
        sys.exit(1)
    
    try:
        output_video = generator.generate_reel(
            italian_audio_path=audio_file,
            output_filename="angelo_business_reel_poc.mp4"
        )
        
        print(f"SUCCESS! Generated reel: {output_video}")
        print(f"File size: {os.path.getsize(output_video) / 1024 / 1024:.1f} MB")
        print("\nReady to show Angelo!")
        
    except Exception as e:
        print(f"FAILED: {str(e)}")
        print("Check the log file for detailed error information")
        sys.exit(1)


if __name__ == "__main__":
    main()