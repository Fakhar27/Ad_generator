"""
Video Prompt Generator for Angelo's T2V Reel System
==================================================

Uses Cohere LLM to analyze complete Italian transcript and generate
a sequence of visual prompts for business video generation.

This creates a cohesive narrative flow rather than random video clips.
"""

import os
import logging
import json
from typing import List, Dict
from dotenv import load_dotenv

try:
    from langchain_cohere import ChatCohere
    from langchain_core.prompts import ChatPromptTemplate
except ImportError as e:
    print(f"Missing LangChain packages: {e}")
    print("Please install: pip install langchain langchain-cohere")
    raise

logger = logging.getLogger(__name__)

class VideoPromptGenerator:
    """
    Generate video prompt sequences from Italian business transcripts using Cohere LLM
    """
    
    def __init__(self):
        """Initialize Cohere LLM for video prompt generation"""
        
        load_dotenv()
        
        cohere_api_key = os.getenv("CO_API_KEY")
        if not cohere_api_key:
            raise ValueError("CO_API_KEY not found in environment variables")
        
        logger.info("Initializing Cohere LLM for video prompt generation...")
        
        try:
            self.llm = ChatCohere(
                cohere_api_key=cohere_api_key,
                temperature=0.4,  # Slightly higher for creative prompts
                max_tokens=400  # More tokens for multiple prompts
            )
            
            # Create the prompt template for video sequence generation
            self.prompt_template = ChatPromptTemplate.from_messages([
                ("system", """You are a professional video director specializing in business content.

Your job is to analyze Italian business transcripts and create visual video sequences for T2V generation.

CRITICAL REQUIREMENTS:
- Create exactly 8 video prompts
- Each prompt generates a 5-second video clip  
- Total sequence = 40 seconds to match audio
- Focus on SIMPLE, CLEAR visual scenes (T2V works better with simple prompts)
- Use professional business settings only
- Each prompt should be 15-25 words maximum

VISUAL ELEMENTS TO USE:
- Business professionals in suits/professional attire
- Modern office environments, conference rooms, workspaces  
- Professional interactions: handshakes, presentations, meetings
- Corporate activities: planning, discussing, collaborating
- Clean, bright, professional lighting and environments

AVOID COMPLEX SCENES:
- No multiple simultaneous actions
- No abstract concepts
- No outdoor scenes  
- No casual/non-business settings
- Keep each scene focused on ONE main action

OUTPUT FORMAT:
Return a JSON object with this exact structure:
{{
  "video_sequence": [
    {{
      "id": 1,
      "prompt": "Professional businesswoman presenting charts to executive team in bright modern conference room",
      "purpose": "introduction",
      "target_duration": 5,
      "scene_type": "presentation"
    }},
    {{
      "id": 2, 
      "prompt": "Two executives shaking hands across glass meeting table in corporate office",
      "purpose": "agreement",
      "target_duration": 5,
      "scene_type": "interaction"
    }}
  ],
  "total_duration": 40,
  "narrative_flow": "Brief description of how videos flow together"
}}"""),
                ("human", """Italian business transcript:
"{transcript}"

Based on this transcript, create 8 professional business video prompts that visually support the spoken content. Focus on concrete business activities and professional interactions that would complement Italian business communication.

Each prompt should describe a simple, clear business scene suitable for AI video generation.""")
            ])
            
            logger.info("Cohere video prompt generator initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Cohere LLM: {e}")
            raise
    
    def generate_video_sequence(self, italian_transcript: str, target_duration: float = 40.0) -> List[Dict]:
        """
        Generate a sequence of video prompts from Italian transcript
        
        Args:
            italian_transcript (str): Full Italian text from Whisper
            target_duration (float): Target total duration (default 40s for 8×5s videos)
            
        Returns:
            List[Dict]: List of video prompt dictionaries
        """
        
        logger.info("Generating video sequence from Italian transcript...")
        logger.info(f"Target duration: {target_duration}s")
        logger.info(f"Transcript preview: {italian_transcript[:100]}...")
        
        try:
            chain = self.prompt_template | self.llm
            
            logger.info("Sending transcript to Cohere for video sequence generation...")
            response = chain.invoke({"transcript": italian_transcript})
            
            response_text = response.content.strip()
            logger.debug(f"Cohere response: {response_text}")
            
            try:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                
                if json_start == -1 or json_end == 0:
                    raise ValueError("No JSON found in response")
                
                json_text = response_text[json_start:json_end]
                prompt_data = json.loads(json_text)
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Could not parse JSON response: {e}")
                logger.warning("Falling back to manual parsing...")
                prompt_data = self._parse_fallback_response(response_text)
            
            video_sequence = prompt_data.get('video_sequence', [])
            
            if not video_sequence:
                logger.warning("No video sequence found, generating fallback prompts")
                video_sequence = self._generate_fallback_prompts(target_duration)
            
            video_sequence = self._validate_and_clean_prompts(video_sequence, target_duration)
            
            logger.info(f"Generated {len(video_sequence)} video prompts")
            self._log_video_sequence(video_sequence)
            
            return video_sequence
            
        except Exception as e:
            logger.error(f"Video prompt generation failed: {e}")
            fallback_prompts = self._generate_fallback_prompts(target_duration)
            logger.warning(f"Using {len(fallback_prompts)} fallback video prompts")
            return fallback_prompts
    
    def _parse_fallback_response(self, response_text: str) -> Dict:
        """Manually parse response if JSON parsing fails"""
        logger.info("Attempting manual parsing of Cohere response...")
        
        lines = response_text.split('\n')
        prompts = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if 'prompt' in line.lower() or (i > 0 and len(line) > 20 and any(word in line.lower() for word in ['business', 'professional', 'office', 'meeting'])):
                # Clean up the line
                prompt = line.replace('"', '').replace("'", '').strip()
                if prompt and len(prompt) > 15:
                    prompts.append({
                        "id": len(prompts) + 1,
                        "prompt": prompt[:100],  # Limit length
                        "purpose": f"scene_{len(prompts) + 1}",
                        "target_duration": 5,
                        "scene_type": "business"
                    })
        
        return {"video_sequence": prompts[:8]}  # Limit to 8
    
    def _validate_and_clean_prompts(self, video_sequence: List[Dict], target_duration: float) -> List[Dict]:
        """Validate and clean the generated prompts"""
        
        cleaned_sequence = []
        
        for i, prompt_data in enumerate(video_sequence):
            try:
                prompt = prompt_data.get('prompt', '').strip()
                if not prompt:
                    continue
                
                if len(prompt) < 10:
                    logger.warning(f"Prompt {i+1} too short: '{prompt}'")
                    continue
                
                if len(prompt) > 150:
                    prompt = prompt[:147] + "..."
                    logger.info(f"Truncated long prompt {i+1}")
                
                business_keywords = ['business', 'professional', 'office', 'corporate', 'executive', 'meeting', 'conference', 'team', 'presentation']
                if not any(keyword in prompt.lower() for keyword in business_keywords):
                    prompt = f"Professional business scene: {prompt}"
                    logger.info(f"Enhanced prompt {i+1} with business context")
                
                cleaned_prompt = {
                    "id": len(cleaned_sequence) + 1,
                    "prompt": prompt,
                    "purpose": prompt_data.get('purpose', f'scene_{len(cleaned_sequence) + 1}'),
                    "target_duration": prompt_data.get('target_duration', 5),
                    "scene_type": prompt_data.get('scene_type', 'business')
                }
                
                cleaned_sequence.append(cleaned_prompt)
                
            except Exception as e:
                logger.warning(f"Error processing prompt {i+1}: {e}")
                continue
        
        while len(cleaned_sequence) < 6:  # Minimum 6 prompts
            fallback_prompt = {
                "id": len(cleaned_sequence) + 1,
                "prompt": f"Professional business team working in modern office environment",
                "purpose": f"fallback_{len(cleaned_sequence) + 1}",
                "target_duration": 5,
                "scene_type": "business"
            }
            cleaned_sequence.append(fallback_prompt)
            logger.info(f"Added fallback prompt {len(cleaned_sequence)}")
        
        max_prompts = int(target_duration / 5)
        if len(cleaned_sequence) > max_prompts:
            cleaned_sequence = cleaned_sequence[:max_prompts]
            logger.info(f"Limited to {max_prompts} prompts for {target_duration}s target duration")
        
        return cleaned_sequence
    
    def _generate_fallback_prompts(self, target_duration: float) -> List[Dict]:
        """Generate fallback business prompts when LLM fails"""
        
        num_prompts = max(6, int(target_duration / 5))
        
        fallback_templates = [
            "Professional businesswoman presenting financial charts to executive team in bright conference room",
            "Two business executives shaking hands across modern glass meeting table",
            "Corporate team collaborating on project around whiteboard in contemporary office",
            "Business manager reviewing documents with client in professional consultation setting",
            "Executive giving presentation using digital display in modern boardroom",
            "Professional team celebrating successful deal with congratulations in office environment",
            "Business advisor explaining strategy to colleagues around conference table",
            "Corporate professionals discussing plans in bright modern workspace"
        ]
        
        prompts = []
        for i in range(num_prompts):
            template = fallback_templates[i % len(fallback_templates)]
            prompts.append({
                "id": i + 1,
                "prompt": template,
                "purpose": f"business_scene_{i + 1}",
                "target_duration": 5,
                "scene_type": "business"
            })
        
        logger.info(f"Generated {len(prompts)} fallback business prompts")
        return prompts
    
    def _log_video_sequence(self, video_sequence: List[Dict]):
        """Log the generated video sequence for review"""
        
        logger.info("Generated Video Sequence:")
        logger.info("=" * 50)
        
        total_duration = 0
        for prompt_data in video_sequence:
            duration = prompt_data.get('target_duration', 5)
            total_duration += duration
            
            logger.info(f"Video {prompt_data['id']}: {prompt_data['purpose']} ({duration}s)")
            logger.info(f"  Prompt: {prompt_data['prompt']}")
            logger.info(f"  Type: {prompt_data.get('scene_type', 'business')}")
            logger.info("-" * 40)
        
        logger.info(f"Total sequence duration: {total_duration}s")
        logger.info("=" * 50)


if __name__ == "__main__":
    generator = VideoPromptGenerator()
    
    sample_text = """
    Benvenuti alla SmartGain Community! Siamo una comunità di imprenditori 
    che supporta la crescita del vostro business attraverso consulenza 
    strategica e networking professionale. Il nostro team di esperti 
    vi aiuterà a raggiungere i vostri obiettivi di crescita.
    """
    
    print(f"Test transcript: {sample_text}")
    print("\n🎬 Generating video sequence...")
    
    try:
        video_sequence = generator.generate_video_sequence(sample_text)
        print(f"\n✅ Generated {len(video_sequence)} video prompts")
        
        for prompt_data in video_sequence:
            print(f"\nVideo {prompt_data['id']}: {prompt_data['purpose']}")
            print(f"Prompt: {prompt_data['prompt']}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")