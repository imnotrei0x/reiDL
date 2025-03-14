import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import json
import os
import threading
from PIL import Image
import keyboard
import pystray
import time
import ctypes
from reidl_core import ReiDLCore, get_video_id
import win32gui
import win32con

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent = parent
        self.title("Settings")
        self.geometry("300x250")  
        
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
        
        self.transient(parent)
        self.grab_set()
        
        self.new_hotkey = parent.hotkey  
        
        self.old_hotkey = parent.hotkey
        if self.old_hotkey:
            try:
                keyboard.unhook_key(self.old_hotkey)
            except Exception:
                pass
        
        self.setup_ui()
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui(self):
        self.hotkey_frame = ctk.CTkFrame(self)
        self.hotkey_frame.pack(fill="x", padx=20, pady=20)
        
        self.hotkey_label = ctk.CTkLabel(self.hotkey_frame, 
                                       text=f"Current Hotkey: {self.parent.hotkey or 'None'}")
        self.hotkey_label.pack(pady=5)
        
        self.hotkey_btn = ctk.CTkButton(self.hotkey_frame, 
                                      text="Set Hotkey",
                                      command=self.start_hotkey_listen)
        self.hotkey_btn.pack(pady=5)
        
        self.save_btn = ctk.CTkButton(self,
                                    text="Save Settings",
                                    command=self.save_settings)
        self.save_btn.pack(pady=20)
        
        self.listening = False
        self.keyboard_listener = None
        self.mouse_listener = None

    def on_close(self):
        if self.listening:
            self.listening = False
            if self.keyboard_listener:
                try:
                    self.keyboard_listener.stop()
                except Exception:
                    pass
                self.keyboard_listener = None
                
            if self.mouse_listener:
                try:
                    self.mouse_listener.stop()
                except Exception:
                    pass
                self.mouse_listener = None
        
        if self.old_hotkey:
            try:
                keyboard.on_press_key(self.old_hotkey, self.parent.on_hotkey)
            except Exception:
                pass
                
        self.destroy()

    def start_hotkey_listen(self):
        if not self.listening:
            self.listening = True
            self.hotkey_btn.configure(text="Press any key or mouse button...")
            
            from pynput import mouse, keyboard as kb
            self.keyboard_listener = kb.Listener(on_press=self.on_key_press)
            self.mouse_listener = mouse.Listener(on_click=self.on_mouse_click)
            
            self.keyboard_listener.start()
            self.mouse_listener.start()

    def on_key_press(self, key):
        if self.listening:
            try:
                scan_code = getattr(key, 'scan_code', None)
                
                raw_name = str(key).replace("Key.", "").lower().strip("'")
                
                if len(raw_name) == 1:
                    key_name = raw_name
                else:
                    key_map = {
                        'esc': 'esc',
                        'space': 'space',
                        'enter': 'enter',
                        'tab': 'tab',
                        'backspace': 'backspace',
                        'delete': 'delete',
                        'up': 'up',
                        'down': 'down',
                        'left': 'left',
                        'right': 'right',
                        'home': 'home',
                        'end': 'end',
                        'page_up': 'page up',
                        'page_down': 'page down',
                        'insert': 'insert'
                    }
                    key_name = key_map.get(raw_name, raw_name)
                
                hotkey_data = {
                    'scan_code': scan_code,
                    'name': key_name
                }
                
                display_name = key_name
                if scan_code:
                    numpad_map = {
                        82: ("Numpad 0", "0"),
                        79: ("Numpad 1", "1"),
                        80: ("Numpad 2", "2"),
                        81: ("Numpad 3", "3"),
                        75: ("Numpad 4", "4"),
                        76: ("Numpad 5", "5"),
                        77: ("Numpad 6", "6"),
                        71: ("Numpad 7", "7"),
                        72: ("Numpad 8", "8"),
                        73: ("Numpad 9", "9"),
                        55: ("Numpad *", "*"),
                        78: ("Numpad +", "+"),
                        284: ("Numpad Enter", "enter"),
                        74: ("Numpad -", "-"),
                        83: ("Numpad .", "."),
                        53: ("Numpad /", "/")
                    }
                    
                    if scan_code in numpad_map:
                        display_name, key_name = numpad_map[scan_code]
                        hotkey_data['name'] = key_name
                
                self.set_hotkey(hotkey_data, display_name)
            except:
                pass

    def on_mouse_click(self, x, y, button, pressed):
        if self.listening and pressed:
            hotkey = str(button).replace("Button.", "mouse_")
            self.set_hotkey(hotkey)

    def set_hotkey(self, hotkey_data, display_name=None):
        if self.listening:
            self.listening = False
            if self.keyboard_listener:
                self.keyboard_listener.stop()
            if self.mouse_listener:
                self.mouse_listener.stop()
            
            self.new_hotkey = hotkey_data
            self.hotkey_label.configure(text=f"Current Hotkey: {display_name or hotkey_data['name']}")
            self.hotkey_btn.configure(text="Set Hotkey")

    def save_settings(self):
        if self.new_hotkey is not None:
            if isinstance(self.new_hotkey, dict) and 'name' in self.new_hotkey:
                self.parent.set_hotkey(self.new_hotkey)
        self.destroy()

class ReiDL(ctk.CTk):
    def __init__(self):
        self.hotkey = None
        self.hotkey_data = None
        self.hotkey_lock = threading.Lock()
        self.is_busy = False
        self.busy_lock = threading.Lock()  
        
        self.last_valid_url = None
        self.cached_video_formats = None
        self.cached_audio_formats = None
        self.url_base_id = None
        
        self.core = ReiDLCore()
        self.load_settings()
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        super().__init__()
        
        self.title("")
        self.geometry("800x250")
        self.resizable(False, False)
        
        self.setup_system_tray()
        
        if self.hotkey:
            keyboard.on_press_key(self.hotkey, self.on_hotkey)
        
        self.setup_window()
        self.setup_ui()

    def setup_window(self):
        try:
            icon_dir = os.path.dirname(__file__)
            png_path = os.path.join(icon_dir, "reidl.png")
            ico_path = os.path.join(icon_dir, "reidl.ico")
            
            if os.path.exists(png_path):
                icon_image = tk.PhotoImage(file=png_path)
                self.iconphoto(True, icon_image)
            
            if os.name == 'nt' and os.path.exists(ico_path):
                self.iconbitmap(ico_path)
                
                try:
                    myappid = "rei.reidl.1.0"
                    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
                except:
                    pass
                    
        except:
            pass
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.bg_color = "#2B2B2B"
        self.configure(fg_color=self.bg_color)
        
        self.attributes('-topmost', True)
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        if os.name == 'nt':
            hwnd = self.winfo_id()
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            style |= win32con.WS_MINIMIZEBOX
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
            
            self.bind("<Unmap>", self.on_minimize)

    def on_minimize(self, event=None):
        if self.state() == 'iconic':
            self.withdraw()
            return "break"

    def on_close(self):
        self.last_valid_url = None
        self.cached_video_formats = None
        self.cached_audio_formats = None
        self.url_base_id = None
        
        if hasattr(self, 'tray_icon'):
            self.tray_icon.stop()
        self.quit()

    def setup_ui(self):
        main_container = ctk.CTkFrame(self, fg_color=self.bg_color)
        main_container.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")  
        main_container.grid_columnconfigure(1, weight=1)
        
        header_frame = ctk.CTkFrame(main_container, fg_color=self.bg_color)
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)
        
        settings_btn = ctk.CTkButton(header_frame, 
                                   text="⚙️",
                                   width=30,
                                   height=30,
                                   command=self.open_settings)
        settings_btn.grid(row=0, column=0, sticky="w", padx=(0, 10))
        
        try:
            logo_path = os.path.join(os.path.dirname(__file__), "reidl.png")
            if os.path.exists(logo_path):
                logo_image = ctk.CTkImage(
                    light_image=Image.open(logo_path),
                    dark_image=Image.open(logo_path),
                    size=(60, 60)
                )
                logo_label = ctk.CTkLabel(header_frame, text="", image=logo_image)
                logo_label.grid(row=0, column=1, pady=(0, 10), sticky="")
        except Exception as e:
            print(f"Failed to load header logo: {str(e)}")
        
        header_frame.grid_columnconfigure(1, weight=1)
        
        url_frame = ctk.CTkFrame(main_container, fg_color=self.bg_color)
        url_frame.grid(row=1, column=0, columnspan=2, pady=(0, 10), sticky="ew")
        url_frame.grid_columnconfigure(1, weight=1)
        
        self.url_label = ctk.CTkLabel(url_frame, text="URL:", font=ctk.CTkFont(size=12))
        self.url_label.grid(row=0, column=0, padx=(5, 5))
        
        self.url_entry = ctk.CTkEntry(url_frame, height=30,
                                    placeholder_text="Paste YouTube, X/Twitter, or TikTok URL here")
        self.url_entry.grid(row=0, column=1, padx=5, sticky="ew")
        
        self.url_entry.bind('<KeyRelease>', self.on_url_change)
        self.url_entry.bind('<Control-v>', self.on_url_change)
        self.url_entry.bind('<<Paste>>', self.on_url_change)
        
        self.download_btn = ctk.CTkButton(url_frame, text="Download",
                                        width=80, height=30,
                                        font=ctk.CTkFont(size=12),
                                        command=self.start_download,
                                        state="disabled")
        self.download_btn.grid(row=0, column=2, padx=(5, 0))
        
        self.pause_btn = ctk.CTkButton(url_frame, text="Pause",
                                     width=70, height=30,
                                     font=ctk.CTkFont(size=12),
                                     command=self.toggle_pause,
                                     state="disabled")
        self.pause_btn.grid(row=0, column=3, padx=(5, 0))
        
        self.cancel_btn = ctk.CTkButton(url_frame, text="Cancel",
                                      width=70, height=30,
                                      font=ctk.CTkFont(size=12),
                                      command=self.cancel_download,
                                      state="disabled")
        self.cancel_btn.grid(row=0, column=4, padx=5)
        
        quality_frame = ctk.CTkFrame(main_container, fg_color=self.bg_color)
        quality_frame.grid(row=2, column=0, columnspan=2, pady=(0, 10), sticky="ew")
        quality_frame.grid_columnconfigure((0, 1), weight=1)
        
        video_label = ctk.CTkLabel(quality_frame, text="Video Quality",
                                 font=ctk.CTkFont(size=12))
        video_label.grid(row=0, column=0, padx=5, pady=(0, 2))
        
        self.video_quality_var = ctk.StringVar(value="Select Video Quality")
        self.video_quality_dropdown = ctk.CTkOptionMenu(quality_frame,
                                                      variable=self.video_quality_var,
                                                      values=["Select Video Quality"],
                                                      width=200,
                                                      height=28,
                                                      font=ctk.CTkFont(size=12))
        self.video_quality_dropdown.grid(row=1, column=0, padx=5)
        
        audio_label = ctk.CTkLabel(quality_frame, text="Audio Quality",
                                 font=ctk.CTkFont(size=12))
        audio_label.grid(row=0, column=1, padx=5, pady=(0, 2))
        
        self.audio_quality_var = ctk.StringVar(value="Select Audio Quality")
        self.audio_quality_dropdown = ctk.CTkOptionMenu(quality_frame,
                                                      variable=self.audio_quality_var,
                                                      values=["Select Audio Quality"],
                                                      width=200,
                                                      height=28,
                                                      font=ctk.CTkFont(size=12))
        self.audio_quality_dropdown.grid(row=1, column=1, padx=5)
        
        info_frame = ctk.CTkFrame(main_container, fg_color=self.bg_color)
        info_frame.grid(row=3, column=0, columnspan=2, sticky="ew")
        info_frame.grid_columnconfigure(0, weight=1)
        
        location_frame = ctk.CTkFrame(info_frame, fg_color=self.bg_color)
        location_frame.grid(row=0, column=0, sticky="ew")
        location_frame.grid_columnconfigure(0, weight=1)
        
        self.location_label = ctk.CTkLabel(location_frame,
                                         text=f"Save to: {self.core.download_path}",
                                         font=ctk.CTkFont(size=11))
        self.location_label.grid(row=0, column=0, padx=5, pady=2, sticky="w")
        
        self.browse_btn = ctk.CTkButton(location_frame, text="Browse",
                                      width=70, height=28,
                                      font=ctk.CTkFont(size=12),
                                      command=self.browse_location)
        self.browse_btn.grid(row=0, column=1, padx=5, pady=2)
        
        self.progress_label = ctk.CTkLabel(info_frame, text="",
                                         font=ctk.CTkFont(size=11))
        self.progress_label.grid(row=1, column=0, padx=5, pady=2, sticky="w")

    def update_ui_safely(self, **kwargs):
        self.after(0, lambda: self._update_ui(**kwargs))
    
    def _update_ui(self, **kwargs):
        if 'download_btn' in kwargs:
            btn_config = kwargs['download_btn']
            self.download_btn.configure(**btn_config)
        
        if 'progress_label' in kwargs:
            self.progress_label.configure(text=kwargs['progress_label'])
            
        if 'video_quality' in kwargs:
            self.video_quality_dropdown.configure(**kwargs['video_quality'])
            
        if 'audio_quality' in kwargs:
            self.audio_quality_dropdown.configure(**kwargs['audio_quality'])
            
        if 'video_quality_value' in kwargs:
            self.video_quality_var.set(kwargs['video_quality_value'])
            
        if 'audio_quality_value' in kwargs:
            self.audio_quality_var.set(kwargs['audio_quality_value'])

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            try:
                if 'filename' in d and self.core.current_download:
                    self.core.current_download['partial_file'] = d['filename']
                
                total_bytes = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
                downloaded_bytes = d.get('downloaded_bytes', 0)
                
                if downloaded_bytes > 0:
                    if total_bytes > 0:
                        percentage = (downloaded_bytes / total_bytes) * 100
                        
                        self.update_ui_safely(
                            download_btn={
                                'text': f"{percentage:.1f}%/{100}%",
                                'state': "disabled",
                                'fg_color': "#808080",
                                'text_color': "white"
                            },
                            progress_label=f"Downloaded: {downloaded_bytes/1024/1024:.1f}MB / {total_bytes/1024/1024:.1f}MB"
                        )
                    else:
                        self.update_ui_safely(
                            download_btn={
                                'text': f"Downloading...",
                                'state': "disabled",
                                'fg_color': "#808080",
                                'text_color': "white"
                            },
                            progress_label=f"Downloaded: {downloaded_bytes/1024/1024:.1f}MB"
                        )
            except Exception as e:
                if str(e) == "Download cancelled" or "cancelled" in str(e).lower():
                    raise e

    def on_url_change(self, event=None):
        if hasattr(self, '_url_check_after_id'):
            self.after_cancel(self._url_check_after_id)
        
        self._url_check_after_id = self.after(300, self._delayed_url_check)
    
    def _delayed_url_check(self):
        if hasattr(self, '_url_check_after_id'):
            delattr(self, '_url_check_after_id')
        
        self.check_and_fetch_url()

    def get_url_base_id(self, url):
        """Extract the base video ID to compare URLs"""
        video_info = get_video_id(url)
        if video_info:
            return f"{video_info['platform']}_{video_info['id']}"
        return None

    def check_and_fetch_url(self):
        url = self.url_entry.get().strip()
        
        url_base_id = self.get_url_base_id(url) if url else None
        
        if url and url_base_id:
            platform = url_base_id.split('_')[0] if '_' in url_base_id else None
            
            if self.url_base_id and '_' in self.url_base_id:
                cached_platform = self.url_base_id.split('_')[0]
                if platform and platform != cached_platform:
                    self.cached_video_formats = None
                    self.cached_audio_formats = None
                    print(f"Platform changed from {cached_platform} to {platform}, clearing cache")
            
            if url_base_id == self.url_base_id and self.cached_video_formats and self.cached_audio_formats:
                if not self.get_busy():
                    self.update_ui_safely(
                        video_quality={'values': self.cached_video_formats, 'state': "normal"},
                        audio_quality={'values': self.cached_audio_formats, 'state': "normal"},
                        video_quality_value=self.cached_video_formats[0],
                        audio_quality_value=self.cached_audio_formats[0],
                        download_btn={
                            'text': "Download",
                            'state': "normal",
                            'fg_color': "#2AAA8A"
                        },
                        progress_label=""
                    )
            else:
                self.set_busy(True)
                self.url_base_id = url_base_id
                self.update_ui_safely(
                    download_btn={
                        'text': "Fetching...",
                        'state': "disabled",
                        'fg_color': "#808080"
                    }
                )
                self.update_quality_options()
        elif url:
            self.update_ui_safely(
                download_btn={
                    'text': "Invalid URL",
                    'state': "disabled",
                    'fg_color': "#FF6B6B"
                },
                video_quality={'state': "disabled"},
                audio_quality={'state': "disabled"}
            )
        else:
            if self.cached_video_formats and self.cached_audio_formats:
                self.update_ui_safely(
                    download_btn={
                        'text': "Download",
                        'state': "disabled",
                        'fg_color': "#1f538d"
                    }
                )
            else:
                self.update_ui_safely(
                    download_btn={
                        'text': "Download",
                        'state': "disabled",
                        'fg_color': "#1f538d"
                    },
                    video_quality={'state': "disabled"},
                    audio_quality={'state': "disabled"}
                )

    def update_quality_options(self):
        url = self.url_entry.get().strip()
        if not url:
            self.set_busy(False)
            return
        
        url_base_id = self.get_url_base_id(url)
        
        if not url_base_id:
            self.set_busy(False)
            return
            
        current_platform = url_base_id.split('_')[0] if '_' in url_base_id else None
        if self.url_base_id and '_' in self.url_base_id:
            cached_platform = self.url_base_id.split('_')[0]
            if current_platform and current_platform != cached_platform:
                self.cached_video_formats = None
                self.cached_audio_formats = None
                print(f"Platform changed from {cached_platform} to {current_platform}, clearing cache in update options")
        
        if (url_base_id == self.url_base_id and 
            self.cached_video_formats and self.cached_audio_formats):
            self.set_busy(False)
            self.update_ui_safely(
                video_quality={'values': self.cached_video_formats, 'state': "normal"},
                audio_quality={'values': self.cached_audio_formats, 'state': "normal"},
                video_quality_value=self.cached_video_formats[0],
                audio_quality_value=self.cached_audio_formats[0],
                download_btn={
                    'text': "Download",
                    'state': "normal",
                    'fg_color': "#2AAA8A"
                },
                progress_label=""
            )
            return
        
        self.update_ui_safely(
            download_btn={
                'text': "Fetching formats...",
                'state': "disabled",
                'fg_color': "#808080"
            },
            video_quality={'state': "disabled"},
            audio_quality={'state': "disabled"},
            progress_label="Fetching available formats, please wait..."
        )
            
        def fetch_qualities():
            try:
                self.set_busy(True)
                
                current_url = url
                current_url_id = url_base_id
                current_platform = current_url_id.split('_')[0] if '_' in current_url_id else None
                
                self.update_ui_safely(
                    video_quality={'state': "disabled"},
                    audio_quality={'state': "disabled"}
                )
                
                video_qualities, audio_qualities = self.core.get_video_formats(url)
                
                url_after_fetch = self.url_entry.get().strip()
                
                if url_after_fetch == current_url and video_qualities and audio_qualities:
                    self.last_valid_url = current_url
                    self.cached_video_formats = video_qualities
                    self.cached_audio_formats = audio_qualities
                    self.url_base_id = current_url_id
                    
                    self.update_ui_safely(
                        video_quality={'values': video_qualities, 'state': "normal"},
                        audio_quality={'values': audio_qualities, 'state': "normal"},
                        video_quality_value=video_qualities[0],
                        audio_quality_value=audio_qualities[0],
                        download_btn={
                            'text': "Download",
                            'state': "normal",
                            'fg_color': "#2AAA8A"
                        },
                        progress_label=""
                    )
                    print(f"Updated cache for platform: {current_platform}")
                elif video_qualities and audio_qualities:
                    self.update_ui_safely(
                        video_quality={'values': video_qualities, 'state': "normal"},
                        audio_quality={'values': audio_qualities, 'state': "normal"},
                        video_quality_value=video_qualities[0],
                        audio_quality_value=audio_qualities[0],
                        download_btn={
                            'text': "Download",
                            'state': "normal",
                            'fg_color': "#2AAA8A"
                        },
                        progress_label=""
                    )
                    print(f"URL changed during fetch, not updating cache")
                else:
                    self.update_ui_safely(
                        download_btn={
                            'text': "No downloadable formats found",
                            'state': "disabled",
                            'fg_color': "#FF6B6B"
                        },
                        progress_label="No formats could be found for this URL."
                    )
            except Exception as e:
                print(f"Error fetching formats: {str(e)}")
                if self.url_entry.get().strip() == url:
                    self.update_ui_safely(
                        download_btn={
                            'text': "Error fetching formats",
                            'state': "disabled",
                            'fg_color': "#FF6B6B"
                        },
                        progress_label=f"Error: {str(e)}"
                    )
            finally:
                self.set_busy(False)
                
                if (not self.cached_video_formats or not self.cached_audio_formats) and self.url_entry.get().strip() == url:
                    self.update_ui_safely(
                        video_quality={'state': "disabled"},
                        audio_quality={'state': "disabled"}
                    )
                
        thread = threading.Thread(target=fetch_qualities, daemon=True)
        thread.start()

    def start_download(self):
        url = self.url_entry.get().strip()
        video_quality = self.video_quality_var.get()
        audio_quality = self.audio_quality_var.get()
        
        if not url or video_quality.startswith("Select") or audio_quality.startswith("Select"):
            self.update_ui_safely(
                download_btn={
                    'text': "Select Quality",
                    'state': "disabled",
                    'fg_color': "#FF6B6B"
                }
            )
            return
        
        self.set_busy(True)
        
        self.update_ui_safely(
            download_btn={
                'text': "Starting download...",
                'state': "disabled",
                'fg_color': "#808080"
            },
            progress_label="Preparing download..."
        )
        
        self.pause_btn.configure(state="normal")
        self.cancel_btn.configure(state="normal")
        
        def download_thread():
            try:
                success = self.core.start_download(
                    url, video_quality, audio_quality,
                    progress_callback=self.progress_hook
                )
                
                if success and not self.core.current_download['cancelled']:
                    self.update_ui_safely(
                        download_btn={
                            'text': "Download completed!",
                            'state': "disabled",
                            'fg_color': "#2AAA8A",
                            'text_color': "white"
                        },
                        progress_label="Download completed successfully!"
                    )
                else:
                    message = "Download cancelled" if self.core.current_download['cancelled'] else "Download failed"
                    self.update_ui_safely(
                        download_btn={
                            'text': "Error" if not self.core.current_download['cancelled'] else "Cancelled",
                            'state': "disabled",
                            'fg_color': "#FF6B6B",
                            'text_color': "white"
                        },
                        progress_label=message
                    )
            except Exception as e:
                self.update_ui_safely(
                    download_btn={
                        'text': "Error",
                        'state': "disabled",
                        'fg_color': "#FF6B6B",
                        'text_color': "white"
                    },
                    progress_label=f"Error: {str(e)}"
                )
            finally:
                self.pause_btn.configure(state="disabled")
                self.cancel_btn.configure(state="disabled")
                
                self.after(10, lambda: self.set_busy(False))
                
                self.after(2000, self.reset_controls)
        
        thread = threading.Thread(target=download_thread, daemon=True)
        thread.start()

    def toggle_pause(self):
        if not self.core.current_download:
            print("No active download to pause/resume")
            return False
            
        is_paused = self.core.toggle_pause()
        print(f"Download {'paused' if is_paused else 'resumed'}")
        
        if is_paused:
            self.pause_btn.configure(text="Continue", fg_color="#2AAA8A")
            self.download_btn.configure(text="PAUSED", fg_color="#808080", font=ctk.CTkFont(size=12, weight="bold"))
            self.update_ui_safely(
                progress_label="Download paused. Click 'Continue' to resume."
            )
        else:
            self.pause_btn.configure(text="Pause", fg_color="#1f538d")
            self.download_btn.configure(text="Resuming...", fg_color="#808080", font=ctk.CTkFont(size=12))
            self.update_ui_safely(
                progress_label="Download resuming..."
            )
        
        return is_paused

    def cancel_download(self):
        self.pause_btn.configure(state="disabled")
        self.cancel_btn.configure(state="disabled")
        
        self.update_ui_safely(
            download_btn={
                'text': "Cancelling...",
                'state': "disabled",
                'fg_color': "#FF6B6B",
                'text_color': "white"
            },
            progress_label="Cancelling download and cleaning up files..."
        )
        
        if self.core.cancel_download():
            self.set_busy(False)
            
            self.after(100, lambda: self.update_ui_safely(
                progress_label="Removing partial download files..."
            ))
            
            self.after(2000, lambda: self.update_ui_safely(
                download_btn={
                    'text': "Cancelled",
                    'state': "disabled",
                    'fg_color': "#FF6B6B",
                    'text_color': "white"
                },
                progress_label="Download cancelled and temporary files removed."
            ))
            
            self.after(4000, self.reset_controls)
        else:
            self.update_ui_safely(
                download_btn={
                    'text': "Error",
                    'state': "disabled",
                    'fg_color': "#FF6B6B",
                    'text_color': "white"
                },
                progress_label="Failed to cancel download."
            )
            
            self.pause_btn.configure(state="normal")
            self.cancel_btn.configure(state="normal")

    def reset_controls(self):
        self.update_ui_safely(
            download_btn={
                'text': "Download",
                'state': "normal",
                'fg_color': "#2AAA8A",
                'text_color': "white"
            }
        )
        
        self.pause_btn.configure(state="disabled", text="Pause", fg_color="#1f538d")
        self.cancel_btn.configure(state="disabled")
        
        self.url_entry.delete(0, 'end')
        
        if self.cached_video_formats and self.cached_audio_formats:
            self.update_ui_safely(
                video_quality={'values': self.cached_video_formats, 'state': "normal"},
                audio_quality={'values': self.cached_audio_formats, 'state': "normal"},
                video_quality_value=self.cached_video_formats[0],
                audio_quality_value=self.cached_audio_formats[0],
                download_btn={
                    'text': "Download",
                    'state': "disabled", 
                    'fg_color': "#1f538d"
                }
            )
        else:
            self.video_quality_var.set("Select Video Quality")
            self.audio_quality_var.set("Select Audio Quality")
            self.video_quality_dropdown.configure(state="disabled")
            self.audio_quality_dropdown.configure(state="disabled")

    def browse_location(self):
        path = filedialog.askdirectory()
        if path:
            self.core.save_download_path(path)
            self.location_label.configure(text=f"Save to: {path}")

    def load_settings(self):
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                
                self.hotkey_data = config.get('hotkey_data')
                
                if not self.hotkey_data and 'hotkey' in config:
                    old_hotkey = config.get('hotkey')
                    if old_hotkey:
                        self.hotkey_data = {
                            'name': old_hotkey,
                            'scan_code': None
                        }
                
                if isinstance(self.hotkey_data, dict) and 'name' in self.hotkey_data:
                    self.hotkey = self.hotkey_data['name']
                else:
                    self.hotkey_data = None
                    self.hotkey = None
                    
        except (FileNotFoundError, json.JSONDecodeError):
            self.hotkey_data = None
            self.hotkey = None

    def save_settings(self):
        config = {}
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
        except:
            pass
        
        config.pop('hotkey', None)
        config.pop('original_hotkey', None)
        
        if self.hotkey_data:
            config['hotkey_data'] = {
                'name': self.hotkey_data['name'],
                'scan_code': self.hotkey_data.get('scan_code')
            }
        else:
            config.pop('hotkey_data', None)
        
        with open('config.json', 'w') as f:
            json.dump(config, f)

    def set_hotkey(self, hotkey_data):
        if hotkey_data is None:
            return
            
        if self.hotkey:
            try:
                keyboard.unhook_key(self.hotkey)
            except Exception:
                pass
        
        if not isinstance(hotkey_data, dict) or 'name' not in hotkey_data or not hotkey_data['name']:
            self.hotkey_data = None
            self.hotkey = None
            self.save_settings()
            return
        
        self.hotkey_data = hotkey_data
        self.hotkey = hotkey_data['name']
        
        try:
            try:
                keyboard.unhook_key(self.hotkey)
            except Exception:
                pass
            
            keyboard.on_press_key(self.hotkey, self.on_hotkey)
            self.save_settings()
        except Exception as e:
            print(f"Error setting hotkey: {str(e)}")
            self.hotkey_data = None
            self.hotkey = None
            self.save_settings()

    def on_hotkey(self, e):
        with self.hotkey_lock:
            is_busy = self.get_busy()
            downloading = is_busy and hasattr(self, 'download_btn') and 'Downloading' in self.download_btn.cget('text')
            
            if downloading and not self.core.current_download['paused']:
                return
            
            if self.hotkey_data and 'scan_code' in self.hotkey_data and self.hotkey_data['scan_code']:
                if e.scan_code != self.hotkey_data['scan_code']:
                    return
            
            if self.state() == 'iconic' or not self.winfo_viewable():
                self.deiconify()
                self.after(10, self._ensure_topmost)
            else:
                self.withdraw()

    def show_window(self, icon=None, item=None):
        self.deiconify()
        self.after(10, self._ensure_topmost)

    def _ensure_topmost(self):
        if self.state() != 'withdrawn':
            hwnd = self.winfo_id()
            rect = win32gui.GetWindowRect(hwnd)
            x, y, w, h = rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1]
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, x, y, w, h, 
                                win32con.SWP_SHOWWINDOW)
            self.focus_force()
            self.attributes('-topmost', True)

    def setup_system_tray(self):
        icon_path = os.path.join(os.path.dirname(__file__), "reidl.png")
        if os.path.exists(icon_path):
            icon = Image.open(icon_path)
            menu = (pystray.MenuItem("Show", self.show_window),
                   pystray.MenuItem("Exit", self.quit_app))
            self.tray_icon = pystray.Icon("reiDL", icon, "reiDL", menu)
            
            threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def quit_app(self, icon=None, item=None):
        if hasattr(self, 'tray_icon'):
            self.tray_icon.stop()
        self.quit()

    def open_settings(self):
        settings_window = SettingsWindow(self)
        settings_window.focus()

    def iconify(self):
        """Override iconify to withdraw to system tray instead"""
        self.withdraw()

    def protocol(self, name, func):
        """Override protocol to handle window events"""
        if name == "WM_DELETE_WINDOW":
            super().protocol(name, func)
        elif name == "WM_ICONIFY":
            pass
        else:
            super().protocol(name, func)

    def set_busy(self, busy_state):
        """Thread-safe method to set the busy state"""
        with self.busy_lock:
            self.is_busy = busy_state
            
    def get_busy(self):
        """Thread-safe method to get the busy state"""
        with self.busy_lock:
            return self.is_busy
            
    def reset_busy_state(self):
        """Can be called to force reset the busy state if UI gets stuck"""
        self.set_busy(False)
        self.update_ui_safely(
            download_btn={
                'text': "Download",
                'state': "normal", 
                'fg_color': "#2AAA8A"
            },
            progress_label=""
        )

if __name__ == "__main__":
    app = ReiDL()
    app.mainloop() 