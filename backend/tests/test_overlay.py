import pytest
import os
import tempfile
import shutil
from dotenv import load_dotenv
from pipeline.overlay import OverlayStage
from pipeline.base import PipelineError, FileError

# Load environment variables for tests
load_dotenv('../.env')


class TestOverlayStage:
    
    @pytest.fixture
    def overlay_stage(self):
        """Create an OverlayStage instance for testing"""
        return OverlayStage()
    
    @pytest.fixture
    def test_video_path(self):
        """Use existing test video file from previous sessions"""
        video_path = "outputs/sessions/1756145058/original_video.mp4"
        
        if not os.path.exists(video_path):
            pytest.skip(f"Test video file not found: {video_path}")
        
        return video_path
    
    @pytest.fixture
    def test_audio_path(self):
        """Use existing test audio file from previous sessions"""
        audio_path = "outputs/sessions/1756145058/dubbed_audio.mp3"
        
        if not os.path.exists(audio_path):
            pytest.skip(f"Test audio file not found: {audio_path}")
        
        return audio_path
    
    @pytest.fixture
    def sample_assembly_data(self, test_video_path, test_audio_path):
        """Sample assembly data for testing"""
        return {
            'video_path': test_video_path,
            'dubbed_audio_path': test_audio_path,
            'session_id': 'test_overlay_session'
        }
    
    @pytest.mark.asyncio
    async def test_successful_overlay(self, overlay_stage, sample_assembly_data):
        """Test successful video overlay operation"""
        result = await overlay_stage.process(sample_assembly_data)
        
        # Verify result structure
        assert 'final_video_path' in result
        assert 'file_size_bytes' in result
        assert 'duration_seconds' in result
        assert 'session_id' in result
        
        # Verify content
        assert result['session_id'] == 'test_overlay_session'
        assert 'final_dubbed_video.mp4' in result['final_video_path']
        assert result['file_size_bytes'] > 1024  # Should be reasonable size
        assert result['duration_seconds'] > 0    # Should have duration
        
        # Verify file was created
        output_path = result['final_video_path']
        assert os.path.exists(output_path)
        assert output_path.endswith('.mp4')
        
        # Verify file in correct session directory  
        assert 'sessions/test_overlay_session' in output_path
        assert output_path.endswith('sessions/test_overlay_session/final_dubbed_video.mp4')
        
        print(f"Created final video: {output_path}")
        print(f"File size: {result['file_size_bytes']:,} bytes")
        print(f"Duration: {result['duration_seconds']:.1f} seconds")
        
        # Cleanup
        try:
            os.remove(output_path)
            session_dir = "outputs/sessions/test_overlay_session"
            if os.path.exists(session_dir):
                os.rmdir(session_dir)
                os.rmdir("outputs/sessions")
        except:
            pass
    
    @pytest.mark.asyncio
    async def test_missing_video_file(self, overlay_stage):
        """Test handling of missing video file"""
        assembly_data = {
            'video_path': 'nonexistent_video.mp4',
            'dubbed_audio_path': 'test_audio.mp3',  # This doesn't need to exist for this test
            'session_id': 'test_session'
        }
        
        with pytest.raises(FileError) as exc_info:
            await overlay_stage.process(assembly_data)
        
        assert exc_info.value.stage == "Overlay"
        assert exc_info.value.error_type == "file_not_found"
        assert "Video file not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_missing_audio_file(self, overlay_stage, test_video_path):
        """Test handling of missing audio file"""
        assembly_data = {
            'video_path': test_video_path,
            'dubbed_audio_path': 'nonexistent_audio.mp3',
            'session_id': 'test_session'
        }
        
        with pytest.raises(FileError) as exc_info:
            await overlay_stage.process(assembly_data)
        
        assert exc_info.value.stage == "Overlay"
        assert exc_info.value.error_type == "file_not_found"
        assert "Dubbed audio file not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_missing_input_paths(self, overlay_stage):
        """Test handling of missing input paths"""
        # Test missing video path
        assembly_data = {
            'dubbed_audio_path': 'test_audio.mp3',
            'session_id': 'test_session'
        }
        
        with pytest.raises(FileError) as exc_info:
            await overlay_stage.process(assembly_data)
        
        assert exc_info.value.error_type == "missing_input"
        
        # Test missing audio path
        assembly_data = {
            'video_path': 'test_video.mp4',
            'session_id': 'test_session'
        }
        
        with pytest.raises(FileError) as exc_info:
            await overlay_stage.process(assembly_data)
        
        assert exc_info.value.error_type == "missing_input"
    
    @pytest.mark.asyncio
    async def test_session_directory_creation(self, overlay_stage, sample_assembly_data):
        """Test that session directory is created if it doesn't exist"""
        # Ensure session directory doesn't exist
        session_dir = "outputs/sessions/test_overlay_session"
        if os.path.exists(session_dir):
            shutil.rmtree(session_dir, ignore_errors=True)
        
        result = await overlay_stage.process(sample_assembly_data)
        
        # Session directory should be created
        assert os.path.exists(session_dir)
        assert os.path.exists(result['final_video_path'])
        
        # Cleanup
        try:
            os.remove(result['final_video_path'])
            os.rmdir(session_dir)
            os.rmdir("outputs/sessions")
        except:
            pass
    
    def test_validate_inputs(self, overlay_stage, test_video_path, test_audio_path):
        """Test input validation method"""
        # Valid inputs should pass
        assert overlay_stage.validate_inputs(test_video_path, test_audio_path) == True
        
        # Invalid video path should raise error
        with pytest.raises(FileError) as exc_info:
            overlay_stage.validate_inputs('nonexistent.mp4', test_audio_path)
        assert exc_info.value.error_type == "video_not_found"
        
        # Invalid audio path should raise error
        with pytest.raises(FileError) as exc_info:
            overlay_stage.validate_inputs(test_video_path, 'nonexistent.mp3')
        assert exc_info.value.error_type == "audio_not_found"
    
    @pytest.mark.asyncio
    async def test_video_duration_detection(self, overlay_stage, test_video_path):
        """Test video duration detection"""
        duration = await overlay_stage._get_video_duration(test_video_path)
        
        # Should detect reasonable duration for BBC Learning English video (around 57 seconds)
        assert 50.0 <= duration <= 65.0
        print(f"Detected video duration: {duration:.2f} seconds")
    
    @pytest.mark.asyncio
    async def test_invalid_video_duration(self, overlay_stage):
        """Test duration detection with invalid file"""
        duration = await overlay_stage._get_video_duration('nonexistent.mp4')
        
        # Should return 0.0 for invalid file
        assert duration == 0.0
    
    @pytest.mark.asyncio
    async def test_default_session_id(self, overlay_stage, test_video_path, test_audio_path):
        """Test behavior with missing session_id"""
        assembly_data = {
            'video_path': test_video_path,
            'dubbed_audio_path': test_audio_path
            # No session_id provided
        }
        
        result = await overlay_stage.process(assembly_data)
        
        # Should use 'unknown' as default session_id
        assert result['session_id'] == 'unknown'
        assert 'sessions/unknown' in result['final_video_path']
        
        # Cleanup
        try:
            os.remove(result['final_video_path'])
            session_dir = "outputs/sessions/unknown"
            if os.path.exists(session_dir):
                os.rmdir(session_dir)
                os.rmdir("outputs/sessions")
        except:
            pass
    
    @pytest.mark.asyncio
    async def test_ffmpeg_availability(self):
        """Test that ffmpeg is available for overlay operations"""
        import shutil
        
        ffmpeg_path = shutil.which('ffmpeg')
        assert ffmpeg_path is not None, "ffmpeg is not available in PATH"
        
        # Also test ffprobe
        ffprobe_path = shutil.which('ffprobe')
        assert ffprobe_path is not None, "ffprobe is not available in PATH"
        
        print(f"ffmpeg found at: {ffmpeg_path}")
        print(f"ffprobe found at: {ffprobe_path}")
    
    @pytest.mark.asyncio
    async def test_output_file_overwrite(self, overlay_stage, sample_assembly_data):
        """Test that existing output files are overwritten"""
        # Run overlay once
        result1 = await overlay_stage.process(sample_assembly_data)
        output_path = result1['final_video_path']
        original_size = result1['file_size_bytes']
        
        # Run overlay again with same session - should overwrite
        result2 = await overlay_stage.process(sample_assembly_data)
        
        # Should be same path but potentially different content
        assert result2['final_video_path'] == output_path
        assert os.path.exists(output_path)
        
        # Cleanup
        try:
            os.remove(output_path)
            session_dir = "outputs/sessions/test_overlay_session"
            if os.path.exists(session_dir):
                os.rmdir(session_dir)
                os.rmdir("outputs/sessions")
        except:
            pass