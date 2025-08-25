import logging
from typing import Dict, Any
from .download import DownloadStage
from .transcribe import TranscribeStage
from .translate import TranslateStage
from .synthesize import SynthesizeStage
from .overlay import OverlayStage


class DubbingPipeline:
    """Main pipeline for video dubbing process"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.download_stage = DownloadStage()
        self.transcribe_stage = TranscribeStage()
        self.translate_stage = TranslateStage()
        self.synthesize_stage = SynthesizeStage()
        self.overlay_stage = OverlayStage()
    
    async def process_audio_only(self, youtube_url: str, target_language: str, video_duration: str = "full", session_id: str = None) -> Dict[str, Any]:
        """Process video through audio dubbing pipeline (no video overlay)"""
        results = {}
        
        try:
            # Stage 1: Download
            self.logger.info(f"Processing audio dubbing: {youtube_url} -> {target_language} (duration: {video_duration})")
            download_result = await self.download_stage.process(youtube_url, video_duration, session_id)
            results['download'] = download_result
            
            # Stage 2: Transcribe
            transcribe_result = await self.transcribe_stage.process(download_result['audio_path'])
            results['transcribe'] = transcribe_result
            
            # Stage 3: Translate
            translate_result = await self.translate_stage.process(transcribe_result, target_language)
            results['translate'] = translate_result
            
            # Stage 4: Synthesize
            synthesize_result = await self.synthesize_stage.process(translate_result, download_result)
            results['synthesize'] = synthesize_result
            
            # Log completion
            self.logger.info(f"Audio dubbing pipeline completed successfully for session: {download_result['session_id']}")
            self.logger.info(f"Generated dubbed audio: {synthesize_result['synthesized_audio_path']}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Audio dubbing pipeline failed: {str(e)}")
            raise
    
    async def process_video(self, youtube_url: str, target_language: str, video_duration: str = "full", session_id: str = None) -> Dict[str, Any]:
        """Process video through complete video dubbing pipeline with overlay"""
        results = {}
        
        try:
            # Stage 1: Download
            self.logger.info(f"Processing video: {youtube_url} -> {target_language} (duration: {video_duration})")
            download_result = await self.download_stage.process(youtube_url, video_duration, session_id)
            results['download'] = download_result
            
            # Stage 2: Transcribe
            transcribe_result = await self.transcribe_stage.process(download_result['audio_path'])
            results['transcribe'] = transcribe_result
            
            # Stage 3: Translate
            translate_result = await self.translate_stage.process(transcribe_result, target_language)
            results['translate'] = translate_result
            
            # Stage 4: Synthesize
            synthesize_result = await self.synthesize_stage.process(translate_result, download_result)
            results['synthesize'] = synthesize_result
            
            # Stage 5: Overlay (Video Assembly)
            overlay_data = {
                'video_path': download_result['video_path'],
                'dubbed_audio_path': synthesize_result['synthesized_audio_path'],
                'session_id': download_result['session_id']
            }
            overlay_result = await self.overlay_stage.process(overlay_data)
            results['overlay'] = overlay_result
            
            # Log completion
            self.logger.info(f"Complete video dubbing pipeline completed successfully for session: {download_result['session_id']}")
            self.logger.info(f"Final dubbed video: {overlay_result['final_video_path']}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Pipeline failed: {str(e)}")
            raise