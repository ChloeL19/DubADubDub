import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from dotenv import load_dotenv
from pipeline.dubbing import DubbingPipeline
from pipeline.base import PipelineError

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="DubADubDub API",
    description="Automatic video dubbing service using ElevenLabs and Claude AI",
    version="1.0.0"
)

# Initialize pipeline
pipeline = DubbingPipeline()


class VideoRequest(BaseModel):
    youtube_url: str
    target_language: str = "spanish"


class VideoResponse(BaseModel):
    session_id: str
    status: str
    results: Dict[str, Any]


@app.get("/")
async def root():
    return {"message": "DubADubDub API is running", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "DubADubDub"}


@app.post("/process-video", response_model=VideoResponse)
async def process_video(request: VideoRequest):
    """Process a YouTube video through the dubbing pipeline"""
    try:
        logger.info(f"Processing video request: {request.youtube_url} -> {request.target_language}")
        
        # Run the pipeline
        results = await pipeline.process_video(request.youtube_url, request.target_language)
        
        response = VideoResponse(
            session_id=results['download']['session_id'],
            status="completed",
            results=results
        )
        
        return response
        
    except PipelineError as e:
        logger.error(f"Pipeline error: {str(e)}")
        raise HTTPException(
            status_code=422,
            detail={
                "error_type": e.error_type,
                "stage": e.stage,
                "message": e.message,
                "retry_possible": e.retry_possible
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


# Test endpoints for development
@app.post("/test-download")
async def test_download(request: Dict[str, str]):
    """Test endpoint for download functionality"""
    try:
        youtube_url = request.get("youtube_url")
        if not youtube_url:
            raise HTTPException(status_code=400, detail="youtube_url required")
        
        result = await pipeline.download_stage.process(youtube_url)
        return {"status": "success", "result": result}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/test-transcribe")
async def test_transcribe(request: Dict[str, str]):
    """Test endpoint for transcription functionality"""
    try:
        audio_path = request.get("audio_path")
        if not audio_path:
            raise HTTPException(status_code=400, detail="audio_path required")
        
        result = await pipeline.transcribe_stage.process(audio_path)
        return {"status": "success", "result": result}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)