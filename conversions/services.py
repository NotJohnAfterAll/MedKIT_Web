import os
import uuid
import ffmpeg
from typing import Dict, Any, Optional, List
from django.conf import settings
from django.core.files.storage import default_storage
from .models import ConversionRequest
import logging

logger = logging.getLogger(__name__)

class ConversionService:
    """Service for handling media conversion using ffmpeg, inspired by the original convertor.py"""
    
    def __init__(self):
        self.conversion_dir = os.path.join(settings.MEDIA_ROOT, 'conversions')
        os.makedirs(self.conversion_dir, exist_ok=True)
    
    SUPPORTED_FORMATS = {
        "video": ["mp4", "mov", "mkv", "avi", "webm"],
        "audio": ["mp3", "flac", "wav", "m4a", "ogg", "aac"],
        "image": ["jpg", "jpeg", "png", "webp", "avif", "ico"]
    }
    
    VIDEO_CODECS = {
        "h264": "libx264",
        "h265": "libx265", 
        "av1": "libaom-av1"
    }
    
    AUDIO_CODECS = ["aac", "mp3", "flac", "alac"]
    
    def get_file_category(self, file_format: str) -> str:
        """Determine if file is video, audio, or image"""
        file_format = file_format.lower()
        for category, formats in self.SUPPORTED_FORMATS.items():
            if file_format in formats:
                return category
        return "unknown"
    
    def get_supported_output_formats(self, input_format: str) -> List[str]:
        """Get supported output formats for a given input format"""
        category = self.get_file_category(input_format)
        if category in self.SUPPORTED_FORMATS:
            formats = self.SUPPORTED_FORMATS[category].copy()
            if input_format.lower() in formats:
                formats.remove(input_format.lower())
            return formats
        return []
    
    def convert_media(self, conversion_request: ConversionRequest) -> str:
        """Convert media file based on conversion request"""
        try:
            input_path = os.path.join(settings.MEDIA_ROOT, conversion_request.input_file.name)
            
            # Generate output filename
            base_name = os.path.splitext(conversion_request.input_filename)[0]
            safe_name = "".join(c for c in base_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            output_filename = f"{uuid.uuid4()}_{safe_name}.{conversion_request.output_format}"
            output_path = os.path.join(self.conversion_dir, output_filename)
            
            # Update status to processing
            conversion_request.status = 'processing'
            conversion_request.progress = 0
            conversion_request.save()
            
            # Determine conversion type
            input_category = self.get_file_category(conversion_request.input_format)
            output_category = self.get_file_category(conversion_request.output_format)
            
            if input_category == "image" and output_category == "image":
                self._convert_image(input_path, output_path, conversion_request)
            elif input_category == "video" and output_category == "audio":
                self._extract_audio(input_path, output_path, conversion_request)
            elif input_category in ["video", "audio"]:
                self._convert_media_ffmpeg(input_path, output_path, conversion_request)
            else:
                raise Exception(f"Unsupported conversion: {input_category} to {output_category}")
            
            # Update completion status
            conversion_request.output_file = os.path.relpath(output_path, settings.MEDIA_ROOT)
            conversion_request.output_size = os.path.getsize(output_path)
            conversion_request.status = 'completed'
            conversion_request.progress = 100
            conversion_request.save()
            
            return output_path
            
        except Exception as e:
            logger.error(f"Conversion failed: {str(e)}")
            conversion_request.status = 'failed'
            conversion_request.error_message = str(e)
            conversion_request.save()
            raise e
    
    def _convert_image(self, input_path: str, output_path: str, conversion_request: ConversionRequest):
        """Convert image files, inspired by stillconvert"""
        try:
            # Update progress
            conversion_request.progress = 25
            conversion_request.save()
            
            stream = ffmpeg.input(input_path)
            stream = ffmpeg.output(stream, output_path, vframes=1)
            
            conversion_request.progress = 75
            conversion_request.save()
            
            ffmpeg.run(stream, overwrite_output=True, quiet=True)
            
        except ffmpeg.Error as e:
            logger.error(f"FFmpeg error in image conversion: {e.stderr}")
            raise Exception(f"Image conversion failed: {e.stderr}")
    
    def _extract_audio(self, input_path: str, output_path: str, conversion_request: ConversionRequest):
        """Extract audio from video, inspired by ExtractAudio"""
        try:
            conversion_request.progress = 10
            conversion_request.save()
            
            stream = ffmpeg.input(input_path)
            
            # Audio extraction options
            audio_options = {}
            if conversion_request.output_format == "mp3":
                audio_options['acodec'] = 'mp3'
                audio_options['audio_bitrate'] = '320k'
            elif conversion_request.output_format == "flac":
                audio_options['acodec'] = 'flac'
            elif conversion_request.output_format == "aac":
                audio_options['acodec'] = 'aac'
                audio_options['audio_bitrate'] = '256k'
            else:
                audio_options['acodec'] = 'copy'
            
            conversion_request.progress = 50
            conversion_request.save()
            
            stream = ffmpeg.output(stream, output_path, vn=None, **audio_options)
            ffmpeg.run(stream, overwrite_output=True, quiet=True)
            
        except ffmpeg.Error as e:
            logger.error(f"FFmpeg error in audio extraction: {e.stderr}")
            raise Exception(f"Audio extraction failed: {e.stderr}")
    
    def _convert_media_ffmpeg(self, input_path: str, output_path: str, conversion_request: ConversionRequest):
        """Convert video/audio files, inspired by convert and manualConvert"""
        try:
            conversion_request.progress = 10
            conversion_request.save()
            
            # Use hardware acceleration if available
            stream = ffmpeg.input(input_path, hwaccel='auto')
            
            output_options = {}
            
            # Quality-based encoding
            if conversion_request.output_quality == 'high':
                if conversion_request.output_format in ['mp4', 'mkv', 'avi']:
                    output_options.update({
                        'vcodec': 'libx264',
                        'crf': '18',
                        'preset': 'slow',
                        'acodec': 'aac',
                        'audio_bitrate': '320k'
                    })
                elif conversion_request.output_format in ['mp3', 'aac', 'm4a']:
                    output_options.update({
                        'acodec': 'aac' if conversion_request.output_format in ['aac', 'm4a'] else 'mp3',
                        'audio_bitrate': '320k'
                    })
            elif conversion_request.output_quality == 'medium':
                if conversion_request.output_format in ['mp4', 'mkv', 'avi']:
                    output_options.update({
                        'vcodec': 'libx264',
                        'crf': '23',
                        'preset': 'medium',
                        'acodec': 'aac',
                        'audio_bitrate': '192k'
                    })
                elif conversion_request.output_format in ['mp3', 'aac', 'm4a']:
                    output_options.update({
                        'acodec': 'aac' if conversion_request.output_format in ['aac', 'm4a'] else 'mp3',
                        'audio_bitrate': '192k'
                    })
            else:  # low quality
                if conversion_request.output_format in ['mp4', 'mkv', 'avi']:
                    output_options.update({
                        'vcodec': 'libx264',
                        'crf': '28',
                        'preset': 'fast',
                        'acodec': 'aac',
                        'audio_bitrate': '128k'
                    })
                elif conversion_request.output_format in ['mp3', 'aac', 'm4a']:
                    output_options.update({
                        'acodec': 'aac' if conversion_request.output_format in ['aac', 'm4a'] else 'mp3',
                        'audio_bitrate': '128k'
                    })
            
            conversion_request.progress = 30
            conversion_request.save()
            
            # Create output stream
            stream = ffmpeg.output(stream, output_path, **output_options)
            
            conversion_request.progress = 50
            conversion_request.save()
            
            # Run conversion with progress callback
            process = ffmpeg.run_async(stream, overwrite_output=True, quiet=True)
            
            # Simulate progress updates (in real implementation, you'd parse ffmpeg output)
            import time
            progress_steps = [60, 70, 80, 90, 95]
            for step in progress_steps:
                if process.poll() is None:  # Process still running
                    time.sleep(1)
                    conversion_request.progress = step
                    conversion_request.save()
                else:
                    break
            
            # Wait for completion
            process.wait()
            
            if process.returncode != 0:
                raise Exception("FFmpeg conversion failed")
                
        except ffmpeg.Error as e:
            logger.error(f"FFmpeg error in media conversion: {e.stderr}")
            raise Exception(f"Media conversion failed: {e.stderr}")
    
    def get_media_info(self, file_path: str) -> Dict[str, Any]:
        """Get media file information using ffprobe"""
        try:
            probe = ffmpeg.probe(file_path)
            
            info = {
                'duration': float(probe.get('format', {}).get('duration', 0)),
                'size': int(probe.get('format', {}).get('size', 0)),
                'bitrate': int(probe.get('format', {}).get('bit_rate', 0)),
                'format_name': probe.get('format', {}).get('format_name', ''),
                'streams': []
            }
            
            for stream in probe.get('streams', []):
                stream_info = {
                    'codec_type': stream.get('codec_type'),
                    'codec_name': stream.get('codec_name'),
                }
                
                if stream.get('codec_type') == 'video':
                    stream_info.update({
                        'width': stream.get('width'),
                        'height': stream.get('height'),
                        'fps': eval(stream.get('r_frame_rate', '0/1'))
                    })
                elif stream.get('codec_type') == 'audio':
                    stream_info.update({
                        'sample_rate': stream.get('sample_rate'),
                        'channels': stream.get('channels'),
                        'channel_layout': stream.get('channel_layout')
                    })
                
                info['streams'].append(stream_info)
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting media info: {str(e)}")
            return {}
    
    def estimate_conversion_time(self, file_size: int, input_format: str, output_format: str, quality: str) -> int:
        """Estimate conversion time in seconds based on file size and formats"""
        # Base time per MB (rough estimates)
        base_time_per_mb = {
            'high': 10,    # High quality takes longer
            'medium': 6,   # Medium quality
            'low': 3       # Low quality is faster
        }
        
        file_size_mb = file_size / (1024 * 1024)
        base_time = file_size_mb * base_time_per_mb.get(quality, 6)
        
        # Format-specific multipliers
        format_multiplier = 1.0
        if output_format in ['h265', 'av1']:
            format_multiplier = 2.0  # Newer codecs take longer
        elif output_format in ['flac']:
            format_multiplier = 0.5  # Lossless audio is faster
        
        return int(base_time * format_multiplier)
