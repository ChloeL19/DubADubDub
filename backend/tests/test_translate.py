import pytest
import os
from dotenv import load_dotenv
from pipeline.translate import TranslateStage
from pipeline.base import APIError

# Load environment variables for tests
load_dotenv('../.env')


class TestTranslateStage:
    
    @pytest.fixture
    def translate_stage(self):
        """Create a TranslateStage instance for testing"""
        return TranslateStage()
    
    @pytest.fixture
    def sample_transcription_data(self):
        """Sample transcription data for testing"""
        return {
            'text': 'Hello, welcome to our English learning course. Today we will learn about basic conversations.',
            'detected_language': 'en'
        }
    
    @pytest.mark.asyncio
    async def test_translate_to_spanish(self, translate_stage, sample_transcription_data):
        """Test translation from English to Spanish"""
        target_language = "spanish"
        
        result = await translate_stage.process(sample_transcription_data, target_language)
        
        # Verify result structure
        assert 'translated_text' in result
        assert 'source_language' in result
        assert 'target_language' in result
        assert 'original_text' in result
        
        # Verify content
        assert result['source_language'] == 'en'
        assert result['target_language'] == 'spanish'
        assert result['original_text'] == sample_transcription_data['text']
        assert len(result['translated_text']) > 0
        assert result['translated_text'] != sample_transcription_data['text']  # Should be different
        
        print(f"Original: {result['original_text']}")
        print(f"Translated: {result['translated_text']}")
    
    @pytest.mark.asyncio
    async def test_translate_to_french(self, translate_stage, sample_transcription_data):
        """Test translation from English to French"""
        target_language = "french"
        
        result = await translate_stage.process(sample_transcription_data, target_language)
        
        assert result['target_language'] == 'french'
        assert len(result['translated_text']) > 0
        assert result['translated_text'] != sample_transcription_data['text']
        
        print(f"French translation: {result['translated_text']}")
    
    @pytest.mark.asyncio
    async def test_empty_text_handling(self, translate_stage):
        """Test handling of empty text"""
        empty_transcription = {
            'text': '',
            'detected_language': 'en'
        }
        
        result = await translate_stage.process(empty_transcription, "spanish")
        
        # Should handle empty text gracefully
        assert 'translated_text' in result
        assert result['translated_text'] is not None
    
    @pytest.mark.asyncio
    async def test_translation_prompt_creation(self, translate_stage):
        """Test the translation prompt creation"""
        text = "This is a test sentence."
        target_language = "german"
        source_language = "en"
        
        prompt = translate_stage._create_translation_prompt(text, target_language, source_language)
        
        assert "german" in prompt.lower()
        assert "en" in prompt.lower()
        assert text in prompt
        assert "natural" in prompt.lower()
        assert "speaking style" in prompt.lower()
    
    def test_api_key_validation(self):
        """Test that missing API key raises appropriate error"""
        # Temporarily remove API key
        original_key = os.environ.get("ANTHROPIC_API_KEY")
        if original_key:
            del os.environ["ANTHROPIC_API_KEY"]
        
        try:
            with pytest.raises(APIError) as exc_info:
                TranslateStage()
            assert exc_info.value.stage == "Translate"
            assert exc_info.value.error_type == "missing_api_key"
        finally:
            # Restore API key
            if original_key:
                os.environ["ANTHROPIC_API_KEY"] = original_key
    
    @pytest.mark.asyncio
    async def test_long_text_handling(self, translate_stage):
        """Test handling of longer text content"""
        long_text = "Welcome to our comprehensive English learning program. " * 20  # Repeat to make longer
        long_transcription = {
            'text': long_text,
            'detected_language': 'en'
        }
        
        result = await translate_stage.process(long_transcription, "spanish")
        
        assert len(result['translated_text']) > 100  # Should be substantial
        assert result['translated_text'] != long_text
        
        print(f"Long text translation length: {len(result['translated_text'])} characters")