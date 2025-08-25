import os
import time
from typing import Dict, Any
from .base import PipelineStage, FileError
import subprocess
import asyncio


class DownloadStage(PipelineStage):
    """Downloads video and audio from YouTube URLs using yt-dlp"""
    
    def __init__(self):
        super().__init__()
        self.output_dir = "outputs/sessions"
    
    async def process(self, youtube_url: str) -> Dict[str, Any]:
        """Download video and extract audio from YouTube URL"""
        session_id = str(int(time.time()))
        session_dir = os.path.join(self.output_dir, session_id)
        os.makedirs(session_dir, exist_ok=True)
        
        self.log_stage_start("Download", f"URL: {youtube_url}")
        
        try:
            # Download video and extract audio using yt-dlp
            audio_path = os.path.join(session_dir, "original_audio.wav")
            video_path = os.path.join(session_dir, "original_video.%(ext)s")
            
            # Command to download audio only
            audio_cmd = [
                "yt-dlp",
                "--extract-audio",
                "--audio-format", "wav",
                "--output", audio_path.replace('.wav', '.%(ext)s'),
                youtube_url
            ]
            
            # Command to download video
            video_cmd = [
                "yt-dlp",
                "--format", "best[height<=720]",
                "--output", video_path,
                youtube_url
            ]
            
            # Execute audio download
            audio_process = await asyncio.create_subprocess_exec(
                *audio_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            audio_stdout, audio_stderr = await audio_process.communicate()
            
            if audio_process.returncode != 0:
                raise FileError(
                    "Download", "download_error", 
                    f"Audio download failed: {audio_stderr.decode()}"
                )
            
            # Execute video download
            video_process = await asyncio.create_subprocess_exec(
                *video_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            video_stdout, video_stderr = await video_process.communicate()
            
            if video_process.returncode != 0:
                raise FileError(
                    "Download", "download_error",
                    f"Video download failed: {video_stderr.decode()}"
                )
            
            # Find the actual downloaded files
            downloaded_files = os.listdir(session_dir)
            audio_file = None
            video_file = None
            
            for file in downloaded_files:
                if file.endswith('.wav'):
                    audio_file = os.path.join(session_dir, file)
                elif any(file.endswith(ext) for ext in ['.mp4', '.webm', '.mkv']):
                    video_file = os.path.join(session_dir, file)
            
            if not audio_file or not video_file:
                raise FileError(
                    "Download", "file_not_found",
                    f"Downloaded files not found. Available: {downloaded_files}"
                )
            
            # Get audio duration for verification
            duration = await self._get_audio_duration(audio_file)
            
            result = {
                'session_id': session_id,
                'audio_path': audio_file,
                'video_path': video_file,
                'duration': duration
            }
            
            self.log_stage_complete("Download", f"Audio: {audio_file}, Video: {video_file}")
            return result
            
        except subprocess.SubprocessError as e:
            self.log_error("Download", e)
            raise FileError("Download", "subprocess_error", str(e))
        except Exception as e:
            self.log_error("Download", e)
            raise
    
    async def _get_audio_duration(self, audio_path: str) -> float:
        """Get duration of audio file using ffprobe (if available)"""
        try:
            cmd = [
                "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                "-of", "csv=p=0", audio_path
            ]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return float(stdout.decode().strip())
            else:
                return 0.0
                
        except Exception:
            return 0.0