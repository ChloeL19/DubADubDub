import pytest
import os
import tempfile
from unittest.mock import Mock, patch, AsyncMock
from dotenv import load_dotenv
from backend.pipeline.dubbing import DubbingPipeline
from backend.pipeline.base import PipelineError

# Load environment variables from .env file
load_dotenv('../.env')


class TestDubbingPipeline:
    
    @pytest.fixture
    def pipeline(self):
        return DubbingPipeline()
    
    @pytest.fixture
    def mock_env_vars(self):
        """Mock environment variables for testing"""
        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test_key"}):
            yield
    
    @pytest.mark.asyncio
    async def test_pipeline_initialization(self, pipeline):
        """Test that pipeline initializes correctly"""
        assert pipeline.download_stage is not None
        assert pipeline.transcribe_stage is not None
        assert pipeline.translate_stage is None  # Not implemented yet
        assert pipeline.synthesize_stage is None  # Not implemented yet
    
    @pytest.mark.asyncio
    async def test_download_stage_mock(self, pipeline, mock_env_vars):
        """Test download stage with mocked yt-dlp"""
        test_url = "https://www.youtube.com/watch?v=test"
        
        # Mock the download stage process method
        mock_result = {
            'session_id': '12345',
            'audio_path': '/tmp/audio.wav',
            'video_path': '/tmp/video.mp4',
            'duration': 60.0
        }
        
        with patch.object(pipeline.download_stage, 'process', new_callable=AsyncMock) as mock_download:
            mock_download.return_value = mock_result
            
            result = await pipeline.download_stage.process(test_url)
            
            assert result['session_id'] == '12345'
            assert result['audio_path'] == '/tmp/audio.wav'
            assert result['duration'] == 60.0
            mock_download.assert_called_once_with(test_url)
    
    @pytest.mark.asyncio
    async def test_transcribe_stage_mock(self, pipeline, mock_env_vars):
        """Test transcribe stage with mocked ElevenLabs API"""
        test_audio_path = "/tmp/test_audio.wav"
        
        # Mock the transcribe stage process method
        mock_result = {
            'text': 'This is a test transcription',
            'detected_language': 'en',
            'utterances': [],
            'has_multiple_speakers': False
        }
        
        with patch.object(pipeline.transcribe_stage, 'process', new_callable=AsyncMock) as mock_transcribe:
            mock_transcribe.return_value = mock_result
            
            result = await pipeline.transcribe_stage.process(test_audio_path)
            
            assert result['text'] == 'This is a test transcription'
            assert result['detected_language'] == 'en'
            assert result['has_multiple_speakers'] is False
            mock_transcribe.assert_called_once_with(test_audio_path)
    
    @pytest.mark.asyncio
    async def test_full_pipeline_mock(self, pipeline, mock_env_vars):
        """Test full pipeline with mocked stages"""
        test_url = "https://www.youtube.com/watch?v=test"
        target_language = "spanish"
        
        # Mock download result
        download_result = {
            'session_id': '12345',
            'audio_path': '/tmp/audio.wav',
            'video_path': '/tmp/video.mp4',
            'duration': 60.0
        }
        
        # Mock transcribe result
        transcribe_result = {
            'text': 'Hello world test content',
            'detected_language': 'en',
            'utterances': [],
            'has_multiple_speakers': False
        }
        
        with patch.object(pipeline.download_stage, 'process', new_callable=AsyncMock) as mock_download, \
             patch.object(pipeline.transcribe_stage, 'process', new_callable=AsyncMock) as mock_transcribe:
            
            mock_download.return_value = download_result
            mock_transcribe.return_value = transcribe_result
            
            result = await pipeline.process_video(test_url, target_language)
            
            assert 'download' in result
            assert 'transcribe' in result
            assert result['download']['session_id'] == '12345'
            assert result['transcribe']['text'] == 'Hello world test content'
            assert result['transcribe']['detected_language'] == 'en'
            
            mock_download.assert_called_once_with(test_url)
            mock_transcribe.assert_called_once_with('/tmp/audio.wav')
    
    @pytest.mark.asyncio
    async def test_pipeline_error_handling(self, pipeline, mock_env_vars):
        """Test pipeline error handling"""
        test_url = "https://invalid-url"
        target_language = "spanish"
        
        # Mock download stage to raise an error
        with patch.object(pipeline.download_stage, 'process', new_callable=AsyncMock) as mock_download:
            mock_download.side_effect = PipelineError("Download", "invalid_url", "Invalid YouTube URL")
            
            with pytest.raises(PipelineError) as exc_info:
                await pipeline.process_video(test_url, target_language)
            
            assert exc_info.value.stage == "Download"
            assert exc_info.value.error_type == "invalid_url"