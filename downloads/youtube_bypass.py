import os
import time
import random
from typing import Dict, Any
import yt_dlp
import logging

logger = logging.getLogger(__name__)

class YouTubeBypassHelper:
    """Helper class with advanced YouTube bot detection bypass techniques"""
    
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0',
        ]
    
    def get_random_user_agent(self) -> str:
        """Get a random user agent"""
        return random.choice(self.user_agents)
    
    def get_base_ydl_opts(self, for_download: bool = False) -> Dict[str, Any]:
        """Get base yt-dlp options with advanced anti-detection measures"""
        opts = {
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'nocheckcertificate': True,
            'format': 'all' if not for_download else 'best',  # Get ALL formats for info extraction
            'merge_output_format': 'mp4',
            'prefer_ffmpeg': True,  # Enable ffmpeg for format merging
            
            # Random user agent
            'user_agent': self.get_random_user_agent(),
            
            # Headers to mimic real browser
            'headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
            },
            
            # Reduce requests and complexity
            'extract_flat': False,
            'force_json': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'writedescription': False,
            'writeinfojson': False,
            'writethumbnail': False,
            
            # Enhanced YouTube-specific anti-detection - PRIORITIZE iOS FOR HIGH QUALITY
            'extractor_args': {
                'youtube': {
                    'skip': [],  # CRITICAL: Don't skip DASH, HLS formats
                    'player_skip': [],  # Don't skip anything 
                    'player_client': ['ios', 'web'],  # iOS FIRST for high quality, then web fallback
                    'comment_sort': ['top'],
                    'max_comments': [0],
                    'include_dash_manifest': True,  # Include DASH for separate streams
                    'include_hls_manifest': True,   # Include HLS for additional formats
                }
            },
            
            # Additional anti-detection measures
            'geo_bypass': True,
            'geo_bypass_country': 'US',
            'age_limit': 18,
            'sleep_interval': random.uniform(1, 3),
            'max_sleep_interval': 5,
        }
        
        if not for_download:
            opts['skip_download'] = True
            
        return opts
    
    def extract_video_info_with_retry(self, url: str, max_retries: int = 5) -> Dict[str, Any]:
        """Extract video info with multiple aggressive retry strategies to get all formats"""
        strategies = [
            # Strategy 1: Web client with specific format extraction
            {
                'extractor_args': {
                    'youtube': {
                        'player_client': ['web'],
                        'skip': [],  # Don't skip any formats
                    }
                },
                'format': 'all',  # Extract all available formats
                'listformats': False,  # Don't list, just extract
            },
            # Strategy 2: Try with different user agent and format listing
            {
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'extractor_args': {
                    'youtube': {
                        'player_client': ['web'],
                        'skip': [],
                    }
                },
                'format': 'bestvideo+bestaudio/best',  # Try to get separate streams
            },
            # Strategy 3: Android client for different format set
            {
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android'],
                        'skip': [],
                    }
                },
                'format': 'all',
            },
            # Strategy 4: Try with cookies for authenticated access
            {
                'cookiesfrombrowser': ('chrome',),
                'extractor_args': {
                    'youtube': {
                        'player_client': ['web'],
                        'skip': [],
                    }
                },
                'format': 'all',
            },
            # Strategy 5: Force different extraction method
            {
                'quiet': False,  # See what's happening
                'format': 'all',
                'extract_flat': False,
            }
        ]
        
        for attempt in range(max_retries):
            try:
                # Add delay between attempts
                if attempt > 0:
                    delay = random.uniform(3, 8) * (attempt + 1)
                    logger.info(f"Retry attempt {attempt + 1} after {delay:.1f}s delay")
                    time.sleep(delay)
                
                # Get base options
                if attempt < len(strategies):
                    ydl_opts = self.get_base_ydl_opts()
                    # Merge strategy-specific options
                    ydl_opts.update(strategies[attempt])
                else:
                    # Fallback to base options with random user agent
                    ydl_opts = self.get_base_ydl_opts()
                    ydl_opts['user_agent'] = self.get_random_user_agent()
                
                logger.info(f"Attempting extraction with strategy {attempt + 1}: {ydl_opts.get('extractor_args', {}).get('youtube', {}).get('player_client', ['default'])}")
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    if info:
                        logger.info(f"Successfully extracted video info on attempt {attempt + 1}")
                        return info
                    
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    logger.error(f"All {max_retries} attempts failed for URL: {url}")
                    raise e
        
        return None
    
    def download_with_fallback(self, url: str, ydl_opts: Dict[str, Any]) -> bool:
        """Download with fallback strategies"""
        base_opts = self.get_base_ydl_opts(for_download=True)
        final_opts = {**base_opts, **ydl_opts}
        
        strategies = [
            # Strategy 1: Standard options
            final_opts,
            
            # Strategy 2: Force mp4 format
            {**final_opts, 'format': 'best[ext=mp4]/best'},
            
            # Strategy 3: Lower quality
            {**final_opts, 'format': 'worst[height>=360]/worst'},
            
            # Strategy 4: Audio only as fallback
            {**final_opts, 'format': 'bestaudio/best'},
        ]
        
        for i, opts in enumerate(strategies):
            try:
                logger.info(f"Trying download strategy {i + 1}")
                
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url])
                    return True
                    
            except Exception as e:
                logger.warning(f"Download strategy {i + 1} failed: {str(e)}")
                
                # Add delay between strategies
                if i < len(strategies) - 1:
                    time.sleep(random.uniform(1, 3))
        
        return False
    
    def download_with_retry(self, url, ydl_opts):
        """
        Download a video with retry logic using different strategies
        Returns the download result
        """
        strategies = self._get_download_strategies(ydl_opts.copy())
        
        for i, opts in enumerate(strategies):
            try:
                logger.info(f"Trying download strategy {i + 1}/{len(strategies)}")
                
                with yt_dlp.YoutubeDL(opts) as ydl:
                    result = ydl.download([url])
                    logger.info(f"Download strategy {i + 1} succeeded")
                    return result
                    
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Download strategy {i + 1} failed: {error_msg}")
                
                # If it's a format-specific error and we're using a combined format, try fallback
                if '+' in ydl_opts.get('format', '') and ('format' in error_msg.lower() or 'not available' in error_msg.lower()):
                    logger.info("Combined format failed, trying fallback to best available format")
                    try:
                        fallback_opts = opts.copy()
                        fallback_opts['format'] = 'best'
                        with yt_dlp.YoutubeDL(fallback_opts) as ydl_fallback:
                            result = ydl_fallback.download([url])
                            logger.info("Fallback to best format succeeded")
                            return result
                    except Exception as fallback_error:
                        logger.warning(f"Fallback also failed: {fallback_error}")
                
                # Add delay between strategies
                if i < len(strategies) - 1:
                    time.sleep(random.uniform(2, 4))
        
        # If all strategies failed, raise the last exception
        raise Exception("All download strategies failed - YouTube may be blocking requests")
    
    def _get_download_strategies(self, base_opts):
        """
        Get different download strategies with varying configurations
        """
        strategies = []
        
        # Strategy 1: Android client with cookies
        strategy1 = base_opts.copy()
        strategy1.update({
            'http_headers': {
                'User-Agent': 'com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
            },
            'extractor_args': {
                'youtube': {
                    'player_client': ['android'],
                    'player_skip': ['webpage']
                }
            }
        })
        strategies.append(strategy1)
        
        # Strategy 2: Android Creator Studio client
        strategy2 = base_opts.copy()
        strategy2.update({
            'http_headers': {
                'User-Agent': 'com.google.android.apps.youtube.creator/22.30.100 (Linux; U; Android 11) gzip',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
            },
            'extractor_args': {
                'youtube': {
                    'player_client': ['android_creator'],
                }
            }
        })
        strategies.append(strategy2)
        
        # Strategy 3: Web client with enhanced headers
        strategy3 = base_opts.copy()
        strategy3.update({
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
            },
            'extractor_args': {
                'youtube': {
                    'player_client': ['web'],
                }
            }
        })
        strategies.append(strategy3)
        
        # Strategy 4: Mobile web client
        strategy4 = base_opts.copy()
        strategy4.update({
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
            },
            'extractor_args': {
                'youtube': {
                    'player_client': ['mweb'],
                }
            }
        })
        strategies.append(strategy4)
        
        # Strategy 5: Minimal options as last resort
        strategy5 = {
            'format': base_opts.get('format', 'best'),
            'outtmpl': base_opts.get('outtmpl'),
            'retries': 5,
            'fragment_retries': 5,
            'skip_unavailable_fragments': True,
            'http_headers': {
                'User-Agent': 'yt-dlp/2025.07.21',
            }
        }
        strategies.append(strategy5)
        
        return strategies
