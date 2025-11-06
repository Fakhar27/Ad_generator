"""
Angelo's Reel Generation POC - Main Orchestrator
==================================================

This is the main file that coordinates the entire reel generation process:
1. Transcribe Italian audio with Whisper
2. Extract keywords using Cohere LLM 
3. Search Pexels for portrait fitness videos
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

# Import our custom modules
from whisper_processor import WhisperProcessor
from keyword_extractor import KeywordExtractor  
from pexels_client import PexelsClient
from video_assembler import VideoAssembler

# Set up logging
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
        
        # Load environment variables
        load_dotenv()
        
        # Validate required environment variables
        self._validate_env()
        
        # Initialize all processors
        logger.info("Initializing reel generation components...")
        
        # Get ngrok URL for Whisper service (should be set manually or through env)
        whisper_ngrok_url = os.getenv("WHISPER_NGROK_URL")
        if not whisper_ngrok_url:
            logger.warning("⚠️ WHISPER_NGROK_URL not set. You'll need to set it manually.")
        
        self.whisper_processor = WhisperProcessor(ngrok_url=whisper_ngrok_url)
        self.keyword_extractor = KeywordExtractor()
        self.pexels_client = PexelsClient()
        self.video_assembler = VideoAssembler()
        
        logger.info("✅ All components initialized successfully")
    
    def _validate_env(self):
        """Ensure all required environment variables are set"""
        required_vars = ['CO_API_KEY', 'PEXELS_API_KEY']
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"❌ Missing environment variables: {missing_vars}")
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
        
        logger.info(f"🎬 Starting reel generation for: {italian_audio_path}")
        
        try:
            # Step 1: Transcribe Italian audio using Whisper
            logger.info("📝 Step 1: Transcribing Italian audio...")
            transcript_data = self.whisper_processor.transcribe_audio(italian_audio_path)
            logger.info(f"✅ Transcription complete: {len(transcript_data['word_level'])} words detected")
            
            # Step 2: Extract keywords using Cohere LLM
            logger.info("🔍 Step 2: Extracting keywords for video search...")
            keywords = self.keyword_extractor.extract_keywords(transcript_data['full_text'])
            logger.info(f"✅ Keywords extracted: {keywords}")
            
            # Step 3: Search Pexels for portrait fitness videos
            logger.info("🎥 Step 3: Searching for relevant videos...")
            video_segments = self.pexels_client.search_portrait_videos(
                keywords=keywords,
                target_duration=transcript_data['total_duration']
            )
            logger.info(f"✅ Found {len(video_segments)} video segments")
            
            # Step 3.5: Download video files (once!)
            logger.info("📥 Step 3.5: Downloading video files...")
            video_files = self.pexels_client.download_all_segments(video_segments)
            logger.info(f"✅ Downloaded {len(video_files)} video files")
            
            # Step 4: Assemble final video with all components
            logger.info("⚙️ Step 4: Assembling final video...")
            final_video_path = self.video_assembler.create_final_reel(
                video_files=video_files,  # Pass downloaded files, not metadata
                original_audio_path=italian_audio_path,
                transcript_data=transcript_data,
                output_filename=output_filename
            )
            logger.info(f"✅ Final video created: {final_video_path}")
            
            # Step 5: Cleanup temporary files
            logger.info("🧹 Step 5: Cleaning up temporary files...")
            self._cleanup_temp_files()
            
            logger.info(f"🎉 REEL GENERATION COMPLETE! Output: {final_video_path}")
            return final_video_path
            
        except Exception as e:
            logger.error(f"❌ Error during reel generation: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            raise
    
    def _cleanup_temp_files(self):
        """Clean up any temporary files created during processing"""
        try:
            # Clean up temporary video downloads
            self.pexels_client.cleanup()
            # Clean up temporary audio conversions
            self.whisper_processor.cleanup()
            logger.info("✅ Temporary files cleaned up")
        except Exception as e:
            logger.warning(f"⚠️ Error during cleanup: {str(e)}")


def main():
    """Main function to run the reel generator with Angelo's audio"""
    
    print("🚀 Angelo's Reel Generation POC")
    print("=" * 50)
    
    # Initialize the generator
    generator = ReelGenerator()
    
    # Path to Angelo's audio file
    audio_file = "demovideo1.mp3"
    
    # Check if audio file exists
    if not os.path.exists(audio_file):
        print(f"❌ Audio file not found: {audio_file}")
        print("Please ensure demovideo1.mp3 is in the current directory")
        sys.exit(1)
    
    # Generate the reel
    try:
        output_video = generator.generate_reel(
            italian_audio_path=audio_file,
            output_filename="angelo_fitness_reel_poc.mp4"
        )
        
        print(f"🎉 SUCCESS! Generated reel: {output_video}")
        print(f"📁 File size: {os.path.getsize(output_video) / 1024 / 1024:.1f} MB")
        print("\n✨ Ready to show Angelo!")
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        print("Check the log file for detailed error information")
        sys.exit(1)


if __name__ == "__main__":
    main()