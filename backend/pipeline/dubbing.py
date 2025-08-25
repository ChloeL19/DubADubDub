import logging
from typing import Dict, Any
from .download import DownloadStage
from .transcribe import TranscribeStage


class DubbingPipeline:
    """Main pipeline for video dubbing process"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.download_stage = DownloadStage()
        self.transcribe_stage = TranscribeStage()
        # Additional stages will be added in future PRs
        self.translate_stage = None
        self.synthesize_stage = None
    
    async def process_video(self, youtube_url: str, target_language: str) -> Dict[str, Any]:
        """Process video through download and transcription stages"""
        results = {}
        
        try:
            # Stage 1: Download
            self.logger.info(f"Processing video: {youtube_url}")
            download_result = await self.download_stage.process(youtube_url)
            results['download'] = download_result
            
            # Stage 2: Transcribe
            transcribe_result = await self.transcribe_stage.process(download_result['audio_path'])
            results['transcribe'] = transcribe_result
            
            # Log completion
            self.logger.info(f"Pipeline completed successfully for session: {download_result['session_id']}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Pipeline failed: {str(e)}")
            raise