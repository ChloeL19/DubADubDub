import os
import asyncio
from typing import Dict, Any
import anthropic
from .base import PipelineStage, APIError


class TranslateStage(PipelineStage):
    """Translation stage using Anthropic Claude API"""
    
    def __init__(self):
        super().__init__()
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise APIError("Translate", "missing_api_key", "ANTHROPIC_API_KEY not found in environment")
        
        self.client = anthropic.Anthropic(api_key=api_key)
    
    async def process(self, transcription_data: Dict, target_language: str) -> Dict[str, Any]:
        """
        Translate transcribed text to target language
        
        Args:
            transcription_data: Dict containing 'text' and 'detected_language'
            target_language: Target language for translation (e.g., "spanish", "french")
        
        Returns:
            Dict with translated_text, source_language, target_language
        """
        self.log_stage_start("Translation", 
                           f"Translating from {transcription_data.get('detected_language', 'unknown')} to {target_language}")
        
        try:
            source_text = transcription_data['text']
            source_language = transcription_data.get('detected_language', 'unknown')
            
            # Create translation prompt
            prompt = self._create_translation_prompt(source_text, target_language, source_language)
            
            # Call Claude API
            response = await asyncio.to_thread(
                self.client.messages.create,
                model="claude-3-haiku-20240307",  # Using Haiku for speed and cost efficiency
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            translated_text = response.content[0].text.strip()
            
            result = {
                'translated_text': translated_text,
                'source_language': source_language,
                'target_language': target_language,
                'original_text': source_text
            }
            
            self.log_stage_complete("Translation", 
                                  f"Translated {len(source_text)} chars to {len(translated_text)} chars")
            
            return result
            
        except Exception as e:
            self.log_error("Translation", e)
            if "rate limit" in str(e).lower():
                raise APIError("Translate", "rate_limit", f"Claude API rate limit exceeded: {str(e)}")
            elif "api key" in str(e).lower() or "authentication" in str(e).lower():
                raise APIError("Translate", "auth_error", f"Authentication failed: {str(e)}")
            elif "model" in str(e).lower():
                raise APIError("Translate", "model_error", f"Model unavailable: {str(e)}")
            else:
                raise APIError("Translate", "api_error", f"Claude API error: {str(e)}")
    
    def _create_translation_prompt(self, text: str, target_language: str, source_language: str) -> str:
        """Create optimized translation prompt for Claude"""
        return f"""Translate this {source_language} text to {target_language}. Preserve the natural speaking style and conversational tone. Keep the translation length similar to the original. Return only the translated text with no additional commentary.

{text}"""