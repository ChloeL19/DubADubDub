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
        self.cookies_file = os.path.join(os.path.dirname(__file__), "..", "cookies.txt")
    
    async def process(self, youtube_url: str, video_duration: str = "full", session_id: str = None) -> Dict[str, Any]:
        """Download video and extract audio from YouTube URL"""
        if not session_id:
            session_id = str(int(time.time()))
        session_dir = os.path.join(self.output_dir, session_id)
        os.makedirs(session_dir, exist_ok=True)
        
        # Determine duration settings
        duration_info = self._get_duration_args(video_duration)
        duration_desc = f" (duration: {duration_info['description']})" if video_duration != "full" else ""
        
        self.log_stage_start("Download", f"URL: {youtube_url}{duration_desc}")
        
        try:
            # Download video and extract audio using yt-dlp
            audio_path = os.path.join(session_dir, "original_audio.wav")
            video_path = os.path.join(session_dir, "original_video.%(ext)s")
            
            # Build base video command with cookie authentication
            video_cmd = [
                "yt-dlp",
                "--format", "best[height<=720][ext=mp4]/best[height<=480][ext=mp4]/best[ext=mp4]/best",
                "--no-write-auto-subs",
                "--no-write-thumbnail", 
                "--concurrent-fragments", "4",
                "--retries", "3",
                "--fragment-retries", "3",
                "--sleep-interval", "1",
                "--max-sleep-interval", "5",
                "--output", video_path
            ]
            
            # Add cookies if file exists
            if os.path.exists(self.cookies_file):
                video_cmd.extend(["--cookies", self.cookies_file])
            else:
                # Fallback to anti-detection measures
                video_cmd.extend([
                    "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                    "--extractor-args", "youtube:player_client=web"
                ])
            
            # Add duration arguments if not full video
            if duration_info['args']:
                video_cmd.extend(duration_info['args'])
            
            video_cmd.append(youtube_url)
            
            # Build base audio command with cookie authentication
            audio_cmd = [
                "yt-dlp", 
                "--extract-audio",
                "--audio-format", "wav",
                "--audio-quality", "0",  # Best quality
                "--output", audio_path.replace('.wav', '.%(ext)s'),
                "--no-write-thumbnail",
                "--retries", "3",
                "--sleep-interval", "1",
                "--max-sleep-interval", "5"
            ]
            
            # Add cookies if file exists
            if os.path.exists(self.cookies_file):
                audio_cmd.extend(["--cookies", self.cookies_file])
            else:
                # Fallback to anti-detection measures
                audio_cmd.extend([
                    "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                    "--extractor-args", "youtube:player_client=web"
                ])
            
            # Add duration arguments if not full video
            if duration_info['args']:
                audio_cmd.extend(duration_info['args'])
            
            audio_cmd.append(youtube_url)
            
            # Execute video download first
            video_process = await asyncio.create_subprocess_exec(
                *video_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            video_stdout, video_stderr = await video_process.communicate()
            
            # Small delay to avoid rate limiting, then start audio download
            await asyncio.sleep(2)
            
            audio_process = await asyncio.create_subprocess_exec(
                *audio_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            audio_stdout, audio_stderr = await audio_process.communicate()
            
            # Check results
            if video_process.returncode != 0:
                self.logger.error(f"Video download stderr: {video_stderr.decode()}")
                raise FileError(
                    "Download", "download_error",
                    f"Video download failed: {video_stderr.decode()[:500]}"
                )
            
            if audio_process.returncode != 0:
                self.logger.error(f"Audio download stderr: {audio_stderr.decode()}")
                raise FileError(
                    "Download", "download_error", 
                    f"Audio download failed: {audio_stderr.decode()[:500]}"
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
    
    def _get_duration_args(self, video_duration: str) -> Dict[str, Any]:
        """Get yt-dlp arguments for duration limiting"""
        if video_duration == "full":
            return {"args": [], "description": "full video"}
        
        # Convert duration to seconds for yt-dlp
        try:
            duration_seconds = int(video_duration)
            # Use external downloader (ffmpeg) for precise time control
            return {
                "args": [
                    "--external-downloader", "ffmpeg",
                    "--external-downloader-args", f"ffmpeg:-ss 00:00:00 -t {duration_seconds}"
                ],
                "description": f"{duration_seconds} seconds"
            }
        except (ValueError, TypeError):
            self.logger.warning(f"Invalid duration '{video_duration}', using full video")
            return {"args": [], "description": "full video (fallback)"}
    
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