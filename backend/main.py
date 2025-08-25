import os
import logging
import uuid
import time
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
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

# Store active sessions - in production, use Redis or database
active_sessions: Dict[str, Dict[str, Any]] = {}


class VideoRequest(BaseModel):
    youtube_url: str
    target_language: str = "spanish"


class VideoResponse(BaseModel):
    session_id: str
    status: str
    results: Optional[Dict[str, Any]] = None


class StatusResponse(BaseModel):
    session_id: str
    status: str
    current_stage: Optional[str] = None
    progress: Optional[int] = None
    error: Optional[str] = None
    source_language: Optional[str] = None
    target_language: Optional[str] = None
    duration: Optional[float] = None


@app.get("/")
async def serve_frontend():
    """Serve the frontend HTML file"""
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return {"message": "DubADubDub API is running", "version": "1.0.0", "frontend": "not found"}


@app.get("/api")
async def api_root():
    return {"message": "DubADubDub API is running", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "DubADubDub"}


async def process_video_background(session_id: str, youtube_url: str, target_language: str):
    """Background task to process video with stage-by-stage status updates"""
    try:
        logger.info(f"Background processing started for session {session_id}")
        results = {}
        
        # Stage 1: Download
        active_sessions[session_id].update({
            "status": "processing",
            "current_stage": "download",
            "progress": 15
        })
        
        logger.info(f"Session {session_id}: Starting download stage")
        download_result = await pipeline.download_stage.process(youtube_url)
        results['download'] = download_result
        
        # Stage 2: Transcribe
        active_sessions[session_id].update({
            "current_stage": "transcribe", 
            "progress": 35
        })
        
        logger.info(f"Session {session_id}: Starting transcribe stage")
        transcribe_result = await pipeline.transcribe_stage.process(download_result['audio_path'])
        results['transcribe'] = transcribe_result
        
        # Stage 3: Translate
        active_sessions[session_id].update({
            "current_stage": "translate",
            "progress": 55,
            "source_language": transcribe_result.get('detected_language', 'unknown')
        })
        
        logger.info(f"Session {session_id}: Starting translate stage")
        translate_result = await pipeline.translate_stage.process(transcribe_result, target_language)
        results['translate'] = translate_result
        
        # Stage 4: Synthesize
        active_sessions[session_id].update({
            "current_stage": "synthesize",
            "progress": 75
        })
        
        logger.info(f"Session {session_id}: Starting synthesize stage")
        synthesize_result = await pipeline.synthesize_stage.process(translate_result)
        results['synthesize'] = synthesize_result
        
        # Stage 5: Overlay
        active_sessions[session_id].update({
            "current_stage": "overlay",
            "progress": 90
        })
        
        logger.info(f"Session {session_id}: Starting overlay stage")
        assembly_data = {
            'video_path': download_result['video_path'],
            'dubbed_audio_path': synthesize_result['synthesized_audio_path'],
            'session_id': session_id
        }
        overlay_result = await pipeline.overlay_stage.process(assembly_data)
        results['overlay'] = overlay_result
        
        # Final completion
        active_sessions[session_id].update({
            "status": "completed",
            "current_stage": "completed",
            "progress": 100,
            "results": results,
            "source_language": transcribe_result.get('detected_language', 'unknown'),
            "target_language": target_language,
            "duration": download_result.get('duration')
        })
        
        logger.info(f"Background processing completed for session {session_id}")
        
    except PipelineError as e:
        logger.error(f"Pipeline error in background task: {str(e)}")
        active_sessions[session_id].update({
            "status": "error",
            "error": f"{e.stage}: {e.message}",
            "retry_possible": e.retry_possible
        })
    except Exception as e:
        logger.error(f"Unexpected error in background task: {str(e)}")
        active_sessions[session_id].update({
            "status": "error",
            "error": str(e),
            "retry_possible": True
        })


@app.post("/process-video", response_model=VideoResponse)
async def process_video(request: VideoRequest, background_tasks: BackgroundTasks):
    """Start processing a YouTube video through the complete dubbing pipeline"""
    try:
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        logger.info(f"Starting video processing for session {session_id}: {request.youtube_url} -> {request.target_language}")
        
        # Initialize session
        active_sessions[session_id] = {
            "session_id": session_id,
            "youtube_url": request.youtube_url,
            "target_language": request.target_language,
            "status": "queued",
            "created_at": time.time(),
            "progress": 0
        }
        
        # Start background processing
        background_tasks.add_task(
            process_video_background, 
            session_id, 
            request.youtube_url, 
            request.target_language
        )
        
        response = VideoResponse(
            session_id=session_id,
            status="queued"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error starting video processing: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to start processing", "message": str(e)}
        )


@app.get("/status/{session_id}", response_model=StatusResponse)
async def get_status(session_id: str):
    """Get the processing status of a video dubbing session"""
    if session_id not in active_sessions:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    session = active_sessions[session_id]
    
    return StatusResponse(
        session_id=session_id,
        status=session.get("status", "unknown"),
        current_stage=session.get("current_stage"),
        progress=session.get("progress"),
        error=session.get("error"),
        source_language=session.get("source_language"),
        target_language=session.get("target_language"),
        duration=session.get("duration")
    )


@app.get("/download/{session_id}")
async def download_video(session_id: str):
    """Download the processed video file"""
    if session_id not in active_sessions:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    session = active_sessions[session_id]
    
    if session.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Video processing not completed. Current status: {session.get('status', 'unknown')}"
        )
    
    # Get the final video path from results
    results = session.get("results", {})
    overlay_result = results.get("overlay", {})
    final_video_path = overlay_result.get("final_video_path")
    
    if not final_video_path or not os.path.exists(final_video_path):
        raise HTTPException(
            status_code=404,
            detail="Processed video file not found"
        )
    
    # Return the file
    filename = f"dubbed_video_{session_id}.mp4"
    return FileResponse(
        path=final_video_path,
        filename=filename,
        media_type="video/mp4"
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


@app.post("/test-translate")
async def test_translate(request: Dict[str, Any]):
    """Test endpoint for translation functionality"""
    try:
        transcription_data = request.get("transcription_data")
        target_language = request.get("target_language", "spanish")
        
        if not transcription_data:
            raise HTTPException(status_code=400, detail="transcription_data required")
        
        result = await pipeline.translate_stage.process(transcription_data, target_language)
        return {"status": "success", "result": result}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/test-synthesize")
async def test_synthesize(request: Dict[str, Any]):
    """Test endpoint for synthesis functionality"""
    try:
        translation_data = request.get("translation_data")
        
        if not translation_data:
            raise HTTPException(status_code=400, detail="translation_data required")
        
        result = await pipeline.synthesize_stage.process(translation_data)
        return {"status": "success", "result": result}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/test-overlay")
async def test_overlay(request: Dict[str, Any]):
    """Test endpoint for overlay functionality"""
    try:
        assembly_data = request.get("assembly_data")
        
        if not assembly_data:
            raise HTTPException(status_code=400, detail="assembly_data required (video_path, dubbed_audio_path, session_id)")
        
        result = await pipeline.overlay_stage.process(assembly_data)
        return {"status": "success", "result": result}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process-audio-only", response_model=VideoResponse)
async def process_audio_only(request: VideoRequest):
    """Process a YouTube video through the audio dubbing pipeline only (no video overlay)"""
    try:
        logger.info(f"Processing audio-only request: {request.youtube_url} -> {request.target_language}")
        
        # Run the audio-only pipeline
        results = await pipeline.process_audio_only(request.youtube_url, request.target_language)
        
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


# Mount static files for frontend
# Check if frontend directory exists
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)