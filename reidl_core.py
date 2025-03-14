import json
import os
import yt_dlp
import re
import glob
import time
import threading
import signal
import sys

def get_video_id(url):
    try:
        if 'youtube.com' in url:
            if 'v=' not in url:
                return None
            query = url.split('?')[-1]
            try:
                params = dict(param.split('=') for param in query.split('&') if '=' in param)
                return {'platform': 'youtube', 'id': params.get('v')}
            except:
                return None
        elif 'youtu.be' in url:
            return {'platform': 'youtube', 'id': url.split('/')[-1]}
        elif 'twitter.com' in url or 'x.com' in url:
            match = re.search(r'(?:twitter\.com|x\.com)/\w+/status/(\d+)', url)
            if match:
                return {'platform': 'twitter', 'id': match.group(1)}
        elif 'tiktok.com' in url:
            match = re.search(r'tiktok\.com/(?:@[\w.-]+/video/|video/)(\d+)', url)
            if match:
                return {'platform': 'tiktok', 'id': match.group(1)}
        return None
    except:
        return None

class ReiDLCore:
    def __init__(self):
        self.download_path = self.load_download_path()
        self.base_ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        self.current_download = None

    def load_download_path(self):
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                return config.get('download_path', os.path.expanduser("~/Downloads"))
        except (FileNotFoundError, json.JSONDecodeError):
            return os.path.expanduser("~/Downloads")

    def save_download_path(self, path):
        self.download_path = path
        
        config = {}
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        
        config['download_path'] = path
        
        with open('config.json', 'w') as f:
            json.dump(config, f)

    def get_next_available_filename(self, platform):
        base_name = {
            'youtube': 'ytdl',
            'twitter': 'xdl',
            'tiktok': 'ttkdl'
        }.get(platform, 'dl')
        
        existing_files = os.listdir(self.download_path)
        counter = 0
        
        while True:
            filename = f"{base_name}{counter if counter > 0 else ''}.mp4"
            if filename not in existing_files:
                return filename
            counter += 1

    def get_video_formats(self, url):
        video_info = get_video_id(url)
        if not video_info:
            return None, None
            
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'format': 'best',
            'youtube_include_dash_manifest': True,
            'nocheckcertificate': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                formats = info.get('formats', [])
                
                if video_info['platform'] in ['twitter', 'tiktok']:
                    return ["Best Quality"], ["Original Audio"]

                if not formats and 'format_id' in info:
                    formats = [info]

                video_formats = []
                seen_resolutions = set()
                audio_formats = []
                
                if not formats:
                    return ["720p HD", "480p", "360p"], ["High Quality Audio", "Medium Quality Audio"]
                
                for f in formats:
                    vcodec = f.get('vcodec', '')
                    if vcodec != 'none' and vcodec is not None:
                        height = f.get('height', 0) or 0
                        fps = f.get('fps', 0) or 0
                        filesize = f.get('filesize', 0) or f.get('filesize_approx', 0) or 0
                        
                        if height > 0 and height not in seen_resolutions:  
                            seen_resolutions.add(height)
                            
                            if height >= 2160:
                                quality = "4K"
                            elif height >= 1440:
                                quality = "2K"
                            elif height >= 1080:
                                quality = "1080p HD"
                            elif height >= 720:
                                quality = "720p HD"
                            elif height >= 480:
                                quality = "480p"
                            else:
                                quality = f"{height}p"
                            
                            if filesize > 0:
                                size_mb = filesize / (1024 * 1024)
                                if size_mb >= 1024:
                                    quality += f" (~{size_mb/1024:.1f}GB)"
                                else:
                                    quality += f" (~{size_mb:.0f}MB)"
                            
                            video_formats.append({
                                'quality': quality,
                                'height': height,
                                'fps': fps,
                                'format_id': f.get('format_id', '')
                            })
                    
                    acodec = f.get('acodec', '')
                    if acodec != 'none' and acodec is not None:
                        abr = f.get('abr', 0) or 0
                        
                        if abr > 0:
                            if abr >= 160:
                                quality = "High Quality Audio"
                            elif abr >= 128:
                                quality = "Medium Quality Audio"
                            else:
                                quality = "Low Quality Audio"
                            
                            audio_formats.append({
                                'quality': quality,
                                'abr': abr,
                                'format_id': f.get('format_id', '')
                            })
                
                if not video_formats:
                    video_formats = [
                        {'quality': '720p HD', 'height': 720, 'fps': 30, 'format_id': 'best[height<=720]'},
                        {'quality': '480p', 'height': 480, 'fps': 30, 'format_id': 'best[height<=480]'},
                        {'quality': '360p', 'height': 360, 'fps': 30, 'format_id': 'best[height<=360]'}
                    ]
                
                if not audio_formats:
                    audio_formats = [
                        {'quality': 'High Quality Audio', 'abr': 160, 'format_id': 'bestaudio'},
                        {'quality': 'Medium Quality Audio', 'abr': 128, 'format_id': 'bestaudio[abr<=128]'}
                    ]
                
                video_formats.sort(key=lambda x: x['height'], reverse=True)
                audio_formats.sort(key=lambda x: x['abr'], reverse=True)
                
                video_qualities = []
                seen_video = set()
                for f in video_formats:
                    if f['quality'] not in seen_video:
                        seen_video.add(f['quality'])
                        video_qualities.append(f['quality'])
                
                audio_qualities = []
                seen_audio = set()
                for f in audio_formats:
                    if f['quality'] not in seen_audio:
                        seen_audio.add(f['quality'])
                        audio_qualities.append(f['quality'])
                
                return video_qualities, audio_qualities
                
        except Exception as e:
            print(f"Error getting formats: {str(e)}")
            return ["720p HD", "480p", "360p"], ["High Quality Audio", "Medium Quality Audio"]

    def start_download(self, url, video_quality, audio_quality, progress_callback=None):
        video_info = get_video_id(url)
        if not video_info:
            return False
            
        output_filename = self.get_next_available_filename(video_info['platform'])
        output_path = os.path.join(self.download_path, output_filename)
        
        if video_info['platform'] in ['twitter', 'tiktok']:
            format_str = 'best'
        else:
            resolution = None
            if "4K" in video_quality:
                resolution = 2160
            elif "2K" in video_quality:
                resolution = 1440
            elif "1080p" in video_quality:
                resolution = 1080
            elif "720p" in video_quality:
                resolution = 720
            elif "480p" in video_quality:
                resolution = 480
            else:
                try:
                    resolution = int(video_quality.split('p')[0])
                except:
                    resolution = 720  
            
            audio_bitrate = None
            if "High Quality" in audio_quality:
                audio_bitrate = 160
            elif "Medium Quality" in audio_quality:
                audio_bitrate = 128
            else:
                audio_bitrate = 64
            
            format_str = (
                f'bestvideo[height<={resolution}]'
                f'+bestaudio[abr>={audio_bitrate}]/'
                f'best[height<={resolution}]/'
                f'best'
            )
        
        def wrapped_progress_hook(d):
            if 'filename' in d and self.current_download:
                self.current_download['partial_file'] = d['filename']
                
            if self.current_download and self.current_download.get('cancelled', False):
                print("Download cancelled, raising exception to stop download")
                raise Exception("Download cancelled")
                
            while self.current_download and self.current_download.get('paused', False):
                time.sleep(0.1)  
                
                if self.current_download and self.current_download.get('cancelled', False):
                    print("Download cancelled during pause, raising exception")
                    raise Exception("Download cancelled during pause")
            
            if progress_callback:
                progress_callback(d)
        
        ydl_opts = {
            'format': format_str,
            'outtmpl': output_path,
            'merge_output_format': 'mp4',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
            'prefer_ffmpeg': True,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,  
            'ignoreerrors': True,  
            'youtube_include_dash_manifest': True,
        }

        ydl_opts['progress_hooks'] = [wrapped_progress_hook]

        if video_info['platform'] == 'tiktok':
            ydl_opts.update({
                'extractor_args': {
                    'tiktok': {
                        'api_hostname': 'api16-normal-c-useast1a.tiktokv.com',
                        'app_version': '25.5.4',
                        'device_id': '7166715775973205509',
                    }
                }
            })
        
        self.current_download = {
            'cancelled': False,
            'paused': False,
            'output_path': output_path,
            'partial_file': None
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    error_code = ydl.download([url])
                    return error_code == 0 and not self.current_download['cancelled']
                except Exception as e:
                    if "Download cancelled" in str(e) or self.current_download['cancelled']:
                        print(f"Download was cancelled: {str(e)}")
                        self.current_download['cancelled'] = True
                        return False
                    else:
                        print(f"Download error: {str(e)}")
                        return False
        except Exception as e:
            print(f"YoutubeDL error: {str(e)}")
            return False

    def toggle_pause(self):
        if self.current_download:
            self.current_download['paused'] = not self.current_download['paused']
            return self.current_download['paused']
        return False

    def cancel_download(self):
        if self.current_download:
            print("Setting download as cancelled")
            self.current_download['cancelled'] = True
            self.current_download['paused'] = False
            
            time.sleep(1.0)
            
            try:
                if os.name == 'nt':
                    import subprocess
                    print("Attempting to kill ffmpeg processes")
                    subprocess.run(["taskkill", "/F", "/IM", "ffmpeg.exe"], 
                                  stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            except Exception as e:
                print(f"Error terminating processes: {str(e)}")
            
            self.cleanup_partial_downloads()
            return True
        return False

    def cleanup_partial_downloads(self):
        print("Starting cleanup of partial downloads...")
        
        if not self.current_download:
            print("No current download to clean up")
            return
            
        patterns_to_clean = []
        files_deleted = 0
        files_to_retry = []
        
        if 'output_path' in self.current_download:
            try:
                output_path = self.current_download['output_path']
                print(f"Checking for output file: {output_path}")
                
                if os.path.exists(output_path):
                    try:
                        os.remove(output_path)
                        files_deleted += 1
                        print(f"Deleted completed file: {output_path}")
                    except Exception as e:
                        print(f"Error deleting output file: {str(e)}")
                        files_to_retry.append(output_path)
            except Exception as e:
                print(f"Error checking output file: {str(e)}")
            
            try:
                base_path = os.path.splitext(self.current_download['output_path'])[0]
                base_dir = os.path.dirname(self.current_download['output_path'])
                
                patterns_to_clean.extend([
                    base_path + "*",                            
                    os.path.join(base_dir, "*.part"),           
                    os.path.join(base_dir, "*.temp"),           
                    os.path.join(base_dir, "*.download"),       
                    os.path.join(base_dir, "*.ytdl"),           
                    os.path.join(base_dir, "*.part.*"),         
                    os.path.join(base_dir, "*_part_*")          
                ])
                print(f"Added cleanup patterns based on output path: {base_path}")
            except Exception as e:
                print(f"Error setting up output path patterns: {str(e)}")
        
        if 'partial_file' in self.current_download and self.current_download['partial_file']:
            try:
                partial_file = self.current_download['partial_file']
                print(f"Checking for partial file: {partial_file}")
                
                if os.path.exists(partial_file):
                    try:
                        os.remove(partial_file)
                        files_deleted += 1
                        print(f"Deleted partial file: {partial_file}")
                    except Exception as e:
                        print(f"Error deleting partial file: {str(e)}")
                        files_to_retry.append(partial_file)
                
                partial_dir = os.path.dirname(partial_file)
                partial_base = os.path.splitext(os.path.basename(partial_file))[0]
                
                patterns_to_clean.extend([
                    os.path.join(partial_dir, partial_base + "*"),  
                    os.path.join(partial_dir, "*.part"),            
                    os.path.join(partial_dir, "*.temp"),            
                    os.path.join(partial_dir, "*.download")         
                ])
                print(f"Added cleanup patterns based on partial file: {partial_file}")
            except Exception as e:
                print(f"Error processing partial file: {str(e)}")
        
        try:
            patterns_to_clean.extend([
                os.path.join(self.download_path, "*.part"),
                os.path.join(self.download_path, "*.temp"),
                os.path.join(self.download_path, "*.download"),
                os.path.join(self.download_path, "*.ytdl")
            ])
            print(f"Added general download folder patterns")
        except Exception as e:
            print(f"Error adding general patterns: {str(e)}")
            
        for pattern in set(patterns_to_clean):  
            try:
                print(f"Searching for files with pattern: {pattern}")
                matching_files = glob.glob(pattern)
                print(f"Found {len(matching_files)} matching files")
                
                for file in matching_files:
                    if any(ext in file.lower() for ext in ['.part', '.temp', '.download', '.ytdl', '.webm.', '.m4a.']):
                        try:
                            print(f"Attempting to delete: {file}")
                            os.remove(file)
                            files_deleted += 1
                            print(f"Successfully deleted: {file}")
                        except Exception as e:
                            print(f"Error deleting file {file}: {str(e)}")
                            files_to_retry.append(file)
                    else:
                        print(f"Skipping non-temporary file: {file}")
            except Exception as e:
                print(f"Error processing pattern {pattern}: {str(e)}")
                
        if files_to_retry:
            print(f"Waiting to retry deletion for {len(files_to_retry)} files...")
            time.sleep(2)
            
            retry_deleted = 0
            for file in files_to_retry:
                try:
                    if os.path.exists(file):
                        print(f"Retrying deletion of: {file}")
                        os.remove(file)
                        retry_deleted += 1
                        files_deleted += 1
                        print(f"Successfully deleted on retry: {file}")
                except Exception as e:
                    print(f"Failed to delete on retry: {file}, Error: {str(e)}")
                    
                    try:
                        if os.name == 'nt' and os.path.exists(file):
                            print(f"Attempting forced deletion with Windows API: {file}")
                            import ctypes
                            if ctypes.windll.kernel32.DeleteFileW(file):
                                retry_deleted += 1
                                files_deleted += 1
                                print(f"Successfully deleted with Windows API: {file}")
                            else:
                                print(f"Windows API deletion failed: {file}")
                    except Exception as e:
                        print(f"Windows API deletion error: {str(e)}")
            
            print(f"Retry cleanup complete. Deleted {retry_deleted} additional files.")
        
        if os.name == 'nt' and files_to_retry:
            remaining_files = [f for f in files_to_retry if os.path.exists(f)]
            if remaining_files:
                print(f"Using Windows DEL command for {len(remaining_files)} stubborn files")
                for file in remaining_files:
                    try:
                        file_path = os.path.normpath(file)
                        import subprocess
                        subprocess.run(f'DEL /F /Q "{file_path}"', shell=True, 
                                      stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                        if not os.path.exists(file):
                            files_deleted += 1
                            print(f"Successfully deleted with DEL command: {file}")
                    except Exception as e:
                        print(f"DEL command failed for {file}: {str(e)}")
        
        print(f"Cleanup complete. Deleted {files_deleted} files.")
        return files_deleted > 0 