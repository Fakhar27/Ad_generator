"""
Keyword Extraction Module using Cohere LLM
==========================================

Analyzes Italian transcript and extracts English keywords suitable for
searching Pexels stock videos. Uses the existing Cohere setup from
langchain_service.py with fitness-focused prompting.

Reuses existing Cohere API setup for zero additional cost.
"""

import os
import logging
from typing import List
from dotenv import load_dotenv

# LangChain imports (reusing existing setup)
try:
    from langchain_cohere import ChatCohere
    from langchain_core.prompts import ChatPromptTemplate
except ImportError as e:
    print(f"Missing LangChain packages: {e}")
    print("Please install: pip install langchain langchain-cohere")
    raise

logger = logging.getLogger(__name__)

class KeywordExtractor:
    """
    Extract video search keywords from Italian transcript using Cohere LLM
    """
    
    def __init__(self):
        """Initialize Cohere LLM with existing setup"""
        
        load_dotenv()
        
        # Get API key from environment
        cohere_api_key = os.getenv("CO_API_KEY")
        if not cohere_api_key:
            raise ValueError("CO_API_KEY not found in environment variables")
        
        logger.info("Initializing Cohere LLM for keyword extraction...")
        
        try:
            # Initialize Cohere LLM (same setup as langchain_service.py)
            self.llm = ChatCohere(
                cohere_api_key=cohere_api_key,
                temperature=0.3,  # Lower temperature for consistent keywords
                max_tokens=100  # Short response needed
            )
            
            # Create the prompt template for corporate/business keyword extraction
            self.prompt_template = ChatPromptTemplate.from_messages([
                ("system", """You are a business video content analyzer for stock video searches.

Extract 4-5 VISUAL English keywords from Italian business content for Pexels stock video search.

FOCUS ON CONCRETE VISUALS that appear in business/corporate stock videos:
- PEOPLE: businessman, businesswoman, executive, professional, team, entrepreneur  
- SETTINGS: office, conference room, meeting room, workspace, boardroom, desk
- ACTIVITIES: meeting, presentation, handshake, collaboration, discussion, planning
- OBJECTS: suit, computer, documents, whiteboard, projector

AVOID ABSTRACT CONCEPTS like "transparency", "innovation", "growth" - these don't translate to visual stock footage.

Return ONLY comma-separated keywords focusing on CONCRETE VISUAL ELEMENTS.
Example: "businessman, office, meeting, presentation, team"
"""),
                ("human", """Italian transcript: {transcript}

Extract 4-5 English keywords for finding relevant business videos:""")
            ])
            
            logger.info("Cohere keyword extractor initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Cohere LLM: {e}")
            raise
    
    def extract_keywords(self, italian_transcript: str) -> List[str]:
        """
        Extract English keywords from Italian transcript for video search
        
        Args:
            italian_transcript (str): Full Italian text from Whisper
            
        Returns:
            List[str]: 4-5 English keywords optimized for Pexels search
        """
        
        logger.info("Extracting keywords from transcript...")
        logger.debug(f"Transcript preview: {italian_transcript[:100]}...")
        
        try:
            # Create the chain
            chain = self.prompt_template | self.llm
            
            # Generate keywords
            response = chain.invoke({"transcript": italian_transcript})
            
            # Parse response
            keywords_text = response.content.strip()
            keywords = [kw.strip().lower() for kw in keywords_text.split(',')]
            
            # Clean and validate keywords
            keywords = self._clean_keywords(keywords)
            
            # Add fallback keywords if too few were extracted
            keywords = self._ensure_minimum_keywords(keywords)
            
            logger.info(f"Extracted keywords: {keywords}")
            return keywords
            
        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}")
            # Return fallback keywords for business content
            fallback_keywords = self._get_fallback_keywords()
            logger.warning(f"Using fallback keywords: {fallback_keywords}")
            return fallback_keywords
    
    def _clean_keywords(self, raw_keywords: List[str]) -> List[str]:
        """Clean and validate extracted keywords"""
        
        cleaned = []
        
        for keyword in raw_keywords:
            # Remove extra whitespace
            keyword = keyword.strip()
            
            # Skip empty strings
            if not keyword:
                continue
                
            # Remove quotes and special characters
            keyword = keyword.replace('"', '').replace("'", '').replace('.', '')
            
            # Skip if too short or too long
            if len(keyword) < 2 or len(keyword) > 15:
                continue
            
            # Only keep alphabetic keywords (no numbers/symbols)
            if keyword.isalpha():
                cleaned.append(keyword)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for kw in cleaned:
            if kw not in seen:
                unique_keywords.append(kw)
                seen.add(kw)
        
        return unique_keywords[:5]  # Maximum 5 keywords
    
    def _ensure_minimum_keywords(self, keywords: List[str]) -> List[str]:
        """Ensure we have at least 4 keywords, add fallbacks if needed"""
        
        fallback_keywords = ["businessman", "office", "meeting", "professional", "boardroom"]
        
        # Add fallbacks if we don't have enough keywords
        for fallback in fallback_keywords:
            if len(keywords) >= 4:
                break
            if fallback not in keywords:
                keywords.append(fallback)
        
        return keywords[:5]  # Limit to 5 keywords
    
    def _get_fallback_keywords(self) -> List[str]:
        """
        Return default business keywords when LLM extraction fails
        These are proven to work well with Pexels business content
        """
        return ["businessman", "office", "meeting", "boardroom", "executive"]

    def extract_keywords_simple(self, italian_transcript: str) -> List[str]:
        """
        Simple keyword extraction without LLM (backup method)
        Uses text matching for common Italian business terms
        """
        
        logger.info("Using simple keyword matching (fallback method)")
        
        # Italian -> English keyword mappings for VISUAL business content
        keyword_map = {
            'business': 'businessman',
            'lavoro': 'office',
            'ufficio': 'office',
            'azienda': 'corporate',
            'team': 'team',
            'gruppo': 'meeting',
            'riunione': 'meeting',
            'progetto': 'presentation',
            'successo': 'handshake',  # Success often shown as handshakes
            'crescita': 'executive',   # Growth often shown with executives
            'innovazione': 'boardroom', # Innovation often in boardroom settings
            'leadership': 'executive',
            'professionale': 'professional',
            'strategia': 'presentation', # Strategy often shown in presentations
            'marketing': 'presentation',
            'vendite': 'handshake',     # Sales often shown as handshakes
            'direttore': 'executive',
            'manager': 'manager',
            'imprenditore': 'entrepreneur'
        }
        
        found_keywords = []
        transcript_lower = italian_transcript.lower()
        
        # Find Italian words and map to English
        for italian_word, english_word in keyword_map.items():
            if italian_word in transcript_lower:
                found_keywords.append(english_word)
        
        # Add default visual business keywords if none found
        if not found_keywords:
            found_keywords = ["businessman", "office", "meeting"]
        
        # Ensure we have enough keywords
        fallback_keywords = ["professional", "executive", "boardroom", "handshake"]
        for keyword in fallback_keywords:
            if len(found_keywords) >= 4:
                break
            if keyword not in found_keywords:
                found_keywords.append(keyword)
        
        return found_keywords[:5]


# Test function for standalone usage  
if __name__ == "__main__":
    # Test the keyword extractor
    extractor = KeywordExtractor()
    
    # Test with sample Italian business text
    sample_text = "Benvenuti alla nostra azienda! Oggi parleremo di strategia e crescita del business."
    keywords = extractor.extract_keywords(sample_text)
    
    print(f"Test transcript: {sample_text}")
    print(f"Extracted keywords: {keywords}")
    
    # Test simple extraction
    simple_keywords = extractor.extract_keywords_simple(sample_text)
    print(f"Simple extraction: {simple_keywords}")