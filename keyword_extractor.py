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
        
        cohere_api_key = os.getenv("CO_API_KEY")
        if not cohere_api_key:
            raise ValueError("CO_API_KEY not found in environment variables")
        
        logger.info("Initializing Cohere LLM for keyword extraction...")
        
        try:
            self.llm = ChatCohere(
                cohere_api_key=cohere_api_key,
                temperature=0.3,  
                max_tokens=100  #
            )
            
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
            chain = self.prompt_template | self.llm
            
            response = chain.invoke({"transcript": italian_transcript})
            
            keywords_text = response.content.strip()
            keywords = [kw.strip().lower() for kw in keywords_text.split(',')]
            
            keywords = self._clean_keywords(keywords)
            
            keywords = self._ensure_minimum_keywords(keywords)
            
            logger.info(f"Extracted keywords: {keywords}")
            return keywords
            
        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}")
            fallback_keywords = self._get_fallback_keywords()
            logger.warning(f"Using fallback keywords: {fallback_keywords}")
            return fallback_keywords
    
    def _clean_keywords(self, raw_keywords: List[str]) -> List[str]:
        """Clean and validate extracted keywords"""
        
        cleaned = []
        
        for keyword in raw_keywords:
            keyword = keyword.strip()
            
            if not keyword:
                continue
                
            keyword = keyword.replace('"', '').replace("'", '').replace('.', '')
            
            if len(keyword) < 2 or len(keyword) > 15:
                continue
            
            if keyword.isalpha():
                cleaned.append(keyword)
        
        seen = set()
        unique_keywords = []
        for kw in cleaned:
            if kw not in seen:
                unique_keywords.append(kw)
                seen.add(kw)
        
        return unique_keywords[:5]  
    
    def _ensure_minimum_keywords(self, keywords: List[str]) -> List[str]:
        """Ensure we have at least 4 keywords, add fallbacks if needed"""
        
        fallback_keywords = ["businessman", "office", "meeting", "professional", "boardroom"]
        
        for fallback in fallback_keywords:
            if len(keywords) >= 4:
                break
            if fallback not in keywords:
                keywords.append(fallback)
        
        return keywords[:5]  
    
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
        
        keyword_map = {
            'business': 'businessman',
            'lavoro': 'office',
            'ufficio': 'office',
            'azienda': 'corporate',
            'team': 'team',
            'gruppo': 'meeting',
            'riunione': 'meeting',
            'progetto': 'presentation',
            'successo': 'handshake',  
            'crescita': 'executive',   
            'innovazione': 'boardroom',
            'leadership': 'executive',
            'professionale': 'professional',
            'strategia': 'presentation', 
            'marketing': 'presentation',
            'vendite': 'handshake',     
            'direttore': 'executive',
            'manager': 'manager',
            'imprenditore': 'entrepreneur'
        }
        
        found_keywords = []
        transcript_lower = italian_transcript.lower()
        
        for italian_word, english_word in keyword_map.items():
            if italian_word in transcript_lower:
                found_keywords.append(english_word)
        
        if not found_keywords:
            found_keywords = ["businessman", "office", "meeting"]
        
        fallback_keywords = ["professional", "executive", "boardroom", "handshake"]
        for keyword in fallback_keywords:
            if len(found_keywords) >= 4:
                break
            if keyword not in found_keywords:
                found_keywords.append(keyword)
        
        return found_keywords[:5]


if __name__ == "__main__":
    extractor = KeywordExtractor()
    
    sample_text = "Benvenuti alla nostra azienda! Oggi parleremo di strategia e crescita del business."
    keywords = extractor.extract_keywords(sample_text)
    
    print(f"Test transcript: {sample_text}")
    print(f"Extracted keywords: {keywords}")
    
    simple_keywords = extractor.extract_keywords_simple(sample_text)
    print(f"Simple extraction: {simple_keywords}")