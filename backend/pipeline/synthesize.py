import os
import time
from typing import Dict, Any
from elevenlabs import ElevenLabs
from .base import PipelineStage, APIError, FileError


class SynthesizeStage(PipelineStage):
    """Speech synthesis stage using ElevenLabs TTS"""
    
    def __init__(self):
        super().__init__()
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            raise APIError("Synthesize", "missing_api_key", "ELEVENLABS_API_KEY not found in environment")
        
        self.client = ElevenLabs(api_key=api_key)
    
    async def process(self, translation_data: Dict, session_info: Dict = None) -> Dict[str, Any]:
        """
        Generate speech from translated text using ElevenLabs TTS
        
        Args:
            translation_data: Dict containing 'translated_text' and 'target_language'
            session_info: Dict containing 'session_id' for file organization
        
        Returns:
            Dict with synthesized_audio_path, language, voice_used
        """
        translated_text = translation_data['translated_text']
        target_language = translation_data['target_language']
        
        self.log_stage_start("Synthesis", 
                           f"Generating {target_language} speech from {len(translated_text)} characters")
        
        try:
            # Determine output directory - use session if available, otherwise fallback
            if session_info and 'session_id' in session_info:
                session_dir = f"outputs/sessions/{session_info['session_id']}"
                os.makedirs(session_dir, exist_ok=True)
                output_path = os.path.join(session_dir, "dubbed_audio.mp3")
                self.logger.info(f"Using session directory: {session_dir}")
            else:
                # Fallback for standalone testing - but log this as it shouldn't happen in normal pipeline
                self.logger.warning(f"No session_info provided, using fallback directory. session_info: {session_info}")
                os.makedirs("outputs", exist_ok=True)
                output_path = f"outputs/synthesized_{int(time.time())}.mp3"
            
            # Select appropriate voice for language
            voice_id = self._select_voice_for_language(target_language)
            
            # Generate speech using ElevenLabs new API
            audio_generator = self.client.text_to_speech.convert(
                voice_id=voice_id,
                text=translated_text,
                model_id="eleven_multilingual_v2",  # Supports multiple languages
                output_format="mp3_44100_128"
            )
            
            # Collect audio data
            audio_data = b""
            for chunk in audio_generator:
                audio_data += chunk
            
            # Save the generated audio to file
            with open(output_path, "wb") as f:
                f.write(audio_data)
            
            # Verify file was created successfully
            if not os.path.exists(output_path):
                raise FileError("Synthesize", "file_creation", f"Failed to create audio file at {output_path}")
            
            result = {
                'synthesized_audio_path': output_path,
                'language': target_language,
                'voice_used': voice_id,
                'text_length': len(translated_text)
            }
            
            self.log_stage_complete("Synthesis", 
                                  f"Generated audio file: {output_path} using voice '{voice_id}'")
            
            return result
            
        except Exception as e:
            self.log_error("Synthesis", e)
            if "rate limit" in str(e).lower():
                raise APIError("Synthesize", "rate_limit", f"ElevenLabs rate limit exceeded: {str(e)}")
            elif "voice" in str(e).lower():
                raise APIError("Synthesize", "voice_error", f"Voice not available: {str(e)}")
            elif "model" in str(e).lower():
                raise APIError("Synthesize", "model_error", f"TTS model unavailable: {str(e)}")
            elif "api key" in str(e).lower() or "authentication" in str(e).lower():
                raise APIError("Synthesize", "auth_error", f"ElevenLabs authentication failed: {str(e)}")
            else:
                raise APIError("Synthesize", "tts_error", f"Text-to-speech failed: {str(e)}")
    
    def _select_voice_for_language(self, target_language: str) -> str:
        """
        Select appropriate voice ID for target language
        
        Returns:
            Voice ID suitable for the target language
        """
        # Language to voice ID mapping - using actual ElevenLabs voice IDs
        # These are voices that work well with eleven_multilingual_v2 model
        language_voice_map = {
            'english': '21m00Tcm4TlvDq8ikWAM',    # Rachel - clear female voice, excellent for English
            'spanish': '21m00Tcm4TlvDq8ikWAM',    # Rachel - clear female voice
            'french': 'EXAVITQu4vr4xnSDxMaL',     # Sarah - female voice
            'german': 'FGY2WhTYpPnrIDTdsKH5',     # Laura - female voice
            'italian': '21m00Tcm4TlvDq8ikWAM',   # Rachel works well for Italian
            'portuguese': '21m00Tcm4TlvDq8ikWAM', # Rachel works for Portuguese
            'polish': 'FGY2WhTYpPnrIDTdsKH5',     # Laura works for Polish
            'turkish': 'EXAVITQu4vr4xnSDxMaL',   # Sarah works for Turkish
            'russian': 'FGY2WhTYpPnrIDTdsKH5',   # Laura works for Russian
            'dutch': 'EXAVITQu4vr4xnSDxMaL',     # Sarah works for Dutch
            'swedish': 'FGY2WhTYpPnrIDTdsKH5',   # Laura works for Swedish
            'norwegian': 'FGY2WhTYpPnrIDTdsKH5', # Laura works for Norwegian
            'danish': 'FGY2WhTYpPnrIDTdsKH5',    # Laura works for Danish
            'finnish': 'FGY2WhTYpPnrIDTdsKH5',   # Laura works for Finnish
            'japanese': 'EXAVITQu4vr4xnSDxMaL',  # Sarah works for Japanese
            'chinese': 'EXAVITQu4vr4xnSDxMaL',   # Sarah works for Chinese
            'korean': 'EXAVITQu4vr4xnSDxMaL',    # Sarah works for Korean
            'hindi': 'EXAVITQu4vr4xnSDxMaL',     # Sarah works for Hindi
            'arabic': 'EXAVITQu4vr4xnSDxMaL',    # Sarah works for Arabic
        }
        
        # Normalize language name (handle "es", "español", "spanish" etc.)
        normalized_language = target_language.lower().strip()
        
        # Try exact match first
        if normalized_language in language_voice_map:
            return language_voice_map[normalized_language]
        
        # Try common language code mappings
        language_code_map = {
            'en': 'english',
            'es': 'spanish',
            'fr': 'french', 
            'de': 'german',
            'it': 'italian',
            'pt': 'portuguese',
            'pl': 'polish',
            'tr': 'turkish',
            'ru': 'russian',
            'nl': 'dutch',
            'sv': 'swedish',
            'no': 'norwegian',
            'da': 'danish',
            'fi': 'finnish',
            'ja': 'japanese',
            'zh': 'chinese',
            'ko': 'korean',
            'hi': 'hindi',
            'ar': 'arabic'
        }
        
        if normalized_language in language_code_map:
            mapped_language = language_code_map[normalized_language]
            return language_voice_map[mapped_language]
        
        # Default fallback voice - Rachel (good quality, reliable)
        self.logger.warning(f"No specific voice mapping for language '{target_language}', using default voice Rachel")
        return '21m00Tcm4TlvDq8ikWAM'  # Rachel - reliable default female voice