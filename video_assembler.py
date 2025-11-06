"""
Video Assembly Module
====================

Handles final video assembly: concatenates Pexels videos, adds audio layers
(original Italian + background music), burns Italian subtitles, and exports
the final vertical TikTok-ready reel.

Reuses existing MoviePy infrastructure from video_manager.py with
optimizations for the fitness reel use case.
"""

import os
import logging
import tempfile
from typing import List, Dict
from pathlib import Path

# Video processing imports (following video_manager.py pattern)
try:
    from moviepy import *
    from moviepy.video.tools.subtitles import SubtitlesClip
except ImportError as e:
    print(f"❌ Missing MoviePy: {e}")
    print("Please install: pip install moviepy")
    raise

logger = logging.getLogger(__name__)

class VideoAssembler:
    """
    Assembles final reel from video segments, audio, and subtitles
    """
    
    def __init__(self):
        """Initialize video assembler"""
        
        self.temp_dir = tempfile.mkdtemp()
        self.temp_files = []
        
        # Video output settings (TikTok/Reels format)
        self.target_width = 1080
        self.target_height = 1920  # 9:16 aspect ratio
        self.target_fps = 30
        
        # Font settings for subtitles
        self.subtitle_font = self._get_subtitle_font()
        
        logger.info(f"Video assembler initialized")
        logger.info(f"   Output resolution: {self.target_width}x{self.target_height}")
        logger.info(f"   Temp directory: {self.temp_dir}")
    
    def create_final_reel(self, video_files: List[str], original_audio_path: str, 
                         transcript_data: Dict, output_filename: str = None) -> str:
        """
        Create the final reel by combining all components
        
        Args:
            video_files: List of already downloaded video file paths
            original_audio_path: Path to Angelo's Italian audio
            transcript_data: Whisper transcription with timing data
            output_filename: Custom output name (optional)
            
        Returns:
            str: Path to final video file
        """
        
        logger.info("Starting final video assembly...")
        
        try:
            # Step 1: Process already downloaded video files
            logger.info("Step 1: Processing video files...")
            processed_clips = self._process_video_files(video_files, transcript_data['total_duration'])
            
            # Step 2: Concatenate videos
            logger.info("Step 2: Concatenating video segments...")
            concatenated_video = self._concatenate_videos(processed_clips)
            
            # Step 3: Add audio layers (Italian + background music)
            logger.info("Step 3: Adding audio layers...")
            video_with_audio = self._add_audio_layers(concatenated_video, original_audio_path)
            
            # Step 4: Burn Italian subtitles
            logger.info("Step 4: Adding Italian subtitles...")
            final_video = self._add_subtitles(video_with_audio, transcript_data)
            
            # Step 5: Export final video
            logger.info("Step 5: Exporting final video...")
            output_path = self._export_final_video(final_video, output_filename)
            
            logger.info(f"Video assembly complete: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Video assembly failed: {e}")
            raise
        finally:
            # Cleanup will be called by main script
            pass
    
    def _process_video_files(self, video_files: List[str], target_duration: float) -> List[VideoFileClip]:
        """Process already downloaded video files into MoviePy clips"""
        
        if not video_files:
            raise ValueError("No video files provided")
        
        processed_clips = []
        duration_per_clip = target_duration / len(video_files)
        
        for i, video_file in enumerate(video_files):
            try:
                logger.info(f"   Processing clip {i+1}/{len(video_files)}: {video_file}")
                
                # Load video clip
                clip = VideoFileClip(video_file)
                
                # Since Pexels already provides portrait videos, no resizing needed
                # Just ensure it matches our target resolution if needed
                if clip.w != self.target_width or clip.h != self.target_height:
                    logger.info(f"     Adjusting resolution from {clip.w}x{clip.h} to {self.target_width}x{self.target_height}")
                    clip = clip.resized((self.target_width, self.target_height))
                
                # Trim to desired duration
                if clip.duration > duration_per_clip:
                    clip = clip.subclipped(0, duration_per_clip)
                elif clip.duration < duration_per_clip:
                    # Loop video if too short
                    loops_needed = int(duration_per_clip / clip.duration) + 1
                    clip = concatenate_videoclips([clip] * loops_needed).subclipped(0, duration_per_clip)
                
                # Remove original audio (we'll add our own)
                clip = clip.without_audio()
                
                processed_clips.append(clip)
                logger.info(f"Processed: {clip.duration:.1f}s, {clip.w}x{clip.h}")
                
            except Exception as e:
                logger.error(f"Failed to process {video_file}: {e}")
                continue
        
        if not processed_clips:
            raise ValueError("No video clips could be processed")
        
        return processed_clips
    
    
    def _concatenate_videos(self, clips: List[VideoFileClip]) -> VideoFileClip:
        """Concatenate video clips with smooth transitions"""
        
        # Add fade transitions between clips
        transition_duration = 0.5
        
        for i, clip in enumerate(clips):
            if i == 0:
                # First clip: fade in
                clips[i] = clip.with_effects([vfx.FadeIn(transition_duration)])
            elif i == len(clips) - 1:
                # Last clip: fade out
                clips[i] = clip.with_effects([vfx.FadeOut(transition_duration)])
            else:
                # Middle clips: fade in and out
                clips[i] = clip.with_effects([vfx.FadeIn(transition_duration), vfx.FadeOut(transition_duration)])
        
        # Concatenate all clips
        final_video = concatenate_videoclips(clips, method="compose")
        
        logger.info(f"Concatenated {len(clips)} clips -> {final_video.duration:.1f}s total")
        return final_video
    
    def _add_audio_layers(self, video_clip: VideoFileClip, original_audio_path: str) -> VideoFileClip:
        """Add Italian audio + background music layers"""
        
        # Load original Italian audio
        original_audio = AudioFileClip(original_audio_path)
        
        # Load background music - try multiple possible locations
        background_music_path = os.getenv("BACKGROUND_MUSIC_PATH")
        if not background_music_path:
            # Try common locations for the background music file
            possible_paths = [
                "temp_audio_1305.wav",
                "hello/temp_audio_1305.wav", 
                os.path.join(os.getcwd(), "temp_audio_1305.wav"),
                os.path.join(os.getcwd(), "hello", "temp_audio_1305.wav")
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    background_music_path = path
                    logger.info(f"Found background music at: {path}")
                    break
            
            if not background_music_path:
                background_music_path = "temp_audio_1305.wav"  # Fallback
        
        if os.path.exists(background_music_path):
            logger.info(f"   Adding background music: {background_music_path}")
            
            background_music = AudioFileClip(background_music_path)
            
            # Trim/loop background music to match video duration
            if background_music.duration > video_clip.duration:
                background_music = background_music.subclipped(0, video_clip.duration)
            elif background_music.duration < video_clip.duration:
                # Loop background music
                loops_needed = int(video_clip.duration / background_music.duration) + 1
                background_music = concatenate_audioclips([background_music] * loops_needed)
                background_music = background_music.subclipped(0, video_clip.duration)
            
            # Reduce background music volume (so Italian audio is clear) but keep it audible
            background_music = background_music.with_effects([afx.MultiplyVolume(0.4)])  # 40% volume for better audibility
            logger.info(f"   Background music volume set to 40% for audibility")
            
            # Mix original Italian audio + background music
            mixed_audio = CompositeAudioClip([original_audio, background_music])
        else:
            logger.warning("   Background music not found, using only original audio")
            mixed_audio = original_audio
        
        # Trim audio to match video duration exactly
        if mixed_audio.duration > video_clip.duration:
            mixed_audio = mixed_audio.subclipped(0, video_clip.duration)
        
        # Attach audio to video
        video_with_audio = video_clip.with_audio(mixed_audio)
        
        logger.info(f"Audio added: {mixed_audio.duration:.1f}s")
        return video_with_audio
    
    def _add_subtitles(self, video_clip: VideoFileClip, transcript_data: Dict) -> CompositeVideoClip:
        """Add Italian subtitles using word-level timing from Whisper (reusing video_manager.py logic)"""
        
        # Create word-level subtitles using the existing video_manager.py approach
        subtitle_clips = self._create_word_level_subtitles(
            transcript_data, 
            (self.target_width, self.target_height), 
            video_clip.duration
        )
        
        # Composite video with subtitles
        final_video = CompositeVideoClip([video_clip] + subtitle_clips)
        
        logger.info(f"Added {len(subtitle_clips)} subtitle clips")
        return final_video
    
    def _create_word_level_subtitles(self, whisper_data: Dict, frame_size: tuple, duration: float, subtitle_color: str = "white") -> List:
        """Creates word-level subtitle clips (adapted from video_manager.py)"""
        try:
            subtitle_clips = []
            words_data = whisper_data.get('word_level', [])
            position = ('center', 0.78)  # Position relative to frame height
            relative = True
            
            logger.info(f"Creating subtitles for {len(words_data)} words with color: {subtitle_color}")
            
            for word_data in words_data:
                word = word_data['word'].strip()
                if not word:
                    continue
                    
                word_clip = (TextClip(
                    text=word,
                    font=self.subtitle_font,
                    font_size=int(frame_size[1] * 0.075),  # 7.5% of frame height
                    color=subtitle_color,
                    stroke_color='black',
                    stroke_width=2
                )
                .with_position(position, relative=relative)
                .with_start(word_data['start'])
                .with_duration(word_data['end'] - word_data['start']))
                
                subtitle_clips.append(word_clip)
                
            return subtitle_clips
        except Exception as e:
            logger.error(f"Error creating word-level subtitles: {e}")
            return []
    
    def _export_final_video(self, final_video: CompositeVideoClip, output_filename: str = None) -> str:
        """Export final video to file"""
        
        # Create output directory
        output_dir = os.getenv("OUTPUT_DIRECTORY", "output_videos")
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename
        if output_filename is None:
            output_filename = "angelo_business_reel.mp4"
        
        output_path = os.path.join(output_dir, output_filename)
        
        # Export settings optimized for social media
        logger.info(f"   Exporting to: {output_path}")
        final_video.write_videofile(
            output_path,
            fps=self.target_fps,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            preset='medium',  # Good balance of speed/quality
            ffmpeg_params=[
                '-b:v', '3M',  # 3 Mbps video bitrate (good for mobile)
                '-b:a', '128k',  # 128 kbps audio bitrate
                '-movflags', '+faststart'  # Optimize for streaming
            ]
        )
        
        return output_path
    
    def _get_subtitle_font(self) -> str:
        """Get system font path based on OS (copied from video_manager.py)"""
        font_paths = {
            'nt': [  
                r"C:\Windows\Fonts\Arial.ttf",
                r"C:\Windows\Fonts\Calibri.ttf",
                r"C:\Windows\Fonts\segoeui.ttf"
            ],
            'posix': [  
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/TTF/Arial.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
            ]
        }

        paths = font_paths.get(os.name, [])
        for path in paths:
            if os.path.exists(path):
                logger.info(f"Using subtitle font: {path}")
                return path

        logger.warning("No system fonts found for subtitles, using default")
        return ""
    
    def cleanup(self):
        """Clean up temporary files"""
        
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    logger.debug(f"Removed temp file: {temp_file}")
            except Exception as e:
                logger.warning(f"Failed to remove temp file {temp_file}: {e}")
        
        self.temp_files.clear()
        
        # Try to remove temp directory
        try:
            import shutil
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                logger.debug(f"Removed temp directory: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to remove temp directory: {e}")


# Test function for standalone usage
if __name__ == "__main__":
    # This would be used for testing individual components
    assembler = VideoAssembler()
    print(f"Video assembler initialized with target format: {assembler.target_width}x{assembler.target_height}")
    print(f"Subtitle font: {assembler.subtitle_font}")