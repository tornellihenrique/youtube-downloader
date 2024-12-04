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

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Sanitize filename
def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', "_", filename)

# Function to download video or audio
def download_video_or_audio(url, folder_path, mode, log_callback, complete_callback):
    try:
        log_callback("Starting download...")
        
        if not url.startswith("http"):
            raise ValueError("Invalid URL provided!")

        yt = YouTube(url)
        title = sanitize_filename(yt.title)
        log_callback(f"Video title: {title}")

        if mode == "video":
            video_stream = yt.streams.filter(file_extension="mp4", only_video=True).order_by('resolution').desc().first()
            audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()

            if not video_stream or not audio_stream:
                raise ValueError("Could not find suitable video or audio streams!")

            log_callback("Downloading video stream...")
            video_path = video_stream.download(folder_path, filename="temp_video.mp4")
            log_callback(f"Video downloaded to: {video_path}")

            log_callback("Downloading audio stream...")
            audio_path = audio_stream.download(folder_path, filename="temp_audio.mp4")
            log_callback(f"Audio downloaded to: {audio_path}")

            output_path = os.path.join(folder_path, title + ".mp4")
            log_callback("Combining video and audio using ffmpeg...")
            command = [
                "ffmpeg",
                "-y",
                "-i", video_path,
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", "aac",
                output_path,
            ]
            subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
        cancel_button.config(state="disabled")
        threading.Thread(target=download_video_or_audio, args=(url, folder_path, mode, log_message, download_complete)).start()

    def log_message(message):
        log_output.insert("end", message + "\n")
        log_output.yview("end")

    def download_complete(success):
        finish_button.config(state="normal")
        cancel_button.config(state="normal")

    def cancel_download():
        root.destroy()

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

    ttk.Label(root, text="Logs:").pack(anchor="w", padx=10, pady=5)
    log_output = scrolledtext.ScrolledText(root, height=10, width=80, state="normal")
    log_output.pack(padx=10, pady=5)

    button_frame = ttk.Frame(root)
    button_frame.pack(pady=10)

    download_button = ttk.Button(button_frame, text="Start Download", command=start_download)
    download_button.grid(row=0, column=0, padx=5)

    finish_button = ttk.Button(button_frame, text="Finish", state="disabled", command=root.destroy)
    finish_button.grid(row=0, column=1, padx=5)

    cancel_button = ttk.Button(button_frame, text="Cancel", command=cancel_download)
    cancel_button.grid(row=0, column=2, padx=5)

    root.mainloop()

# Run the GUI
if __name__ == "__main__":
    import sys
    default_folder = sys.argv[1] if len(sys.argv) == 2 else os.getcwd()
    create_downloader_gui(default_folder)