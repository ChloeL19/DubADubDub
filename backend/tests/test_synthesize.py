import pytest
import os
from dotenv import load_dotenv
from pipeline.synthesize import SynthesizeStage
from pipeline.base import APIError, FileError

# Load environment variables for tests
load_dotenv('../.env')


class TestSynthesizeStage:
    
    @pytest.fixture
    def synthesize_stage(self):
        """Create a SynthesizeStage instance for testing"""
        return SynthesizeStage()
    
    @pytest.fixture
    def sample_translation_data(self):
        """Sample translation data for testing"""
        return {
            'translated_text': 'Hola, bienvenidos a nuestro curso de aprendizaje de inglés.',
            'source_language': 'en',
            'target_language': 'spanish',
            'original_text': 'Hello, welcome to our English learning course.'
        }
    
    @pytest.mark.asyncio
    async def test_synthesize_spanish_text(self, synthesize_stage, sample_translation_data):
        """Test synthesis of Spanish text"""
        result = await synthesize_stage.process(sample_translation_data)
        
        # Verify result structure
        assert 'synthesized_audio_path' in result
        assert 'language' in result
        assert 'voice_used' in result
        assert 'text_length' in result
        
        # Verify content
        assert result['language'] == 'spanish'
        assert result['voice_used'] == '21m00Tcm4TlvDq8ikWAM'  # Rachel voice ID for Spanish
        assert result['text_length'] == len(sample_translation_data['translated_text'])
        
        # Verify file was created
        audio_path = result['synthesized_audio_path']
        assert os.path.exists(audio_path)
        assert audio_path.endswith('.mp3')
        # Should use fallback naming since no session info provided
        assert 'synthesized_' in audio_path
        
        # Verify file has some content
        file_size = os.path.getsize(audio_path)
        assert file_size > 1000  # Should be at least 1KB for actual audio
        
        print(f"Generated audio file: {audio_path} ({file_size} bytes)")
        print(f"Used voice: {result['voice_used']} for {result['language']}")
        
        # Clean up test file
        try:
            os.remove(audio_path)
        except:
            pass
    
    @pytest.mark.asyncio
    async def test_synthesize_french_text(self, synthesize_stage):
        """Test synthesis of French text"""
        french_data = {
            'translated_text': 'Bonjour, bienvenue dans notre cours d\'apprentissage de l\'anglais.',
            'target_language': 'french'
        }
        
        result = await synthesize_stage.process(french_data)
        
        assert result['language'] == 'french'
        assert result['voice_used'] == 'EXAVITQu4vr4xnSDxMaL'  # Sarah voice ID for French
        
        # Verify file exists
        audio_path = result['synthesized_audio_path']
        assert os.path.exists(audio_path)
        
        print(f"French audio with voice: {result['voice_used']}")
        
        # Clean up
        try:
            os.remove(audio_path)
        except:
            pass
    
    @pytest.mark.asyncio
    async def test_voice_selection_mapping(self, synthesize_stage):
        """Test voice selection for different languages"""
        test_cases = [
            ('spanish', '21m00Tcm4TlvDq8ikWAM'),  # Rachel
            ('french', 'EXAVITQu4vr4xnSDxMaL'),   # Sarah
            ('german', 'FGY2WhTYpPnrIDTdsKH5'),   # Laura
            ('italian', '21m00Tcm4TlvDq8ikWAM'),  # Rachel
            ('unknown_language', '21m00Tcm4TlvDq8ikWAM')  # Rachel fallback
        ]
        
        for language, expected_voice in test_cases:
            voice = synthesize_stage._select_voice_for_language(language)
            assert voice == expected_voice, f"Expected {expected_voice} for {language}, got {voice}"
    
    @pytest.mark.asyncio
    async def test_language_code_mapping(self, synthesize_stage):
        """Test language code to voice mapping"""
        test_cases = [
            ('es', '21m00Tcm4TlvDq8ikWAM'),  # Spanish code -> Rachel
            ('fr', 'EXAVITQu4vr4xnSDxMaL'),  # French code -> Sarah
            ('de', 'FGY2WhTYpPnrIDTdsKH5'),  # German code -> Laura
            ('it', '21m00Tcm4TlvDq8ikWAM')   # Italian code -> Rachel
        ]
        
        for lang_code, expected_voice in test_cases:
            voice = synthesize_stage._select_voice_for_language(lang_code)
            assert voice == expected_voice, f"Expected {expected_voice} for {lang_code}, got {voice}"
    
    @pytest.mark.asyncio
    async def test_short_text_synthesis(self, synthesize_stage):
        """Test synthesis of very short text"""
        short_data = {
            'translated_text': 'Hola.',
            'target_language': 'spanish'
        }
        
        result = await synthesize_stage.process(short_data)
        
        assert result['text_length'] == 5  # Length of "Hola."
        assert os.path.exists(result['synthesized_audio_path'])
        
        # Clean up
        try:
            os.remove(result['synthesized_audio_path'])
        except:
            pass
    
    @pytest.mark.asyncio
    async def test_session_based_file_organization(self, synthesize_stage, sample_translation_data):
        """Test that synthesis saves to session directory when session info provided"""
        session_info = {'session_id': 'test_session_123'}
        
        result = await synthesize_stage.process(sample_translation_data, session_info)
        
        # Verify file path uses session directory
        audio_path = result['synthesized_audio_path']
        assert 'sessions/test_session_123/dubbed_audio.mp3' in audio_path
        assert os.path.exists(audio_path)
        
        # Verify session directory structure
        session_dir = "outputs/sessions/test_session_123"
        assert os.path.exists(session_dir)
        
        print(f"Session-based audio saved to: {audio_path}")
        
        # Clean up
        try:
            os.remove(audio_path)
            os.rmdir(session_dir)
            os.rmdir("outputs/sessions")
        except:
            pass
    
    @pytest.mark.asyncio
    async def test_empty_text_handling(self, synthesize_stage):
        """Test handling of empty text"""
        empty_data = {
            'translated_text': '',
            'target_language': 'spanish'
        }
        
        result = await synthesize_stage.process(empty_data)
        
        # Should handle empty text gracefully
        assert 'synthesized_audio_path' in result
        assert result['text_length'] == 0
    
    def test_api_key_validation(self):
        """Test that missing API key raises appropriate error"""
        # Temporarily remove API key
        original_key = os.environ.get("ELEVENLABS_API_KEY")
        if original_key:
            del os.environ["ELEVENLABS_API_KEY"]
        
        try:
            with pytest.raises(APIError) as exc_info:
                SynthesizeStage()
            assert exc_info.value.stage == "Synthesize"
            assert exc_info.value.error_type == "missing_api_key"
        finally:
            # Restore API key
            if original_key:
                os.environ["ELEVENLABS_API_KEY"] = original_key
    
    @pytest.mark.asyncio
    async def test_output_directory_creation(self, synthesize_stage):
        """Test that output directory is created if it doesn't exist"""
        # Remove outputs directory if it exists
        import shutil
        if os.path.exists("outputs"):
            shutil.rmtree("outputs")
        
        sample_data = {
            'translated_text': 'Test audio generation.',
            'target_language': 'english'
        }
        
        result = await synthesize_stage.process(sample_data)
        
        # Directory should be created
        assert os.path.exists("outputs")
        assert os.path.exists(result['synthesized_audio_path'])
        
        # Clean up
        try:
            os.remove(result['synthesized_audio_path'])
        except:
            pass
    
    @pytest.mark.asyncio
    async def test_session_based_file_organization(self, synthesize_stage, sample_translation_data):
        """Test that synthesis saves to session directory when session info provided"""
        session_info = {'session_id': 'test_session_123'}
        
        result = await synthesize_stage.process(sample_translation_data, session_info)
        
        # Verify file path uses session directory
        audio_path = result['synthesized_audio_path']
        assert 'sessions/test_session_123/dubbed_audio.mp3' in audio_path
        assert os.path.exists(audio_path)
        
        # Verify session directory structure
        session_dir = "outputs/sessions/test_session_123"
        assert os.path.exists(session_dir)
        
        print(f"Session-based audio saved to: {audio_path}")
        
        # Clean up
        try:
            os.remove(audio_path)
            os.rmdir(session_dir)
            os.rmdir("outputs/sessions")
        except:
            pass