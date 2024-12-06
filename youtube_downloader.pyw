import os
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

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Sanitize filename
def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', "_", filename)

# Function to download video or audio
def download_video_or_audio(url, folder_path, mode, quality, log_callback, complete_callback):
    try:
        log_callback("Starting download...")
        
        if not url.startswith("http"):
            raise ValueError("Invalid URL provided!")

        yt = YouTube(url)
        title = sanitize_filename(yt.title)
        log_callback(f"Video title: {title}")

        if mode == "video":
            selected_quality = quality  # 'Max', '1080p', '720p', or '480p'

            if selected_quality == "Max":
                # Get the highest resolution video stream
                video_stream = yt.streams.filter(
                    file_extension="mp4", only_video=True
                ).order_by('resolution').desc().first()
            else:
                # Attempt to get the stream with the selected resolution
                video_stream = yt.streams.filter(
                    file_extension="mp4", only_video=True, res=selected_quality
                ).first()
                if not video_stream:
                    # If the desired resolution is not available, fallback to the next lower resolution
                    available_resolutions = [stream.resolution for stream in yt.streams.filter(
                        file_extension="mp4", only_video=True
                    ).order_by('resolution').desc()]
                    fallback_stream = None
                    for res in ["1080p", "720p", "480p"]:
                        if res in available_resolutions:
                            fallback_stream = yt.streams.filter(
                                file_extension="mp4", only_video=True, res=res
                            ).first()
                            break
                    if fallback_stream:
                        log_callback(f"Desired resolution {selected_quality} not available. Using {fallback_stream.resolution} instead.")
                        video_stream = fallback_stream
                    else:
                        # If no acceptable resolution is found, use the highest available
                        log_callback("Desired resolutions not available. Using highest available resolution.")
                        video_stream = yt.streams.filter(
                            file_extension="mp4", only_video=True
                        ).order_by('resolution').desc().first()

            # Old way:
            # video_stream = yt.streams.filter(file_extension="mp4", only_video=True).order_by('resolution').desc().first()
            
            audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()

            if not video_stream or not audio_stream:
                raise ValueError("Could not find suitable video or audio streams!")
            
            temp_dir = tempfile.gettempdir()  # Get the system temporary directory

            log_callback("Downloading video stream...")
            video_path = video_stream.download(temp_dir, filename="temp_video.mp4")
            log_callback(f"Video downloaded to: {video_path}")

            log_callback("Downloading audio stream...")
            audio_path = audio_stream.download(temp_dir, filename="temp_audio.mp4")
            log_callback(f"Audio downloaded to: {audio_path}")

            output_path = os.path.join(folder_path, title + ".mp4")
            log_callback("Combining video and audio using ffmpeg...")
            
            command = [
                "ffmpeg",
                "-y",  # Overwrite output if exists
                "-i", video_path,
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", "aac",
                output_path,
            ]

            log_callback("Starting ffmpeg processing...")
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0  # Hide CMD on Windows
            )

            # Read ffmpeg output line by line and log it
            for line in process.stdout:
                log_callback(line.strip())

            # Wait for process to finish
            process.wait()
            log_callback(f"Video saved to: {output_path}")

            os.remove(video_path)
            os.remove(audio_path)
            log_callback("Temporary files removed.")

        elif mode == "audio":
            audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
            if not audio_stream:
                raise ValueError("Could not find suitable audio stream!")

            log_callback("Downloading audio stream...")
            audio_path = audio_stream.download(folder_path, filename=title + ".mp3")
            log_callback(f"Audio saved to: {audio_path}")

        else:
            raise ValueError("Invalid mode specified!")

        log_callback("Download completed successfully.")
        complete_callback(success=True)
    except Exception as e:
        log_callback(f"Error: {e}")
        complete_callback(success=False)

# GUI for the downloader
def create_downloader_gui(default_folder):
    def start_download():
        url = url_entry.get().strip()
        mode = mode_var.get()
        folder_path = folder_entry.get().strip()

        if not url or not folder_path:
            messagebox.showerror("Error", "Please provide both a URL and a folder path!")
            return

        download_button.config(state="disabled")
        close_button.config(state="disabled")
        threading.Thread(target=download_video_or_audio, args=(url, folder_path, mode, quality_var.get(), log_message, download_complete)).start()

    def log_message(message):
        log_output.insert("end", message + "\n")
        log_output.yview("end")

    def download_complete(success):
        download_button.config(state="normal")
        close_button.config(state="normal")

    def cancel_download():
        root.destroy()

    def update_quality_options():
        if mode_var.get() == "video":
            quality_combobox.configure(state="readonly")
        else:
            quality_combobox.configure(state="disabled")

    # Detect clipboard URL
    clipboard_url = pyperclip.paste()
    default_url = clipboard_url if clipboard_url.startswith("http") and "youtube.com" in clipboard_url else ""

    root = ThemedTk(theme="arc")
    root.title("YouTube Downloader")
    # root.geometry("650x400")

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
    quality_combobox.current(0)  # Set default to 'Max'

    mode_var.trace_add("write", lambda *args: update_quality_options())
    update_quality_options()

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

# Run the GUI
if __name__ == "__main__":
    import sys
    default_folder = sys.argv[1] if len(sys.argv) == 2 else os.getcwd()
    create_downloader_gui(default_folder)
