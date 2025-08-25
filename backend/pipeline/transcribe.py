import os
from typing import Dict, Any
from .base import PipelineStage, APIError
from elevenlabs import ElevenLabs


class TranscribeStage(PipelineStage):
    """Transcribes audio to text using ElevenLabs Speech to Text API"""
    
    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise APIError("Transcribe", "missing_api_key", "ELEVENLABS_API_KEY not found in environment")
        
        self.client = ElevenLabs(api_key=self.api_key)
    
    async def process(self, audio_path: str) -> Dict[str, Any]:
        """Transcribe audio file to text with language detection"""
        self.log_stage_start("Transcribe", f"Audio file: {audio_path}")
        
        try:
            # Use ElevenLabs speech-to-text API
            with open(audio_path, "rb") as audio_file:
                # Try the convert method with file parameter
                result = self.client.speech_to_text.convert(
                    file=audio_file,
                    model_id="scribe_v1"
                )
            
            # Handle the ElevenLabs response model
            if hasattr(result, 'text'):
                transcription_text = result.text
            elif hasattr(result, 'transcript'):
                transcription_text = result.transcript
            else:
                # Fallback - convert to string
                transcription_text = str(result)
            
            # Extract other attributes if available
            detected_language = getattr(result, 'detected_language', 'en')
            
            transcription_result = {
                'text': transcription_text,
                'detected_language': detected_language,
                'utterances': [],  # Will enhance this later
                'has_multiple_speakers': False
            }
            
            self.log_stage_complete("Transcribe", f"Text length: {len(transcription_text)}, Language: {transcription_result['detected_language']}")
            return transcription_result
            
        except FileNotFoundError:
            raise APIError("Transcribe", "file_not_found", f"Audio file not found: {audio_path}")
        except Exception as e:
            self.log_error("Transcribe", e)
            if "api" in str(e).lower() or "rate" in str(e).lower():
                raise APIError("Transcribe", "api_error", f"ElevenLabs API error: {str(e)}")
            else:
                raise APIError("Transcribe", "transcription_error", f"Transcription failed: {str(e)}")