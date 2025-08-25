import os
import asyncio
import subprocess
import tempfile
from typing import Dict, Any
from .base import PipelineStage, FileError, PipelineError


class OverlayStage(PipelineStage):
    """Stage for overlaying dubbed audio onto the original video using ffmpeg"""
    
    def __init__(self):
        super().__init__()
    
    async def process(self, assembly_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Overlay dubbed audio onto original video
        
        Args:
            assembly_data: Dictionary containing:
                - video_path: Path to original video file
                - dubbed_audio_path: Path to dubbed audio file
                - session_id: Session identifier
                
        Returns:
            Dictionary containing final video path
        """
        try:
            video_path = assembly_data.get('video_path')
            dubbed_audio_path = assembly_data.get('dubbed_audio_path')
            session_id = assembly_data.get('session_id', 'unknown')
            
            if not video_path or not dubbed_audio_path:
                raise FileError("Overlay", "missing_input", "Video path and dubbed audio path are required")
            
            if not os.path.exists(video_path):
                raise FileError("Overlay", "file_not_found", f"Video file not found: {video_path}")
            
            if not os.path.exists(dubbed_audio_path):
                raise FileError("Overlay", "file_not_found", f"Dubbed audio file not found: {dubbed_audio_path}")
            
            self.log_stage_start("Overlay", f"Video: {os.path.basename(video_path)}, Audio: {os.path.basename(dubbed_audio_path)}")
            
            # Use existing session directory (should already exist from download/synthesize stages)
            session_dir = f"outputs/sessions/{session_id}"
            if not os.path.exists(session_dir):
                os.makedirs(session_dir, exist_ok=True)
                self.logger.warning(f"Session directory did not exist, created: {session_dir}")
            
            output_path = os.path.join(session_dir, "final_dubbed_video.mp4")
            
            # Use ffmpeg to replace audio track
            # -c:v copy: Copy video stream without re-encoding (faster, preserves quality)
            # -c:a aac: Encode audio to AAC (widely compatible)
            # -map 0:v:0: Use video stream from first input (original video)
            # -map 1:a:0: Use audio stream from second input (dubbed audio)
            # -shortest: Match duration to shortest input (prevents issues with audio/video length mismatch)
            cmd = [
                'ffmpeg',
                '-y',  # Overwrite output file if it exists
                '-i', video_path,        # Input video
                '-i', dubbed_audio_path, # Input dubbed audio
                '-c:v', 'copy',          # Copy video codec
                '-c:a', 'aac',           # Audio codec
                '-map', '0:v:0',         # Map video from first input
                '-map', '1:a:0',         # Map audio from second input  
                '-shortest',             # Match shortest duration
                '-avoid_negative_ts', 'make_zero',  # Handle timestamp issues
                output_path
            ]
            
            self.logger.info(f"Running ffmpeg command: {' '.join(cmd)}")
            
            # Execute ffmpeg command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8') if stderr else "Unknown ffmpeg error"
                self.logger.error(f"ffmpeg failed with return code {process.returncode}: {error_msg}")
                raise PipelineError("Overlay", "ffmpeg_error", f"Video overlay failed: {error_msg}")
            
            # Verify output file was created and has reasonable size
            if not os.path.exists(output_path):
                raise FileError("Overlay", "output_not_created", "Output video file was not created")
            
            file_size = os.path.getsize(output_path)
            if file_size < 1024:  # Less than 1KB is likely an error
                raise FileError("Overlay", "output_too_small", f"Output file is suspiciously small: {file_size} bytes")
            
            # Get video info for verification
            duration = await self._get_video_duration(output_path)
            
            self.log_stage_complete("Overlay", f"Created {os.path.basename(output_path)} ({file_size:,} bytes, {duration:.1f}s)")
            
            return {
                'final_video_path': output_path,
                'file_size_bytes': file_size,
                'duration_seconds': duration,
                'session_id': session_id
            }
            
        except Exception as e:
            if isinstance(e, (FileError, PipelineError)):
                raise
            else:
                self.logger.error(f"Unexpected error in overlay stage: {str(e)}")
                raise PipelineError("Overlay", "unexpected_error", f"Overlay stage failed: {str(e)}")
    
    async def _get_video_duration(self, video_path: str) -> float:
        """Get video duration using ffprobe"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'csv=p=0',
                video_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and stdout:
                return float(stdout.decode().strip())
            else:
                self.logger.warning(f"Could not get video duration: {stderr.decode() if stderr else 'Unknown error'}")
                return 0.0
                
        except Exception as e:
            self.logger.warning(f"Error getting video duration: {str(e)}")
            return 0.0
    
    def validate_inputs(self, video_path: str, audio_path: str) -> bool:
        """Validate that input files exist and are readable"""
        if not os.path.exists(video_path):
            raise FileError("Overlay", "video_not_found", f"Video file not found: {video_path}")
        
        if not os.path.exists(audio_path):
            raise FileError("Overlay", "audio_not_found", f"Audio file not found: {audio_path}")
        
        # Check file sizes
        video_size = os.path.getsize(video_path)
        audio_size = os.path.getsize(audio_path)
        
        if video_size < 1024:
            raise FileError("Overlay", "video_too_small", f"Video file is too small: {video_size} bytes")
        
        if audio_size < 1024:
            raise FileError("Overlay", "audio_too_small", f"Audio file is too small: {audio_size} bytes")
        
        return True