import streamlit as st
import yt_dlp
from time import sleep
from urllib.parse import urlparse, parse_qs
import os
import zipfile
import io

# Directory to store downloaded files temporarily
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Path to cookies file
COOKIES_FILE = 'cookies.txt'

# Function to create a ZIP file for all downloaded files
def create_zip(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zip_file:
        for file_path in files:
            if os.path.exists(file_path):
                file_name = os.path.basename(file_path)
                zip_file.write(file_path, file_name)
            else:
                st.warning(f"File {file_path} not found. It will not be included in the ZIP.")
    buffer.seek(0)
    return buffer

# Function to check if all files are downloaded
def check_all_files_downloaded(expected_files):
    downloaded_files = set(os.listdir(DOWNLOAD_DIR))
    return all(file in downloaded_files for file in expected_files)

# Function to handle download progress
def download_videos(video_urls, quality='best', fmt='mp4'):
    ydl_opts = {
        'format': f'{quality}/{fmt}',
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
        'continuedl': True,
        'ignoreerrors': True,
        'cookiefile': COOKIES_FILE,
        'progress_hooks': [lambda d: progress_hook(d, st.session_state.download_files)]  # Use session state
    }

    total_videos = len(video_urls)
    overall_progress = st.progress(0)
    status_container = st.empty()
    
    failed_videos = []
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            for i, url in enumerate(video_urls):
                try:
                    status_container.subheader(f"Downloading {i+1}/{total_videos}...")
                    ydl.download([url])
                    
                    overall_progress.progress((i + 1) / total_videos)
                    sleep(0.1)  # Simulate delay for smooth progress bar update
                except Exception as e:
                    st.error(f"Error downloading video {url}: {str(e)}")
                    failed_videos.append(url)  # Add to failed videos list
                    continue  # Skip to the next video in case of an error
    except Exception as e:
        st.error(f"Error during download: {str(e)}")
    finally:
        overall_progress.empty()
        status_container.subheader("Download completed!")

        # Retry failed videos
        if failed_videos:
            st.warning("Some videos failed to download. Retrying...")
            download_videos(failed_videos, quality=quality, fmt=fmt)

        if not failed_videos:
            # Create a ZIP file if all videos are downloaded
            zip_files = [os.path.join(DOWNLOAD_DIR, f"{os.path.basename(urlparse(v).path)}.mp4") for v in video_urls]
            if check_all_files_downloaded(zip_files):
                zip_buffer = create_zip(zip_files)
                st.download_button(
                    label="Download All as ZIP",
                    data=zip_buffer,
                    file_name="videos.zip",
                    mime="application/zip",
                    key="download_zip"
                )
            else:
                st.warning("Not all videos could be downloaded. ZIP file will not be created.")

# Footer with contact icons and information
st.markdown("""
<style>
.footer {
    position: fixed;
    bottom: 0;
    left: 0;
    width: 100%;
    background-color: #2c3e50;
    color: white;
    padding: 15px 0;
    text-align: center;
    border-top: 1px solid #34495e;
    display: flex;
    justify-content: center;
    align-items: center;
    flex-direction: column;
}
.footer .text {
    margin-bottom: 10px;
}
.footer a {
    color: white;
    text-decoration: none;
    margin: 0 5px;
}
.footer a:hover {
    text-decoration: underline;
}
.footer img {
    vertical-align: middle;
}
</style>
<div class="footer">
    <div class="text">
        Created by Chohaidi Abdessamad on 13-08-2024
        <br>
        For more information or inquiries, feel free to <a href="mailto:abdessamad.chohaidi@gmail.com">contact me</a>.
    </div>
    <div>
        <a href="https://www.facebook.com/profile.php?id=100091786905006" target="_blank">
            <img src="https://cdn-icons-png.flaticon.com/512/174/174848.png" width="24" alt="Facebook">
        </a>
        <a href="https://www.instagram.com/chohaidi1311s/" target="_blank">
            <img src="https://cdn-icons-png.flaticon.com/512/174/174855.png" width="24" alt="Instagram">
        </a>
        <a href="https://www.linkedin.com/in/abdessamad-chohaidi/" target="_blank">
            <img src="https://cdn-icons-png.flaticon.com/512/174/174857.png" width="24" alt="LinkedIn">
        </a>
        <a href="mailto:abdessamad.chohaidi@gmail.com" target="_blank">
            <img src="https://cdn-icons-png.flaticon.com/512/64/64572.png" width="24" alt="Email">
        </a>
    </div>
</div>
""", unsafe_allow_html=True)
