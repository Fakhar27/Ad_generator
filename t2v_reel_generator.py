"""
Angelo's T2V Reel Generation Pipeline - Open Source Approach
==========================================================

This is the T2V alternative to main_reel_generator.py that uses:
1. Transcribe Italian audio with Whisper (same)
2. Extract keywords using Cohere LLM (same)
3. Generate video prompts using Cohere LLM (new)
4. Generate videos using CogVideoX T2V (new)
5. Burn Italian subtitles and assemble (same)

⚠️ WARNING: This approach takes 60-90 minutes per reel vs 3 minutes with Pexels
Only use for unique content generation or when stock footage is insufficient.

Usage:
    python t2v_reel_generator.py

Author: Generated for Angelo's TikTok automation project
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
import time
from typing import Dict

# Import our custom modules
from whisper_processor import WhisperProcessor
from keyword_extractor import KeywordExtractor  
from video_prompt_generator import VideoPromptGenerator
from t2v_client import T2VClient
from video_assembler import VideoAssembler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("t2v_reel_generation.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class T2VReelGenerator:
    """
    Main class that orchestrates the T2V reel generation pipeline
    """
    
    def __init__(self):
        """Initialize the T2V reel generator with all required components"""
        
        # Load environment variables
        load_dotenv()
        
        # Validate required environment variables
        self._validate_env()
        
        # Initialize all processors
        logger.info("Initializing T2V reel generation components...")
        
        # Get ngrok URLs for services
        whisper_ngrok_url = os.getenv("WHISPER_NGROK_URL")
        t2v_ngrok_url = os.getenv("T2V_NGROK_URL")
        
        if not whisper_ngrok_url:
            logger.warning("WHISPER_NGROK_URL not set. You'll need to set it manually.")
        
        if not t2v_ngrok_url:
            logger.error("T2V_NGROK_URL not set. T2V generation will fail!")
            logger.error("Please start the T2V service notebook and set T2V_NGROK_URL")
        
        # Initialize components
        self.whisper_processor = WhisperProcessor(ngrok_url=whisper_ngrok_url)
        self.keyword_extractor = KeywordExtractor()
        self.video_prompt_generator = VideoPromptGenerator()
        self.t2v_client = T2VClient(ngrok_url=t2v_ngrok_url)
        self.video_assembler = VideoAssembler()
        
        logger.info("All T2V components initialized successfully")
    
    def _validate_env(self):
        """Ensure all required environment variables are set"""
        required_vars = ['CO_API_KEY', 'T2V_NGROK_URL']
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"Missing environment variables: {missing_vars}")
            logger.error("Please check your .env file")
            if 'T2V_NGROK_URL' in missing_vars:
                logger.error("T2V_NGROK_URL is required - start the T2V service notebook first!")
            sys.exit(1)
    
    def generate_reel(self, italian_audio_path: str, output_filename: str = None) -> str:
        """
        Main method to generate a complete reel from Italian audio using T2V
        
        Args:
            italian_audio_path (str): Path to Angelo's Italian audio file
            output_filename (str): Optional custom output filename
            
        Returns:
            str: Path to the generated video file
        """
        
        start_time = time.time()
        logger.info(f"Starting T2V reel generation for: {italian_audio_path}")
        logger.warning("T2V GENERATION IS VERY SLOW - Expected time: 60-90 minutes")
        
        try:
            # Step 1: Transcribe Italian audio using Whisper (same as main pipeline)
            logger.info("Step 1: Transcribing Italian audio...")
            transcript_data = self.whisper_processor.transcribe_audio(italian_audio_path)
            logger.info(f"Transcription complete: {len(transcript_data['word_level'])} words detected")
            
            # Step 2: Extract keywords using Cohere LLM (same as main pipeline)
            logger.info("Step 2: Extracting keywords for context...")
            keywords = self.keyword_extractor.extract_keywords(transcript_data['full_text'])
            logger.info(f"Keywords extracted: {keywords}")
            
            # Step 3: Generate video prompts using Cohere LLM (NEW!)
            logger.info("Step 3: Generating video prompt sequence...")
            video_prompts = self.video_prompt_generator.generate_video_sequence(
                italian_transcript=transcript_data['full_text'],
                target_duration=transcript_data['total_duration']
            )
            logger.info(f"Generated {len(video_prompts)} video prompts for {transcript_data['total_duration']:.1f}s")
            
            # Step 4: Generate videos using T2V service (NEW!)
            estimated_time = len(video_prompts) * 8  # 8 minutes per video
            logger.info(f"Step 4: Generating videos via T2V service...")
            logger.warning(f"ESTIMATED TIME: {estimated_time} minutes ({len(video_prompts)} videos × 8 min each)")
            logger.warning(f"Good time for a meal break! This will take a while...")
            
            video_generation_start = time.time()
            video_files = self.t2v_client.generate_videos_from_prompts(
                prompts=video_prompts,
                target_duration=transcript_data['total_duration']
            )
            video_generation_time = time.time() - video_generation_start
            
            if not video_files:
                raise Exception("No videos were successfully generated by T2V service")
            
            logger.info(f"T2V generation complete: {len(video_files)} videos in {video_generation_time/60:.1f} minutes")
            
            # Step 5: Assemble final video with all components (same as main pipeline)
            logger.info("Step 5: Assembling final video...")
            final_video_path = self.video_assembler.create_final_reel(
                video_files=video_files,  # Pass T2V generated files
                original_audio_path=italian_audio_path,
                transcript_data=transcript_data,
                output_filename=output_filename or "angelo_t2v_reel.mp4"
            )
            logger.info(f"Final video created: {final_video_path}")
            
            # Step 6: Cleanup temporary files (AFTER video assembly is complete!)
            logger.info("Step 6: Cleaning up temporary files...")
            self._cleanup_temp_files()
            
            total_time = time.time() - start_time
            logger.info(f"T2V REEL GENERATION COMPLETE! Output: {final_video_path}")
            logger.info(f"Total processing time: {total_time/60:.1f} minutes")
            logger.info(f"   - Transcription + Prompts: {(video_generation_start - start_time)/60:.1f} min")
            logger.info(f"   - T2V Generation: {video_generation_time/60:.1f} min")
            logger.info(f"   - Video Assembly: {(total_time - video_generation_time)/60:.1f} min")
            
            return final_video_path
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"Error during T2V reel generation after {total_time/60:.1f} minutes: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            
            # Try to cleanup even on failure
            try:
                self._cleanup_temp_files()
            except:
                pass
            
            raise
    
    def _cleanup_temp_files(self):
        """Clean up any temporary files created during processing"""
        try:
            # Clean up temporary T2V videos
            self.t2v_client.cleanup()
            # Clean up temporary audio conversions  
            self.whisper_processor.cleanup()
            logger.info("Temporary files cleaned up")
        except Exception as e:
            logger.warning(f"Error during cleanup: {str(e)}")
    
    def get_generation_estimate(self, audio_duration: float) -> Dict:
        """
        Estimate T2V generation time and costs
        
        Args:
            audio_duration (float): Duration of audio in seconds
            
        Returns:
            Dict: Estimation data
        """
        
        videos_needed = max(6, int(audio_duration / 5))
        t2v_time = videos_needed * 8  # 8 minutes per video
        total_time = t2v_time + 15  # +15 min for transcription and assembly
        
        return {
            "audio_duration": audio_duration,
            "videos_needed": videos_needed,
            "t2v_generation_minutes": t2v_time,
            "total_estimated_minutes": total_time,
            "gpu_cost_estimate_usd": total_time * 0.05,  # Rough T4 cost estimate
            "recommendation": "Use Pexels for speed, T2V for unique content only"
        }


def main():
    """Main function to run the T2V reel generator with Angelo's audio"""
    
    print("🎬 Angelo's T2V Reel Generation (Open Source Approach)")
    print("=" * 60)
    print("⚠️  WARNING: This is the SLOW T2V approach!")
    print("⚠️  Expected time: 60-90 minutes vs 3 minutes with Pexels")
    print("=" * 60)
    
    # Initialize the generator
    try:
        generator = T2VReelGenerator()
    except Exception as e:
        print(f"❌ Failed to initialize T2V generator: {e}")
        print("💡 Make sure T2V service notebook is running and T2V_NGROK_URL is set")
        sys.exit(1)
    
    # Path to Angelo's audio file
    audio_file = "demovideo1.mp3"
    
    # Check if audio file exists
    if not os.path.exists(audio_file):
        print(f"❌ Audio file not found: {audio_file}")
        print("Please ensure demovideo1.mp3 is in the current directory")
        sys.exit(1)
    
    # Show generation estimate
    try:
        with open(audio_file, 'rb') as f:
            # Rough duration estimate (not precise, but good enough for estimate)
            file_size = len(f.read())
            estimated_duration = file_size / 15000  # Rough estimate
        
        estimate = generator.get_generation_estimate(estimated_duration)
        
        print(f"📊 T2V Generation Estimate:")
        print(f"   Audio duration: ~{estimate['audio_duration']:.1f} seconds")
        print(f"   Videos needed: {estimate['videos_needed']}")
        print(f"   T2V generation time: {estimate['t2v_generation_minutes']} minutes")
        print(f"   Total estimated time: {estimate['total_estimated_minutes']} minutes")
        print(f"   Recommendation: {estimate['recommendation']}")
        print()
        
        # Ask for confirmation
        confirm = input("Continue with T2V generation? (y/N): ").strip().lower()
        if confirm != 'y':
            print("T2V generation cancelled. Use main_reel_generator.py for faster Pexels approach.")
            sys.exit(0)
            
    except Exception as e:
        print(f"⚠️ Could not estimate duration: {e}")
        
        confirm = input("Continue anyway with T2V generation? (y/N): ").strip().lower()
        if confirm != 'y':
            print("T2V generation cancelled.")
            sys.exit(0)
    
    # Generate the reel
    try:
        print(f"🚀 Starting T2V reel generation...")
        print(f"💡 This is a good time to:")
        print(f"   - Get some coffee ☕")
        print(f"   - Have a meal 🍕") 
        print(f"   - Take a walk 🚶")
        print(f"   - Do other work 💼")
        print()
        
        output_video = generator.generate_reel(
            italian_audio_path=audio_file,
            output_filename="angelo_t2v_reel_poc.mp4"
        )
        
        print(f"🎉 SUCCESS! Generated T2V reel: {output_video}")
        print(f"📁 File size: {os.path.getsize(output_video) / 1024 / 1024:.1f} MB")
        print(f"🎬 This video was generated entirely with open source AI!")
        print(f"🚀 Ready to show Angelo the cutting-edge approach!")
        
    except Exception as e:
        print(f"❌ T2V GENERATION FAILED: {str(e)}")
        print(f"💡 Try the main_reel_generator.py for reliable Pexels approach")
        print("Check the log file for detailed error information")
        sys.exit(1)


if __name__ == "__main__":
    main()