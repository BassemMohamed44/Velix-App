"""
╔══════════════════════════════════════════════════════════╗
║                  VELIX - Video Downloader                ║
║                       Version 2.1.2                      ║
║             Developed by: Bassem Mohamed                 ║
╚══════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import logging
import threading
import webbrowser
import concurrent.futures
import ctypes
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path
import requests
import tkinter as tk
import customtkinter as ctk
from PIL import Image
import yt_dlp

# ══════════════════════════════════════════════════════════
#  LOGGING SETUP
# ══════════════════════════════════════════════════════════
log_path = os.path.join(os.environ.get("APPDATA", str(Path.home())), "Velix", "velix.log")
os.makedirs(os.path.dirname(log_path), exist_ok=True)

logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ══════════════════════════════════════════════════════════
#  A. CONSTANTS & CONFIGURATION
# ══════════════════════════════════════════════════════════
UPDATE_URL    = "https://raw.githubusercontent.com/BassemMohamed44/latest_version/main/latest_version.json"
APP_NAME      = "Velix"
APP_VERSION   = "2.1.2"
PARALLEL_WORKERS = 3 

WINDOW_WIDTH  = 850
WINDOW_HEIGHT = 800
SIDEBAR_WIDTH = 250
SIDEBAR_X_HIDDEN  = WINDOW_WIDTH
SIDEBAR_X_VISIBLE = WINDOW_WIDTH - SIDEBAR_WIDTH
SIDEBAR_Y_OFFSET  = 60

THEME_COLOR   = "#9d00ff"
THEME_HOVER   = "#6a0dad"
BG_COLOR      = "#0f0f13"
CARD_COLOR    = "#1c1c24"
INPUT_BG      = "#1a1c23"
INPUT_FIELD   = "#2d2f39"

_APPDATA_DIR  = os.path.join(os.environ.get("APPDATA", str(Path.home())), "Velix")
os.makedirs(_APPDATA_DIR, exist_ok=True)
SETTINGS_FILE = os.path.join(_APPDATA_DIR, "Velix_settings.json")

QUALITY_OPTIONS = [
    "Best Quality (Auto)",
    "1080p", "720p", "480p", "360p", "144p",
    "Audio Only (MP3)"
]

class FontConfig:
    FAMILY  = "Segoe UI"
    SMALL   = (FAMILY, 12)
    BOLD_SM = (FAMILY, 12, "bold")
    MEDIUM  = (FAMILY, 14)
    LARGE   = (FAMILY, 16)
    BOLD_LG = (FAMILY, 16, "bold")
    XLARGE  = (FAMILY, 22, "bold")

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ══════════════════════════════════════════════════════════
#  B. UTILITY FUNCTIONS
# ══════════════════════════════════════════════════════════
def resource_path(relative_path: str) -> str:
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def get_ffmpeg_dir() -> str:
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        candidates = [
            exe_dir,
            os.path.join(exe_dir, '_internal'),
            os.path.join(exe_dir, 'ffmpeg'),
        ]
        for path in candidates:
            if os.path.exists(os.path.join(path, 'ffmpeg.exe')):
                logging.info(f"Found ffmpeg in: {path}")
                return path
        logging.error("ffmpeg.exe not found in any expected location!")
        return exe_dir
    else:
        return os.path.abspath(".")


def get_icon_path() -> str:

    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        candidates = [
            exe_dir,
            os.path.join(exe_dir, '_internal'),
        ]
        for path in candidates:
            full = os.path.join(path, 'VelixNew_fixed.ico')
            if os.path.exists(full):
                logging.info(f"Found icon in: {full}")
                return full
        logging.error("VelixNew_fixed.ico not found!")
        return os.path.join(exe_dir, 'VelixNew_fixed.ico')
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            script_dir,
            os.path.join(script_dir, 'pyarmor_runtime_0'),
            os.getcwd(),
        ]
        for path in candidates:
            full = os.path.join(path, 'VelixNew_fixed.ico')
            if os.path.exists(full):
                logging.info(f"Found icon in: {full}")
                return full
        
        return os.path.join(script_dir, 'VelixNew_fixed.ico')


def version_tuple(version: str) -> tuple:
    if not version:
        return (0, 0, 0)
    try:
        return tuple(map(int, version.split(".")))
    except ValueError:
        return (0, 0, 0)


def format_duration(seconds) -> str:
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return "--:--"
    mins, secs = divmod(seconds, 60)
    return f"{mins:02d}:{secs:02d}"


# ══════════════════════════════════════════════════════════
#  C. SETTINGS MANAGER
# ══════════════════════════════════════════════════════════
class SettingsManager:

    DEFAULT_SETTINGS = {
        "download_path": str(Path.home() / "Downloads"),
        "history": []
    }

    def __init__(self):
        self.settings = dict(self.DEFAULT_SETTINGS)
        self._load()

    def _load(self):
        if not os.path.exists(SETTINGS_FILE):
            return
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                self.settings.update(json.load(f))
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in settings file: {e}")
        except OSError as e:
            logging.error(f"Failed to load settings: {e}")

    def save(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
        except OSError as e:
            logging.error(f"Error saving settings: {e}")

    def get_path(self) -> str:
        return self.settings.get("download_path", self.DEFAULT_SETTINGS["download_path"])

    def set_path(self, path: str):
        self.settings["download_path"] = path
        self.save()

    def add_to_history(self, entry: dict):
        entry.setdefault("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M"))
        history = self.settings.setdefault("history", [])
        history.append(entry)
        if len(history) > 200:
            self.settings["history"] = history[-200:]
        self.save()

    def get_history(self) -> list:
        return list(reversed(self.settings.get("history", [])))

    def clear_history(self):
        self.settings["history"] = []
        self.save()


# ══════════════════════════════════════════════════════════
#  D. DOWNLOAD ENGINE
# ══════════════════════════════════════════════════════════
def _detect_platform(url: str) -> str:
    url_lower = url.lower()
    if any(d in url_lower for d in ["twitter.com", "x.com", "t.co"]):
        return "twitter"
    if "instagram.com" in url_lower:
        return "instagram"
    if "tiktok.com" in url_lower:
        return "tiktok"
    if "reddit.com" in url_lower or "redd.it" in url_lower:
        return "reddit"
    if "facebook.com" in url_lower or "fb.watch" in url_lower:
        return "facebook"
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    return "generic"


class DownloadEngine:

    def __init__(self, on_progress, on_log, on_finished):
        self.on_progress = on_progress
        self.on_log      = on_log
        self.on_finished = on_finished
        self.is_active   = False
        self.stop_flag   = threading.Event()
        self._ffmpeg_dir = get_ffmpeg_dir()

        logging.info(f"ffmpeg dir: {self._ffmpeg_dir}")
        logging.info(f"ffmpeg.exe exists: {os.path.exists(os.path.join(self._ffmpeg_dir, 'ffmpeg.exe'))}")

    def _base_opts(self) -> dict:
        return {
            "quiet": True,
            "nocheckcertificate": True,
            "ffmpeg_location": self._ffmpeg_dir,
        }

    _COOKIE_BROWSERS = ["chrome", "edge", "firefox", "brave", "opera", "vivaldi", "chromium"]

    def _find_twitter_cookies(self) -> str | None:
        """
        Return the name of the first installed browser whose cookie store
        exists on disk.  yt-dlp will pull Twitter cookies from it at runtime.
        Returns None when no supported browser is found.
        """
        appdata   = os.environ.get("APPDATA", "")
        localdata = os.environ.get("LOCALAPPDATA", "")
        home      = str(Path.home())

        cookie_hints = {
            "chrome":   [
                os.path.join(localdata, "Google", "Chrome", "User Data", "Default", "Cookies"),
                os.path.join(home, ".config", "google-chrome", "Default", "Cookies"),
                os.path.join(home, "Library", "Application Support", "Google", "Chrome", "Default", "Cookies"),
            ],
            "edge":     [
                os.path.join(localdata, "Microsoft", "Edge", "User Data", "Default", "Cookies"),
                os.path.join(home, ".config", "microsoft-edge", "Default", "Cookies"),
            ],
            "firefox":  [
                os.path.join(appdata, "Mozilla", "Firefox", "Profiles"),
                os.path.join(home, ".mozilla", "firefox"),
                os.path.join(home, "Library", "Application Support", "Firefox", "Profiles"),
            ],
            "brave":    [
                os.path.join(localdata, "BraveSoftware", "Brave-Browser", "User Data", "Default", "Cookies"),
                os.path.join(home, ".config", "BraveSoftware", "Brave-Browser", "Default", "Cookies"),
            ],
            "opera":    [
                os.path.join(appdata, "Opera Software", "Opera Stable", "Cookies"),
                os.path.join(home, ".config", "opera", "Cookies"),
            ],
            "vivaldi":  [
                os.path.join(localdata, "Vivaldi", "User Data", "Default", "Cookies"),
                os.path.join(home, ".config", "vivaldi", "Default", "Cookies"),
            ],
            "chromium": [
                os.path.join(localdata, "Chromium", "User Data", "Default", "Cookies"),
                os.path.join(home, ".config", "chromium", "Default", "Cookies"),
            ],
        }

        for browser in self._COOKIE_BROWSERS:
            for path in cookie_hints.get(browser, []):
                if os.path.exists(path):
                    return browser
        return None

    def _platform_opts(self, url: str) -> dict:
        platform = _detect_platform(url)

        common_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        }

        if platform == "twitter":
            opts = {
                "http_headers": {
                    **common_headers,
                    "Accept-Language": "en-US,en;q=0.9",
                },
                "noplaylist": True,
            }
            cookie_browser = self._find_twitter_cookies()
            if cookie_browser:
                opts["cookiesfrombrowser"] = (cookie_browser,)
                logging.info(f"Twitter: using cookies from {cookie_browser}")
            else:
                logging.warning("Twitter: no browser cookies found — download may fail for auth-required tweets.")
            return opts

        if platform == "instagram":
            return {
                "http_headers": common_headers,
                "noplaylist": True,
            }

        if platform == "tiktok":
            return {
                "http_headers": common_headers,
                "noplaylist": True,
            }

        if platform == "reddit":
            return {
                "http_headers": common_headers,
                "noplaylist": True,
            }

        if platform == "facebook":
            return {
                "http_headers": common_headers,
                "noplaylist": True,
            }

        return {
            "noplaylist": True,
        }

    def fetch_info(self, url: str) -> dict:
        opts = {
            **self._base_opts(),
            **self._platform_opts(url),
            "skip_download": True,
            "ignoreerrors":  False,  
            "extract_flat":  False,
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info is None:
                    raise ValueError("Unsupported URL or private content.")
                if info.get("_type") == "playlist":
                    entries = info.get("entries") or []
                    entries = [e for e in entries if e]
                    if not entries:
                        raise ValueError("No downloadable content found.")
                    info = entries[0]
                return info
        except yt_dlp.utils.DownloadError as e:
            logging.error(f"yt-dlp error during fetch: {e}")
            err_msg = str(e)
            if "twitter" in err_msg.lower() or "x.com" in err_msg.lower():
                raise RuntimeError(
                    "Could not fetch Twitter/X video. "
                    "The tweet may be private, age-restricted, or the link is incorrect."
                )
            raise RuntimeError("Invalid or unsupported link.")
        except ValueError as e:
            raise RuntimeError(str(e))
        except Exception as e:
            logging.error(f"Unexpected error in fetch_info: {e}")
            raise RuntimeError("Something went wrong while analyzing the link.")

    def _build_format_string(self, format_choice: str, platform: str) -> str:
        SINGLE_STREAM_PLATFORMS = {"twitter", "instagram", "tiktok", "reddit", "facebook"}
        is_single = platform in SINGLE_STREAM_PLATFORMS

        if format_choice == "Audio Only (MP3)":
            return "bestaudio/best"

        if format_choice == "Best Quality (Auto)":
            if is_single:
                return "best"
            return "bestvideo+bestaudio/best"

        res = format_choice.replace("p", "")
        if is_single:
            return f"best[height<={res}]/best"
        return (
            f"bestvideo[height<={res}]+bestaudio"
            f"/best[height<={res}]"
            f"/bestvideo[height<={res}]/best"
        )

    def _build_opts(self, url: str, output_path: str, format_choice: str,
                    custom_name: str = None) -> dict:
        platform = _detect_platform(url)
        if custom_name and custom_name.strip():
            safe = "".join(c for c in custom_name.strip() if c not in r'\/:*?"<>|')
            template = os.path.join(output_path, f"{safe}.%(ext)s")
        else:
            template = os.path.join(output_path, "%(title)s.%(ext)s")
        base = {
            **self._base_opts(),
            **self._platform_opts(url),
        }

        fmt = self._build_format_string(format_choice, platform)

        if format_choice == "Audio Only (MP3)":
            return {
                **base,
                "format": fmt,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
                "outtmpl": template,
                "progress_hooks": [self._progress_hook],
            }

        return {
            **base,
            "format": fmt,
            "merge_output_format": "mp4",
            "outtmpl": template,
            "progress_hooks": [self._progress_hook],
            "keepvideo": False,
        }

    def download(self, url: str, output_path: str, format_choice: str,
                 custom_name: str = None):
        self.is_active = True
        self.stop_flag.clear()

        try:
            opts = self._build_opts(url, output_path, format_choice,
                                    custom_name=custom_name)
            logging.info(f"Downloading: {url} | platform={_detect_platform(url)} | format={format_choice}")
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])

            if not self.stop_flag.is_set():
                self.on_finished(success=True)

        except Exception as e:
            msg = str(e).lower()
            if "stopped by user" in msg:
                logging.info("Download stopped by user.")
                self.on_finished(success=False, error="Stopped by user")
            else:
                logging.error(f"Download failed: {e}")
                self.on_finished(success=False, error=str(e))
        finally:
            self.is_active = False
            self.stop_flag.clear()

    def stop(self):
        self.stop_flag.set()

    # ── Parallel Queue support ─────────────────────────────
    def download_queue(self, items: list, output_path: str, format_choice: str,
                       on_item_start, on_item_done, workers: int = 2): 
        self.is_active = True
        self.stop_flag.clear()

        lock = threading.Lock()

        def _download_one(args):
            i, url, title, custom_name = args
            if self.stop_flag.is_set():
                on_item_done(i, False, "Stopped by user")
                return
            on_item_start(i)
            try:
                opts = self._build_opts(url, output_path, format_choice,
                                        custom_name=custom_name)
                logging.info(f"Parallel Queue [{i+1}] Downloading: {url}")
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url])
                if self.stop_flag.is_set():
                    on_item_done(i, False, "Stopped by user")
                else:
                    on_item_done(i, True, None)
            except Exception as e:
                msg = str(e).lower()
                if "stopped by user" in msg:
                    on_item_done(i, False, "Stopped by user")
                else:
                    logging.error(f"Queue item {i} failed: {e}")
                    on_item_done(i, False, str(e))

        tasks = [(i, url, title, custom_name)
                 for i, (url, title, custom_name) in enumerate(items)]

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            executor.map(_download_one, tasks)

        self.is_active = False
        self.stop_flag.clear()

    def _progress_hook(self, d: dict):
        if self.stop_flag.is_set():
            raise Exception("Download stopped by user")

        if d.get("status") == "downloading":
            try:
                raw     = d.get("_percent_str", "0.0%")
                clean   = raw.replace("\x1b[0;94m", "").replace("\x1b[0m", "").strip()
                percent = float(clean.replace("%", "")) / 100.0
                speed   = d.get("_speed_str", "N/A").strip()
                eta     = d.get("_eta_str",   "N/A").strip()
                self.on_progress(percent, f"Speed: {speed} | ETA: {eta}")
            except (ValueError, TypeError) as e:
                logging.warning(f"Failed to parse progress data: {e}")

        elif d.get("status") == "finished":
            self.on_log("Processing file…")


# ══════════════════════════════════════════════════════════
#  E. CONTEXT MENU
# ══════════════════════════════════════════════════════════
class ContextMenu:

    SHORTCUTS = {
        86: "paste",
        67: "copy",
        88: "cut",
        65: "select_all",
    }

    def __init__(self, widget: ctk.CTkEntry):
        self.widget = widget
        self._entry = widget
        widget.bind("<Control-KeyPress>", self._handle_shortcut)
        widget.bind("<Button-3>", self.show_menu)

    def _handle_shortcut(self, event):
        action = self.SHORTCUTS.get(event.keycode)
        if action:
            getattr(self, action)()
            return "break"

    def _has_selection(self) -> bool:
        try:
            self._entry.selection_get()
            return True
        except Exception:
            return False

    def _delete_selection(self):
        try:
            self._entry.delete("sel.first", "sel.last")
        except Exception:
            pass

    def copy(self):
        try:
            text = self._entry.selection_get()
            self.widget.clipboard_clear()
            self.widget.clipboard_append(text)
        except Exception as e:
            logging.warning(f"Copy failed: {e}")

    def cut(self):
        try:
            if self._has_selection():
                self.copy()
                self._delete_selection()
        except Exception as e:
            logging.warning(f"Cut failed: {e}")

    def paste(self):
        try:
            text = self.widget.clipboard_get()
            if self._has_selection():
                self._delete_selection()
            self._entry.insert(tk.INSERT, text)
        except Exception as e:
            logging.warning(f"Paste failed: {e}")

    def select_all(self):
        self._entry.select_range(0, "end")
        self._entry.icursor("end")
        self._entry.focus_set()

    def show_menu(self, event):
        menu = tk.Menu(
            self.widget, tearoff=0,
            bg=CARD_COLOR, fg="white",
            activebackground=THEME_COLOR, activeforeground="white", bd=0
        )
        menu.add_command(label="Cut",        command=self.cut)
        menu.add_command(label="Copy",       command=self.copy)
        menu.add_command(label="Paste",      command=self.paste)
        menu.add_separator()
        menu.add_command(label="Select All", command=self.select_all)
        menu.tk_popup(event.x_root, event.y_root)


# ══════════════════════════════════════════════════════════
#  F. SPLASH SCREEN
# ══════════════════════════════════════════════════════════
class SplashScreen(ctk.CTkToplevel):

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Starting Velix...")
        self.overrideredirect(True)
        self.configure(fg_color="black")
        self.attributes("-transparentcolor", "black")

        w, h = 400, 250
        x = (self.winfo_screenwidth()  // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

        try:
            icon = get_icon_path()
            self.iconbitmap(default=icon)
            self.wm_iconbitmap(default=icon)
        except Exception as e:
            logging.warning(f"Splash icon error: {e}")

        inner = ctk.CTkFrame(self, width=w, height=h, fg_color=BG_COLOR, corner_radius=20)
        inner.pack(fill="both", expand=True)
        inner.pack_propagate(False)

        ctk.CTkLabel(
            inner, text="▶ VELIX",
            font=ctk.CTkFont(family=FontConfig.FAMILY, size=32, weight="bold"),
            text_color=THEME_COLOR
        ).pack(expand=True)

        self.progress_bar = ctk.CTkProgressBar(
            inner, width=300,
            fg_color=CARD_COLOR, progress_color=THEME_COLOR
        )
        self.progress_bar.pack(pady=20)
        self.progress_bar.set(0)


# ══════════════════════════════════════════════════════════
#  G. UPDATE POPUP
# ══════════════════════════════════════════════════════════
class UpdatePopup(ctk.CTkToplevel):

    def __init__(self, parent, latest_version: str, notes: str, download_url: str):
        super().__init__(parent)
        self._download_url = download_url

        self.title("Update Available")
        self.overrideredirect(True)
        self.resizable(False, False)
        self.configure(fg_color="black")
        self.attributes("-transparentcolor", "black")
        self.grab_set()

        w, h = 400, 180
        x = (self.winfo_screenwidth()  // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

        try:
            icon = get_icon_path()
            self.iconbitmap(default=icon)
            self.wm_iconbitmap(default=icon)
        except Exception as e:
            logging.warning(f"UpdatePopup icon error: {e}")

        inner = ctk.CTkFrame(self, width=w, height=h, fg_color="#0d0d0e", corner_radius=20)
        inner.pack(fill="both", expand=True)
        inner.pack_propagate(False)

        ctk.CTkLabel(
            inner, text=f"New Version {latest_version}",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=THEME_COLOR
        ).pack(pady=(20, 10))

        ctk.CTkLabel(inner, text=notes, wraplength=350, justify="center").pack(pady=10)

        btn_frame = ctk.CTkFrame(inner, fg_color="transparent")
        btn_frame.pack(pady=20)

        ctk.CTkButton(
            btn_frame, text="Update",
            fg_color=THEME_COLOR, hover_color=THEME_HOVER,
            command=self._do_update
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_frame, text="Later",
            fg_color="#333", hover_color="#444",
            command=self.destroy
        ).pack(side="left", padx=10)

    def _do_update(self):
        webbrowser.open(self._download_url)
        self.destroy()


# ══════════════════════════════════════════════════════════
#  H. HISTORY WINDOW
# ══════════════════════════════════════════════════════════
class HistoryWindow(ctk.CTkToplevel):

    def __init__(self, parent, settings: "SettingsManager"):
        super().__init__(parent)
        self._settings = settings

        self.title("Download History")
        self.geometry("700x500")
        self.resizable(True, True)
        self.configure(fg_color=BG_COLOR)
        self.grab_set()

        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=(15, 5))

        ctk.CTkLabel(
            hdr, text="Download History",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=THEME_COLOR
        ).pack(side="left")

        ctk.CTkButton(
            hdr, text="Clear All", width=90, height=30,
            fg_color="#cc0000", hover_color="#aa0000",
            font=ctk.CTkFont(size=12),
            command=self._clear_all
        ).pack(side="right")

        ctk.CTkFrame(self, height=1, fg_color=THEME_COLOR).pack(fill="x", padx=20, pady=(5, 10))

        # Scrollable list
        self._list = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color="#333",
            scrollbar_button_hover_color=THEME_COLOR
        )
        self._list.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self._populate()

    def _populate(self):
        for w in self._list.winfo_children():
            w.destroy()

        history = self._settings.get_history()
        if not history:
            ctk.CTkLabel(
                self._list, text="No history yet.",
                text_color="gray", font=ctk.CTkFont(size=13)
            ).pack(pady=30)
            return

        for entry in history:
            row = ctk.CTkFrame(self._list, fg_color=CARD_COLOR, corner_radius=8)
            row.pack(fill="x", pady=3, padx=2)

            left = ctk.CTkFrame(row, fg_color="transparent")
            left.pack(side="left", fill="x", expand=True, padx=10, pady=8)

            url   = entry.get("url", "")
            fmt   = entry.get("format", "")
            path  = entry.get("path", "")
            ts    = entry.get("timestamp", "")

            ctk.CTkLabel(
                left,
                text=url[:65] + ("…" if len(url) > 65 else ""),
                font=ctk.CTkFont(size=12),
                anchor="w", text_color="white"
            ).pack(anchor="w")

            ctk.CTkLabel(
                left,
                text=f"{ts}  •  {fmt}  •  {path}",
                font=ctk.CTkFont(size=10),
                anchor="w", text_color="gray"
            ).pack(anchor="w")

            # Open folder button
            ctk.CTkButton(
                row, text="📁", width=32, height=32,
                fg_color="transparent", hover_color="#333",
                font=ctk.CTkFont(size=14),
                command=lambda p=path: self._open_folder(p)
            ).pack(side="right", padx=(0, 6))

            # Copy URL button
            ctk.CTkButton(
                row, text="🔗", width=32, height=32,
                fg_color="transparent", hover_color="#333",
                font=ctk.CTkFont(size=14),
                command=lambda u=url: self._copy(u)
            ).pack(side="right")

    def _open_folder(self, path: str):
        try:
            if os.path.exists(path):
                os.startfile(path)
        except Exception as e:
            logging.warning(f"Could not open folder: {e}")

    def _copy(self, text: str):
        self.clipboard_clear()
        self.clipboard_append(text)

    def _clear_all(self):
        self._settings.clear_history()
        self._populate()


# ══════════════════════════════════════════════════════════
#  I. MAIN APPLICATION
# ══════════════════════════════════════════════════════════
class VelixApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        icon = get_icon_path()
        self.after(100, lambda: self.iconbitmap(icon))
        self.title(f"{APP_NAME} — Download everything, easily.")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(800, 750)
        self.resizable(False, False)
        self.configure(fg_color=BG_COLOR)
        self.withdraw()

    

        self.settings = SettingsManager()
        self.engine   = DownloadEngine(
            on_progress = self._update_progress,
            on_log      = self._update_status,
            on_finished = self._on_download_finished,
        )
        self._current_url     = ""
        self._sidebar_visible = False
        self._queue           = []   
        self._queue_running   = False
        self._current_thumb_url = None

        self._build_header()
        self._build_input_section()
        self._build_preview_section()
        self._build_controls_section()
        self._build_progress_section()
        self._build_action_buttons()
        self._build_queue_section()
        self._build_sidebar()

        self._show_splash()
        self.after(2000, self._check_for_updates)

    # ══════════════════════════════════════════════════════
    #  UI BUILDERS
    # ══════════════════════════════════════════════════════

    def _build_header(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="x", padx=20, pady=(20, 5))

        top = ctk.CTkFrame(container, fg_color="transparent")
        top.pack(fill="x")

        ctk.CTkLabel(
            top, text="▶ VELIX",
            font=ctk.CTkFont(family=FontConfig.FAMILY, size=22, weight="bold"),
            text_color="white"
        ).pack(side="left")

        ctk.CTkLabel(
            top, text="Video Downloader",
            font=ctk.CTkFont(family=FontConfig.FAMILY, size=12),
            text_color="#666666"
        ).pack(side="left", padx=(10, 0), pady=(5, 0))

        ctk.CTkButton(
            top, text="⚙ Settings", width=100,
            fg_color="transparent", border_width=1,
            border_color="gray", hover_color="#333333",
            command=self._toggle_sidebar
        ).pack(side="right")

        ctk.CTkButton(
            top, text="History", width=100,
            fg_color="transparent", border_width=1,
            border_color="gray", hover_color="#333333",
            command=self._open_history
        ).pack(side="right", padx=(0, 8))

        ctk.CTkFrame(container, height=2, fg_color=THEME_COLOR).pack(fill="x", pady=(10, 0))

    def _build_input_section(self):
        frame = ctk.CTkFrame(self, fg_color=INPUT_BG, corner_radius=10)
        frame.pack(fill="x", padx=12, pady=(10, 10))

        ctk.CTkLabel(
            frame, text="PASTE VIDEO URL",
            font=ctk.CTkFont(family=FontConfig.FAMILY, size=12, weight="bold"),
            text_color="#8a8d9b"
        ).pack(anchor="w", padx=20, pady=(15, 10))

        group = ctk.CTkFrame(frame, fg_color="transparent")
        group.pack(fill="x", padx=15, pady=(0, 15))

        self.url_entry = ctk.CTkEntry(
            group,
            placeholder_text="Paste link here…",
            height=45, fg_color=INPUT_FIELD,
            border_width=0, corner_radius=6,
            text_color="white"
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 15))

        ContextMenu(self.url_entry)

        self.analyze_btn = ctk.CTkButton(
            group, text="Analyze",
            width=120, height=45,
            fg_color=THEME_COLOR, hover_color="#b533ff",
            corner_radius=6,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._start_analysis
        )
        self.analyze_btn.pack(side="right")

        self.add_queue_btn = ctk.CTkButton(
            group, text="+ Queue",
            width=90, height=45,
            fg_color="#2d2f39", hover_color="#3a3c4a",
            border_width=1, border_color=THEME_COLOR,
            text_color=THEME_COLOR,
            corner_radius=6,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._add_to_queue
        )
        self.add_queue_btn.pack(side="right", padx=(0, 8))

    def _build_preview_section(self):
        frame = ctk.CTkFrame(self, fg_color=INPUT_BG, corner_radius=15)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.thumb_label = ctk.CTkLabel(
            frame, text="No Media",
            width=320, height=180,
            fg_color=BG_COLOR, corner_radius=10
        )
        self.thumb_label.pack(side="left", padx=12, pady=12)

        info = ctk.CTkFrame(frame, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, pady=20, padx=(0, 20))

        self.title_label = ctk.CTkLabel(
            info, text="Awaiting URL…",
            font=ctk.CTkFont(family=FontConfig.FAMILY, size=16, weight="bold"),
            wraplength=400, justify="left"
        )
        self.title_label.pack(anchor="w", pady=(0, 10))

        self.duration_label = ctk.CTkLabel(
            info, text="⏱ --:--",
            font=ctk.CTkFont(family=FontConfig.FAMILY, size=12, weight="bold"),
            text_color="gray"
        )
        self.duration_label.pack(anchor="w")

    def _build_controls_section(self):
        frame = ctk.CTkFrame(self, fg_color=INPUT_BG, corner_radius=15)
        frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(frame, text="Quality:").grid(row=0, column=0, padx=15, pady=15, sticky="w")

        self.quality_var = ctk.StringVar(value=QUALITY_OPTIONS[0])
        ctk.CTkOptionMenu(
            frame, variable=self.quality_var,
            values=QUALITY_OPTIONS,
            fg_color="#333",
            button_color=THEME_COLOR,
            button_hover_color="#5d4b80"
        ).grid(row=0, column=1, padx=15, pady=15, sticky="w")

        ctk.CTkLabel(frame, text="Save to:").grid(row=0, column=2, padx=15, pady=15, sticky="e")

        self.path_entry = ctk.CTkEntry(frame, width=200, state="normal")
        self.path_entry.insert(0, self.settings.get_path())
        self.path_entry.configure(state="readonly")
        self.path_entry.grid(row=0, column=3, padx=5, pady=15, sticky="w")

        ctk.CTkButton(
            frame, text="Browse", width=80,
            fg_color="#444", hover_color="#555",
            command=self._browse_folder
        ).grid(row=0, column=4, padx=15, pady=15, sticky="w")

        ctk.CTkLabel(
            frame, text="File name:",
            font=ctk.CTkFont(size=12)
        ).grid(row=1, column=0, padx=15, pady=(0, 12), sticky="w")

        self.filename_entry = ctk.CTkEntry(
            frame,
            placeholder_text="Leave blank to use video title…",
            width=420, height=32,
            fg_color=INPUT_FIELD, border_width=0, corner_radius=5,
            text_color="white"
        )
        self.filename_entry.grid(row=1, column=1, columnspan=4,
                                 padx=(0, 15), pady=(0, 12), sticky="w")
        ContextMenu(self.filename_entry)

    def _build_progress_section(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", padx=20, pady=(10, 0))

        self.progress_bar = ctk.CTkProgressBar(frame, progress_color=THEME_COLOR, height=12)
        self.progress_bar.pack(fill="x", pady=5)
        self.progress_bar.set(0)

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x")

        self.status_label = ctk.CTkLabel(row, text="Ready", text_color="gray", font=ctk.CTkFont(size=12))
        self.status_label.pack(side="left")

        self.speed_label = ctk.CTkLabel(row, text="", text_color="gray", font=ctk.CTkFont(size=12))
        self.speed_label.pack(side="right")

    def _build_action_buttons(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", padx=20, pady=20)

        ctk.CTkButton(
            frame, text="Follow The Dev. Here", height=40,
            font=ctk.CTkFont(family=FontConfig.FAMILY, size=16),
            fg_color="transparent", border_width=2,
            border_color=THEME_COLOR, text_color=THEME_COLOR,
            hover_color=CARD_COLOR,
            command=lambda: webbrowser.open("https://bassem-social-hub.pages.dev/")
        ).pack(side="left")

        self.stop_btn = ctk.CTkButton(
            frame, text="⏹ Stop", height=40,
            font=ctk.CTkFont(family=FontConfig.FAMILY, size=16),
            fg_color="#3a3a45", hover_color="#cc0000",
            state="disabled",
            command=self._stop_download
        )
        self.stop_btn.pack(side="right", padx=(10, 0))

        self.download_btn = ctk.CTkButton(
            frame, text="Download", height=40,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=THEME_COLOR, hover_color=THEME_HOVER,
            command=self._start_download
        )
        self.download_btn.pack(side="right", fill="x", expand=True, padx=(10, 0))

    def _build_queue_section(self):
        """Build the collapsible download queue panel."""
        self._queue_frame_outer = ctk.CTkFrame(self, fg_color=INPUT_BG, corner_radius=12)
        self._queue_frame_outer.pack(fill="x", padx=10, pady=(0, 6))

        header = ctk.CTkFrame(self._queue_frame_outer, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(8, 4))

        ctk.CTkLabel(
            header, text="Download Queue",
            font=ctk.CTkFont(family=FontConfig.FAMILY, size=13, weight="bold"),
            text_color=THEME_COLOR
        ).pack(side="left")

        self._queue_count_label = ctk.CTkLabel(
            header, text="0 items",
            font=ctk.CTkFont(size=11),
            text_color="#666"
        )
        self._queue_count_label.pack(side="left", padx=10)

        btn_row = ctk.CTkFrame(header, fg_color="transparent")
        btn_row.pack(side="right")

        ctk.CTkButton(
            btn_row, text="Clear", width=55, height=26,
            fg_color="#333", hover_color="#444",
            font=ctk.CTkFont(size=11),
            command=self._clear_queue
        ).pack(side="right", padx=(4, 0))

        ctk.CTkButton(
            btn_row, text="Import", width=70, height=26,
            fg_color="#333", hover_color="#444",
            font=ctk.CTkFont(size=11),
            command=self._import_queue
        ).pack(side="right", padx=(4, 0))

        ctk.CTkButton(
            btn_row, text="Export", width=70, height=26,
            fg_color="#333", hover_color="#444",
            font=ctk.CTkFont(size=11),
            command=self._export_queue
        ).pack(side="right", padx=(4, 0))

        self.start_queue_btn = ctk.CTkButton(
            btn_row, text="▶ Start All", width=90, height=26,
            fg_color=THEME_COLOR, hover_color=THEME_HOVER,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._start_queue
        )
        self.start_queue_btn.pack(side="right")

        self._queue_list_frame = ctk.CTkScrollableFrame(
            self._queue_frame_outer,
            height=110, fg_color="transparent",
            scrollbar_button_color="#333",
            scrollbar_button_hover_color=THEME_COLOR
        )
        self._queue_list_frame.pack(fill="x", padx=8, pady=(0, 8))

    def _add_to_queue(self):
        url = self.url_entry.get().strip()
        if not url:
            self._update_status("Please enter a URL first.", error=True)
            return

        if any(item[0] == url for item in self._queue):
            self._update_status("This URL is already in the queue.", error=True)
            return

        title       = self._current_url_title() or url[:60] + ("…" if len(url) > 60 else "")
        custom_name = self.filename_entry.get().strip()
        thumb_url   = self._current_thumb_url
        status_var  = tk.StringVar(value="Pending")
        self._queue.append([url, title, status_var, custom_name, thumb_url])
        self._render_queue_item(len(self._queue) - 1, title, status_var, thumb_url)
        self._update_queue_count()
        self._update_status(f"Added to queue: {title[:40]}…" if len(title) > 40 else f"Added to queue: {title}")

    def _current_url_title(self) -> str:
        """Return the title shown in the preview label (strip the 'Title: ' prefix)."""
        txt = self.title_label.cget("text")
        if txt.startswith("Title: ") and txt != "Awaiting URL…":
            return txt[7:]
        return ""

    def _render_queue_item(self, index: int, title: str, status_var: tk.StringVar,
                            thumb_url: str = None):
        row = ctk.CTkFrame(self._queue_list_frame, fg_color=CARD_COLOR, corner_radius=8)
        row.pack(fill="x", pady=3, padx=2)

        thumb_lbl = ctk.CTkLabel(
            row, text="", width=64, height=36,
            fg_color=BG_COLOR, corner_radius=4
        )
        thumb_lbl.pack(side="left", padx=(8, 6), pady=6)
        if thumb_url:
            threading.Thread(
                target=self._load_queue_thumb,
                args=(thumb_lbl, thumb_url),
                daemon=True
            ).start()
        ctk.CTkLabel(
            row,
            text=f"{index + 1}",
            width=22, height=22,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=THEME_COLOR, corner_radius=11,
            text_color="white"
        ).pack(side="left", padx=(0, 6), pady=6)

    
        ctk.CTkLabel(
            row,
            text=title[:50] + ("…" if len(title) > 50 else ""),
            font=ctk.CTkFont(size=11),
            anchor="w"
        ).pack(side="left", fill="x", expand=True, pady=6)


        ctk.CTkLabel(
            row,
            textvariable=status_var,
            font=ctk.CTkFont(size=11),
            text_color="gray",
            width=95
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            row, text="✕", width=26, height=26,
            fg_color="transparent", hover_color="#cc0000",
            font=ctk.CTkFont(size=11),
            command=lambda i=index: self._remove_from_queue(i)
        ).pack(side="right", padx=(0, 6))

    def _load_queue_thumb(self, label: ctk.CTkLabel, url: str):
        try:
            resp    = requests.get(url, timeout=8)
            img     = Image.open(BytesIO(resp.content)).resize((64, 36), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(64, 36))
            self.after(0, lambda: label.configure(image=ctk_img))
        except Exception:
            pass

    def _remove_from_queue(self, index: int):
        if self._queue_running:
            return
        if 0 <= index < len(self._queue):
            self._queue.pop(index)
            self._rebuild_queue_ui()

    def _clear_queue(self):
        if self._queue_running:
            return
        self._queue.clear()
        self._rebuild_queue_ui()

    def _rebuild_queue_ui(self):
        for widget in self._queue_list_frame.winfo_children():
            widget.destroy()
        for i, item in enumerate(self._queue):
            url, title, status_var = item[0], item[1], item[2]
            thumb_url = item[4] if len(item) > 4 else None
            status_var.set("Pending")
            self._render_queue_item(i, title, status_var, thumb_url)
        self._update_queue_count()

    def _update_queue_count(self):
        n = len(self._queue)
        self._queue_count_label.configure(text=f"{n} item{'s' if n != 1 else ''}")

    def _start_queue(self):
        if not self._queue:
            self._update_status("Queue is empty. Add URLs first.", error=True)
            return
        if self._queue_running:
            return

        self._queue_running = True
        self.start_queue_btn.configure(state="disabled", text="Running…")
        self.download_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self._update_status(f"Starting queue: {len(self._queue)} items…")
        self.progress_bar.set(0)

        items = [(item[0], item[1], item[3]) for item in self._queue]
        workers = int(self._workers_var.get())

        threading.Thread(
            target=self.engine.download_queue,
            args=(
                items,
                self.settings.get_path(),
                self.quality_var.get(),
                self._on_queue_item_start,
                self._on_queue_item_done,
                workers,
            ),
            daemon=True
        ).start()

    def _on_queue_item_start(self, index: int):
        def _ui():
            self._queue[index][2].set("⬇ Downloading")
            total = len(self._queue)
            self._update_status(f"Downloading {index + 1}/{total}: {self._queue[index][1][:40]}")
            self.progress_bar.set(index / total)
        self.after(0, _ui)

    def _on_queue_item_done(self, index: int, success: bool, error: str):
        def _ui():
            total = len(self._queue)
            if success:
                self._queue[index][2].set("Done")
                self.settings.add_to_history({
                    "url":    self._queue[index][0],
                    "format": self.quality_var.get(),
                    "path":   self.settings.get_path()
                })
            elif error == "Stopped by user":
                self._queue[index][2].set("⏹ Stopped")
            else:
                self._queue[index][2].set("Failed")

            done_count = sum(1 for item in self._queue if item[2].get() in ("Done", "Failed", "⏹ Stopped"))
            self.progress_bar.set(done_count / total)

            if done_count >= total or error == "Stopped by user":
                self._queue_running = False
                self.start_queue_btn.configure(state="normal", text="▶ Start All")
                self.download_btn.configure(state="normal")
                self.stop_btn.configure(state="disabled")
                finished = sum(1 for item in self._queue if item[2].get() == "Done")
                self._update_status(f"Queue finished: {finished}/{total} downloaded successfully.")
                self._notify_queue_done(finished, total)

        self.after(0, _ui)

    def _export_queue(self):
        if not self._queue:
            self._update_status("Queue is empty — nothing to export.", error=True)
            return
        path = ctk.filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="velix_queue.txt",
            title="Export Queue"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                for item in self._queue:
                    f.write(item[0] + "\n")
            self._update_status(f"Queue exported: {os.path.basename(path)}")
        except OSError as e:
            self._update_status(f"Export failed: {e}", error=True)

    def _import_queue(self):
        path = ctk.filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Import Queue (one URL per line)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                urls = [line.strip() for line in f if line.strip()]
        except OSError as e:
            self._update_status(f"Import failed: {e}", error=True)
            return

        added = 0
        for url in urls:
            if not any(item[0] == url for item in self._queue):
                status_var = tk.StringVar(value="Pending")
                short = url[:60] + ("…" if len(url) > 60 else "")
                self._queue.append([url, short, status_var, "", None])
                self._render_queue_item(len(self._queue) - 1, short, status_var, None)
                added += 1
        self._update_queue_count()
        self._update_status(f"Imported {added} URL(s) from file.")

    def _open_history(self):
        HistoryWindow(self, self.settings)

    def _notify_queue_done(self, finished: int, total: int):
        """Show a Windows toast-style notification when queue completes."""
        try:
            ctypes.windll.user32.MessageBeep(0x00000040)  
        except Exception:
            pass
        
        popup = ctk.CTkToplevel(self)
        popup.title("")
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.configure(fg_color=CARD_COLOR)
        popup.geometry(f"300x70+{self.winfo_x() + WINDOW_WIDTH - 320}+{self.winfo_y() + WINDOW_HEIGHT - 90}")

        ctk.CTkLabel(
            popup,
            text=f"Queue Done — {finished}/{total} downloaded",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME_COLOR
        ).pack(expand=True)

        popup.after(4000, popup.destroy)

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self, width=SIDEBAR_WIDTH, height=WINDOW_HEIGHT,
            fg_color="#14151a", corner_radius=1
        )
        self.sidebar.place(x=SIDEBAR_X_HIDDEN, y=SIDEBAR_Y_OFFSET)

        header = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        header.pack(fill="x", pady=15, padx=10)

        ctk.CTkLabel(
            header, text="Settings",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=THEME_COLOR
        ).pack(side="left")

        ctk.CTkButton(
            header, text="✕", width=30, height=30,
            fg_color="transparent", hover_color="#333",
            command=self._toggle_sidebar
        ).pack(side="right")

        ctk.CTkFrame(self.sidebar, height=1, fg_color="#333").pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(
            self.sidebar, text="Follow Me",
            fg_color=THEME_COLOR,
            command=lambda: webbrowser.open(
                "https://www.instagram.com/bassemmohamed_0?igsh=NWZoMHVzNnpxdG9t"
            )
        ).pack(pady=10)

        ctk.CTkFrame(self.sidebar, height=1, fg_color="#333").pack(fill="x", padx=10, pady=5)

        # Parallel downloads slider
        ctk.CTkLabel(
            self.sidebar, text="Parallel Downloads:",
            font=ctk.CTkFont(size=12), text_color="gray"
        ).pack(pady=(8, 2))

        self._workers_var = ctk.StringVar(value="2")
        self._workers_label = ctk.CTkLabel(
            self.sidebar,
            text=f"Workers: {self._workers_var.get()}",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=THEME_COLOR
        )
        self._workers_label.pack()

        def _on_slider(val):
            n = int(val)
            self._workers_var.set(str(n))
            self._workers_label.configure(text=f"Workers: {n}")

        ctk.CTkSlider(
            self.sidebar,
            from_=1, to=5, number_of_steps=4,
            command=_on_slider,
            progress_color=THEME_COLOR,
            button_color=THEME_COLOR,
            button_hover_color="#b533ff"
        ).pack(padx=20, pady=(4, 12))

        ctk.CTkFrame(self.sidebar, height=1, fg_color="#333").pack(fill="x", padx=10, pady=5)

        ctk.CTkButton(
            self.sidebar, text="History",
            fg_color="#2d2f39", hover_color="#3a3c4a",
            border_width=1, border_color=THEME_COLOR,
            text_color=THEME_COLOR,
            command=self._open_history
        ).pack(pady=8)

        ctk.CTkLabel(self.sidebar, text=f"Version: {APP_VERSION}", text_color="gray").pack(pady=5)

    # ══════════════════════════════════════════════════════
    #  SIDEBAR ANIMATION
    # ══════════════════════════════════════════════════════

    def _toggle_sidebar(self):
        if self._sidebar_visible:
            self._animate_sidebar(SIDEBAR_X_VISIBLE, SIDEBAR_X_HIDDEN)
            self._sidebar_visible = False
        else:
            self._animate_sidebar(SIDEBAR_X_HIDDEN, SIDEBAR_X_VISIBLE)
            self._sidebar_visible = True

    def _animate_sidebar(self, start: int, end: int):
        step    = -10 if start > end else 10
        current = [start]

        def _slide():
            if (step < 0 and current[0] > end) or (step > 0 and current[0] < end):
                current[0] += step
                self.sidebar.place(x=current[0], y=SIDEBAR_Y_OFFSET)
                self.after(5, _slide)
            else:
                self.sidebar.place(x=end, y=SIDEBAR_Y_OFFSET)

        _slide()

    # ══════════════════════════════════════════════════════
    #  SPLASH & UPDATES
    # ══════════════════════════════════════════════════════

    def _show_splash(self):
        self._splash     = SplashScreen(self)
        self._splash_pct = 0.0
        self._animate_splash()

    def _animate_splash(self):
        self._splash_pct += 0.05
        self._splash.progress_bar.set(self._splash_pct)
        if self._splash_pct < 1.0:
            self.after(100, self._animate_splash)
        else:
            self._splash.destroy()
            self.deiconify()
    def _apply_icon(self):
       
        icon = get_icon_path()
        if not os.path.exists(icon):
            logging.warning(f"Icon file not found: {icon}")
            return

        def _set():
            try:
                self.iconbitmap(default=icon)
                logging.info(f"Icon applied: {icon}")
            except Exception as e:
                logging.warning(f"Icon error: {e}")

        _set()
        self.after(200, _set)

    def _check_for_updates(self):
        def _worker():
            try:
                resp   = requests.get(UPDATE_URL, timeout=5)
                data   = resp.json()
                latest = data.get("latest_version", "")
                notes  = data.get("notes", "")
                dl_url = data.get("download_url", "")

                if version_tuple(latest) > version_tuple(APP_VERSION):
                    self.after(0, lambda: UpdatePopup(self, latest, notes, dl_url))
                else:
                    logging.info("App is up to date.")
            except requests.RequestException as e:
                logging.warning(f"Update check network error: {e}")
            except Exception as e:
                logging.error(f"Update check unexpected error: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    # ══════════════════════════════════════════════════════
    #  ANALYSIS
    # ══════════════════════════════════════════════════════

    def _start_analysis(self):
        url = self.url_entry.get().strip()
        if not url:
            self._update_status("Please enter a valid URL.", error=True)
            return

        self._current_url = url
        self._update_status("Analyzing URL…")
        self.analyze_btn.configure(state="disabled")

        threading.Thread(target=self._analysis_worker, args=(url,), daemon=True).start()

    def _analysis_worker(self, url: str):
        try:
            info = self.engine.fetch_info(url)
            self.after(0, self._populate_preview, info)
        except Exception as e:
            logging.error(f"Analysis failed: {e}")
            self.after(0, self._update_status, "Invalid or unsupported link.", True)
            self.after(0, lambda: self.analyze_btn.configure(state="normal"))

    def _populate_preview(self, info: dict):
        if not info:
            self._update_status("Failed to load video info.", error=True)
            self.analyze_btn.configure(state="normal")
            return

        self.title_label.configure(text=f"Title: {info.get('title', 'Unknown')}")
        self.duration_label.configure(text=f"⏱ {format_duration(info.get('duration'))}")

        thumb = info.get("thumbnail")
        self._current_thumb_url = thumb
        if thumb:
            threading.Thread(target=self._load_thumbnail, args=(thumb,), daemon=True).start()

        self._update_status("Analysis complete. Ready to download.")
        self.analyze_btn.configure(state="normal")

    def _load_thumbnail(self, url: str):
        try:
            resp    = requests.get(url, timeout=10)
            img     = Image.open(BytesIO(resp.content)).resize((320, 180), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(320, 180))
            self.after(0, lambda: self.thumb_label.configure(image=ctk_img, text=""))
        except requests.RequestException as e:
            logging.warning(f"Thumbnail download failed: {e}")
            self.after(0, lambda: self.thumb_label.configure(text="Image Load Failed"))
        except Exception as e:
            logging.error(f"Unexpected thumbnail error: {e}")

    # ══════════════════════════════════════════════════════
    #  DOWNLOAD
    # ══════════════════════════════════════════════════════

    def _start_download(self):
        if not self._current_url:
            self._update_status("Please analyze a video first.", error=True)
            return

        self._set_downloading_state(True)
        self.progress_bar.set(0)
        self._update_status("Starting download…")

        custom_name = self.filename_entry.get().strip()

        threading.Thread(
            target=self.engine.download,
            args=(self._current_url, self.settings.get_path(),
                  self.quality_var.get(), custom_name),
            daemon=True
        ).start()


    def _stop_download(self):
        self.engine.stop()
        self._update_status("Stopped. Ready to download again.")
        self.after(500, lambda: self._set_downloading_state(False))

    def _on_download_finished(self, success: bool, error: str = None):
        if success:
            self.after(0, self._update_status, "Download completed successfully!")
            self.after(0, lambda: self.progress_bar.set(1.0))
            self.after(0, lambda: self.speed_label.configure(text="Done"))
            self.settings.add_to_history({
                "url":    self._current_url,
                "format": self.quality_var.get(),
                "path":   self.settings.get_path()
            })
            self.after(0, lambda: self._set_downloading_state(False))

        elif error == "Stopped by user":
            pass

        else:
            self.after(0, self._update_status, f"Download failed: {error}", True)
            self.after(0, lambda: self._set_downloading_state(False))

    # ══════════════════════════════════════════════════════
    #  HELPERS
    # ══════════════════════════════════════════════════════

    def _set_downloading_state(self, downloading: bool):
        if downloading:
            self.download_btn.configure(state="disabled", text="Downloading…")
            self.stop_btn.configure(state="normal")
            self.analyze_btn.configure(state="disabled")
        else:
            self.download_btn.configure(state="normal", text="Download")
            self.stop_btn.configure(state="disabled")
            self.analyze_btn.configure(state="normal")

    def _update_status(self, text: str, error: bool = False):
        self.status_label.configure(
            text=text,
            text_color="red" if error else "gray"
        )

    def _update_progress(self, percent: float, stats: str):
        self.progress_bar.set(percent)
        self.speed_label.configure(text=stats)

    def _browse_folder(self):
        folder = ctk.filedialog.askdirectory(initialdir=self.settings.get_path())
        if folder:
            self.settings.set_path(folder)
            self.path_entry.configure(state="normal")
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, folder)
            self.path_entry.configure(state="readonly")


# ══════════════════════════════════════════════════════════
#  I. ENTRY POINT
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = VelixApp()
    app.mainloop()
