import os
import sys
import re
from pytubefix import YouTube
import logging
import threading
from tkinter import scrolledtext, messagebox
from tkinter import StringVar
from tkinter import ttk
from ttkthemes import ThemedTk
import pyperclip
import subprocess
import tempfile
import uuid

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', "_", filename)

def download_video_or_audio(url, folder_path, mode, quality, log_callback, complete_callback, progress_callback):
    try:
        log_callback("Starting download...")
        if not url.startswith("http"):
            raise ValueError("Invalid URL provided!")

        yt = YouTube(url)

        title = sanitize_filename(yt.title)
        log_callback(f"Video title: {title}")

        # Variables for progress
        total_size = 0
        downloaded_bytes = 0
        total_duration = float(yt.length) if yt.length else 0.0
        download_done = False

        # Define on_progress callback
        def on_progress(stream, chunk, bytes_remaining):
            nonlocal downloaded_bytes
            downloaded_now = stream.filesize - bytes_remaining
            downloaded_bytes = downloaded_now
            if total_size > 0:
                # Download phase = first half of progress (0-50%)
                downloaded_now = stream.filesize - bytes_remaining
                download_percent = ((downloaded_offset + downloaded_now) / total_size) * 100
                combined_progress = download_percent * 0.5
                progress_callback(combined_progress)

        # Re-instantiate yt with on_progress_callback
        yt = YouTube(url, on_progress_callback=on_progress)

        if mode == "video":
            selected_quality = quality
            # Determine video stream
            if selected_quality == "Max":
                video_stream = yt.streams.filter(file_extension="mp4", only_video=True).order_by('resolution').desc().first()
            else:
                video_stream = yt.streams.filter(file_extension="mp4", only_video=True, res=selected_quality).first()
                if not video_stream:
                    available_resolutions = [stream.resolution for stream in yt.streams.filter(file_extension="mp4", only_video=True).order_by('resolution').desc()]
                    fallback_stream = None
                    for res in ["1080p", "720p", "480p"]:
                        if res in available_resolutions:
                            fallback_stream = yt.streams.filter(file_extension="mp4", only_video=True, res=res).first()
                            break
                    if fallback_stream:
                        log_callback(f"Desired resolution {selected_quality} not available. Using {fallback_stream.resolution} instead.")
                        video_stream = fallback_stream
                    else:
                        log_callback("Desired resolutions not available. Using highest available resolution.")
                        video_stream = yt.streams.filter(file_extension="mp4", only_video=True).order_by('resolution').desc().first()

            audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
            if not video_stream or not audio_stream:
                raise ValueError("Could not find suitable video or audio streams!")

            # Total size for video+audio download
            total_size = (video_stream.filesize or 0) + (audio_stream.filesize or 0)
            downloaded_offset = 0

            temp_dir = tempfile.gettempdir()
            unique_id = uuid.uuid4().hex

            log_callback("Downloading video stream...")
            video_path = video_stream.download(temp_dir, filename=f"temp_video_{unique_id}.mp4")
            log_callback(f"Video downloaded to: {video_path}")

            downloaded_offset = video_stream.filesize

            log_callback("Downloading audio stream...")
            audio_path = audio_stream.download(temp_dir, filename=f"temp_audio_{unique_id}.mp4")
            log_callback(f"Audio downloaded to: {audio_path}")

            # After finishing download, we have 100% of download phase = 50% total
            progress_callback(50.0)

            output_path = os.path.join(folder_path, title + ".mp4")
            log_callback("Combining video and audio using ffmpeg...")

            def parse_ffmpeg_time(line):
                time_match = re.search(r"time=([\d:.]+)", line)
                if time_match:
                    time_str = time_match.group(1)
                    h, m, s = time_str.split(':')
                    s = float(s)
                    seconds = int(h)*3600 + int(m)*60 + s
                    return seconds
                return None

            log_callback("Starting ffmpeg processing...")
            command = [
                "ffmpeg",
                "-y",
                "-i", video_path,
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", "aac",
                output_path,
            ]

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )

            # Track ffmpeg progress: from 50% to 100%
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    log_callback(line.strip())
                    current_time = parse_ffmpeg_time(line)
                    if current_time is not None and total_duration > 0:
                        ffmpeg_percent = (current_time / total_duration) * 100
                        combined_progress = 50 + (ffmpeg_percent * 0.5)
                        if combined_progress > 100:
                            combined_progress = 100
                        progress_callback(combined_progress)

            process.wait()
            log_callback(f"Video saved to: {output_path}")

            os.remove(video_path)
            os.remove(audio_path)
            log_callback("Temporary files removed.")

        elif mode == "audio":
            audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
            if not audio_stream:
                raise ValueError("Could not find suitable audio stream!")

            total_size = audio_stream.filesize or 0
            downloaded_offset = 0

            log_callback("Downloading audio stream...")
            audio_path = audio_stream.download(folder_path, filename=title + ".mp3")
            log_callback(f"Audio saved to: {audio_path}")

            # Audio-only has no ffmpeg stage, so once download done = 100%
            progress_callback(100.0)

        else:
            raise ValueError("Invalid mode specified!")

        log_callback("Download completed successfully.")
        complete_callback(success=True)

    except Exception as e:
        log_callback(f"Error: {e}")
        complete_callback(success=False)

if __name__ == "__main__":
    import sys
    default_folder = sys.argv[1] if len(sys.argv) == 2 else os.getcwd()

    def create_downloader_gui_with_progress(default_folder):
        def start_download():
            url = url_entry.get().strip()
            mode = mode_var.get()
            folder_path = folder_entry.get().strip()

            if not url or not folder_path:
                messagebox.showerror("Error", "Please provide both a URL and a folder path!")
                return

            download_button.config(state="disabled")
            close_button.config(state="disabled")
            update_progress_bar(0.0)
            log_output.delete('1.0', 'end')

            # progress_callback closure
            def progress_callback(percentage):
                # Safely update progress in main thread
                root.after(0, lambda: update_progress_bar(percentage))

            threading.Thread(
                target=download_video_or_audio,
                args=(url, folder_path, mode, quality_var.get(), log_message, download_complete, progress_callback),
                daemon=True
            ).start()

        def log_message(message):
            log_output.insert("end", message + "\n")
            log_output.yview("end")

        def download_complete(success):
            download_button.config(state="normal")
            close_button.config(state="normal")

        def update_quality_options():
            if mode_var.get() == "video":
                quality_combobox.configure(state="readonly")
            else:
                quality_combobox.configure(state="disabled")

        def update_progress_bar(percentage):
            progress_bar["value"] = percentage
            progress_label_var.set(f"{percentage:.2f}%")

        # Detect clipboard URL
        clipboard_url = pyperclip.paste()
        default_url = clipboard_url if clipboard_url.startswith("http") and "youtube.com" in clipboard_url else ""

        root = ThemedTk(theme="arc")
        root.title(f"YouTube Downloader - {sys.executable}")

        ttk.Label(root, text="YouTube URL:").pack(anchor="w", padx=10, pady=5)
        url_entry = ttk.Entry(root, width=80)
        url_entry.insert(0, default_url)
        url_entry.pack(padx=10, pady=5)

        ttk.Label(root, text="Save to Folder:").pack(anchor="w", padx=10, pady=5)
        folder_entry = ttk.Entry(root, width=80)
        folder_entry.insert(0, default_folder)
        folder_entry.pack(padx=10, pady=5)

        ttk.Label(root, text="Download Mode:").pack(anchor="w", padx=10, pady=5)
        mode_var = StringVar(value="video")
        ttk.Radiobutton(root, text="Video", variable=mode_var, value="video").pack(anchor="w", padx=20)
        ttk.Radiobutton(root, text="Audio", variable=mode_var, value="audio").pack(anchor="w", padx=20)

        ttk.Label(root, text="Video Quality:").pack(anchor="w", padx=10, pady=5)
        quality_var = StringVar(value="Max")
        quality_combobox = ttk.Combobox(root, textvariable=quality_var, values=["Max", "1080p", "720p", "480p"], state="readonly")
        quality_combobox.pack(anchor="w", padx=20)
        quality_combobox.current(0)

        mode_var.trace_add("write", lambda *args: update_quality_options())
        update_quality_options()

        # Progress UI
        ttk.Label(root, text="Progress:").pack(anchor="w", padx=10, pady=5)
        progress_label_var = StringVar(value="0.00%")
        ttk.Label(root, textvariable=progress_label_var).pack(anchor="w", padx=10)
        progress_bar = ttk.Progressbar(root, maximum=100)
        progress_bar.pack(fill="x", expand=True, padx=10, pady=5)

        ttk.Label(root, text="Logs:").pack(anchor="w", padx=10, pady=5)
        log_output = scrolledtext.ScrolledText(root, height=10, width=80, state="normal")
        log_output.pack(padx=10, pady=5)

        button_frame = ttk.Frame(root)
        button_frame.pack(pady=10)

        download_button = ttk.Button(button_frame, text="Download", command=start_download)
        download_button.grid(row=0, column=0, padx=5)

        close_button = ttk.Button(button_frame, text="Close", command=root.destroy)
        close_button.grid(row=0, column=1, padx=5)

        root.mainloop()

    create_downloader_gui_with_progress(default_folder)