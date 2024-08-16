import streamlit as st
import yt_dlp
from googleapiclient.discovery import build
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

# YouTube Data API key
API_KEY = 'AIzaSyDtHIlY1Z_urTEHSKNqeNMZ9Iynoco8AUU'

# Function to get video info using YouTube Data API
def get_video_info(video_id):
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    try:
        request = youtube.videos().list(
            part='snippet,contentDetails,statistics',
            id=video_id
        )
        response = request.execute()
        return response['items'][0] if response['items'] else None
    except Exception as e:
        st.error(f"Error fetching video info: {str(e)}")
        return None

# Function to handle download progress
def progress_hook(d, download_files):
    if d['status'] == 'finished':
        download_files.add(d['filename'])

# Function to download videos with progress tracking
def download_videos(video_urls, fmt='mp4'):
    ydl_opts = {
        'format': fmt,
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
                    failed_videos.append(url)
                    continue  # Skip to the next video in case of an error
    except Exception as e:
        st.error(f"Error during download: {str(e)}")
    finally:
        overall_progress.empty()
        status_container.subheader("Download completed!")

    # Retry failed downloads
    if failed_videos:
        st.warning("Retrying failed downloads...")
        download_videos(failed_videos, fmt=fmt)

# Function to create a ZIP file for all downloaded files
def create_zip(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zip_file:
        for file_path in files:
            file_name = os.path.basename(file_path)
            zip_file.write(file_path, file_name)
    buffer.seek(0)
    return buffer

# Function to get video ID from URL
def get_video_id(url):
    try:
        parsed_url = urlparse(url)
        video_id = parse_qs(parsed_url.query).get('v', [None])[0]
        return video_id
    except Exception as e:
        st.error(f"Error parsing video ID: {str(e)}")
        return None

# Initialize session state for download files
if 'download_files' not in st.session_state:
    st.session_state.download_files = set()

# User Interface
st.title("YouTube Downloader Pro")

st.markdown("""
**Welcome to YouTube Downloader Pro**: 
The ultimate solution for downloading videos or playlists from YouTube with ease.
""")

# Download options
st.header("Download Options")
download_type = st.radio("Choose download type", ['Single Video', 'Playlist'], key="download_type")

# URL input
url = st.text_input("Enter YouTube URL", key="url_input")

if url:
    video_id = get_video_id(url)
    
    if video_id and download_type == 'Single Video':
        video_info = get_video_info(video_id)
        
        if video_info:
            st.subheader(f"Video Title: {video_info['snippet']['title']}")
            st.image(video_info['snippet']['thumbnails']['high']['url'])  # Display thumbnail
            
            if st.button("Download Video", key="download_button_single"):
                download_videos([url], fmt='mp4')
                st.success(f"Download of '{video_info['snippet']['title']}' completed successfully!")
        else:
            st.warning("No valid video found.")
    
    elif download_type == 'Playlist':
        playlist_id = get_playlist_id(url)
        videos = get_playlist_videos(playlist_id)
        
        if videos:
            st.subheader("Video Selection Options")

            select_all = st.checkbox("Select all videos", value=False, key="select_all")
            deselect_all = st.checkbox("Deselect all videos", value=False, key="deselect_all")
            
            start_range = st.number_input("Start range", min_value=1, max_value=len(videos), value=1, key="start_range")
            end_range = st.number_input("End range", min_value=1, max_value=len(videos), value=len(videos), key="end_range")

            st.subheader("Playlist Preview")
            selected_videos = []

            with st.expander("Video List"):
                for i, video in enumerate(videos):
                    is_selected = select_all or (start_range - 1 <= i <= end_range - 1)
                    if deselect_all:
                        is_selected = False
                    if st.checkbox(video['title'], value=is_selected, key=f"checkbox_{i}"):
                        selected_videos.append(video['url'])
                        video_info = get_video_info(video['url'].split('/')[-1])
                        if video_info:
                            st.image(video_info['snippet']['thumbnails']['high']['url'])  # Display thumbnail

            if st.button("Download Selected Videos", key="download_button_playlist"):
                if selected_videos:
                    download_videos(selected_videos, fmt='mp4')
                    st.success("Download of selected videos completed successfully!")

                    # Provide a single download button for all files as a ZIP archive
                    if st.session_state.download_files:
                        zip_buffer = create_zip(st.session_state.download_files)
                        st.download_button(
                            label="Download All as ZIP",
                            data=zip_buffer,
                            file_name="videos.zip",
                            mime="application/zip",
                            key="download_zip"
                        )
                else:
                    st.warning("No videos selected.")
        else:
            st.warning("No videos found in the playlist.")

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
