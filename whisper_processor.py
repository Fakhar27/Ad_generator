"""
Whisper Audio Transcription Client
=================================

Handles Italian audio transcription by sending requests to the ngrok-exposed
notebook service. Converts MP3 to base64, sends to Whisper service, and
returns formatted data for subtitle generation.

Integrates with the existing notebook.ipynb Whisper service via HTTP requests.
"""

import os
import logging
import base64
import requests
from pathlib import Path
from typing import Dict, List, Optional

# Audio processing imports
try:
    from pydub import AudioSegment
except ImportError as e:
    print(f"❌ Missing required packages for audio processing: {e}")
    print("Please install: pip install pydub")
    raise

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
        Transcribe Italian audio file by sending to ngrok Whisper service
        
        Args:
            audio_path (str): Path to audio file (MP3, WAV, etc.)
            
        Returns:
            dict: {
                'full_text': complete transcription,
                'word_level': list of words with timing,
                'line_level': subtitle-ready segments,
                'total_duration': audio duration in seconds,
                'language': detected language,
                'language_probability': confidence score
            }
        """
        
        logger.info(f"📝 Starting transcription of: {audio_path}")
        
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        if not self.process_endpoint:
            raise ValueError("No Whisper service endpoint configured. Set ngrok_url during initialization.")
        
        try:
            # Step 1: Convert audio to WAV format for consistent processing
            wav_path = self._convert_to_wav(audio_path)
            
            # Step 2: Convert WAV to base64 for HTTP transmission
            logger.info("📤 Encoding audio for transmission...")
            audio_base64 = self._encode_audio_to_base64(wav_path)
            
            # Step 3: Send request to ngrok Whisper service
            logger.info(f"🌐 Sending audio to Whisper service: {self.process_endpoint}")
            
            payload = {
                "audio_data": audio_base64
            }
            
            response = requests.post(
                self.process_endpoint,
                json=payload,
                timeout=120  # 2 minute timeout for processing
            )
            
            if response.status_code != 200:
                raise Exception(f"Whisper service returned status {response.status_code}: {response.text}")
            
            # Step 4: Parse response from notebook service
            service_result = response.json()
            
            logger.info("✅ Received response from Whisper service")
            logger.info(f"   Language: {service_result.get('detected_language', 'unknown')}")
            logger.info(f"   Word count: {len(service_result.get('word_level', []))}")
            logger.info(f"   Line count: {len(service_result.get('line_level', []))}")
            
            # Step 5: Format result to match expected interface
            word_level_data = service_result.get('word_level', [])
            line_level_data = service_result.get('line_level', [])
            
            # Calculate total duration and full text from word data
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
                'words_count': len(word_level_data),
                'processing_time': service_result.get('processing_time', {})
            }
            
            logger.info(f"📊 Transcription summary:")
            logger.info(f"   Total words: {len(word_level_data)}")
            logger.info(f"   Subtitle lines: {len(line_level_data)}")
            logger.info(f"   Duration: {total_duration:.1f} seconds")
            logger.info(f"   Text preview: {full_text[:100]}...")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Transcription failed: {e}")
            raise
    
    def _convert_to_wav(self, audio_path: str) -> str:
        """Convert audio file to WAV format for HTTP transmission"""
        
        # If already WAV, return as-is
        if audio_path.lower().endswith('.wav'):
            return audio_path
        
        logger.info(f"🔄 Converting {audio_path} to WAV format...")
        
        try:
            # Load audio with pydub (supports many formats)
            audio = AudioSegment.from_file(audio_path)
            
            # Create temporary WAV file
            import tempfile
            wav_path = tempfile.mktemp(suffix=".wav")
            self.temp_files.append(wav_path)
            
            # Export as WAV with settings optimized for Whisper
            audio.export(
                wav_path,
                format="wav",
                parameters=["-ar", "16000"]  # 16kHz sample rate (Whisper standard)
            )
            
            logger.info(f"✅ Converted to WAV: {wav_path}")
            return wav_path
            
        except Exception as e:
            logger.error(f"❌ Audio conversion failed: {e}")
            raise
    
    def _encode_audio_to_base64(self, wav_path: str) -> str:
        """Encode WAV file to base64 for HTTP transmission"""
        
        try:
            with open(wav_path, 'rb') as audio_file:
                audio_bytes = audio_file.read()
                audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                
            logger.info(f"📦 Encoded audio to base64: {len(audio_base64)/1024:.1f} KB")
            return audio_base64
            
        except Exception as e:
            logger.error(f"❌ Audio encoding failed: {e}")
            raise
    
    def set_ngrok_url(self, ngrok_url: str):
        """Update the ngrok URL for the Whisper service"""
        self.ngrok_url = ngrok_url
        self.process_endpoint = f"{ngrok_url}/process_audio"
        logger.info(f"Updated Whisper service endpoint: {self.process_endpoint}")
    
    def cleanup(self):
        """Remove temporary files"""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    logger.debug(f"🗑️ Removed temp file: {temp_file}")
            except Exception as e:
                logger.warning(f"Failed to remove temp file {temp_file}: {e}")
        
        self.temp_files.clear()


# Test function for standalone usage
if __name__ == "__main__":
    # Test with Angelo's audio file
    ngrok_url = input("Enter ngrok URL for Whisper service (e.g., https://abc123.ngrok.io): ").strip()
    processor = WhisperProcessor(ngrok_url=ngrok_url)
    
    audio_file = "demovideo1.mp3"
    if os.path.exists(audio_file):
        try:
            result = processor.transcribe_audio(audio_file)
            print(f"Transcribed text: {result['full_text']}")
            print(f"Word count: {result['words_count']}")
            print(f"Duration: {result['total_duration']} seconds")
        except Exception as e:
            print(f"Transcription failed: {e}")
        finally:
            processor.cleanup()
    else:
        print(f"Test file not found: {audio_file}")