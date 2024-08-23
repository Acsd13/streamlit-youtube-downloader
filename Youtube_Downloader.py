import streamlit as st
import yt_dlp
from googleapiclient.discovery import build
from urllib.parse import urlparse, parse_qs
import os
import zipfile
import io

# Configuration
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
COOKIES_FILE = 'cookies.txt'
API_KEY = os.getenv('AIzaSyDtHIlY1Z_urTEHSKNqeNMZ9Iynoco8AUU')

# Initialize session state
if 'download_progress' not in st.session_state:
    st.session_state.download_progress = {}

# Function to get video info using YouTube Data API
def get_video_info(video_id):
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    try:
        request = youtube.videos().list(
            part='snippet',
            id=video_id
        )
        response = request.execute()
        return response['items'][0] if response['items'] else None
    except Exception as e:
        st.error(f"Error fetching video info: {str(e)}")
        return None

# Function to handle progress updates
def progress_hook(d):
    if d['status'] == 'finished':
        st.session_state.download_progress[d['filename']] = 'Completed'
    elif d['status'] == 'downloading':
        st.session_state.download_progress[d['filename']] = f"Downloading {d['downloaded_bytes'] / d['total_bytes']:.1%}"

# Function to download videos
def download_videos(video_urls, quality):
    ydl_opts = {
        'format': quality,
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
        'cookiefile': COOKIES_FILE,
        'progress_hooks': [progress_hook]
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download(video_urls)
        st.success("Download completed!")
    except Exception as e:
        st.error(f"Error during download: {str(e)}")

# Function to create a ZIP file for all downloaded files
def create_zip(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zip_file:
        for file_path in files:
            if os.path.exists(file_path):
                file_name = os.path.basename(file_path)
                zip_file.write(file_path, file_name)
    buffer.seek(0)
    return buffer

# Function to get video ID from URL
def get_video_id(url):
    try:
        parsed_url = urlparse(url)
        if 'watch' in parsed_url.path:
            query_params = parse_qs(parsed_url.query)
            return query_params.get('v', [None])[0]
        return None
    except Exception as e:
        st.error(f"Error parsing video ID: {str(e)}")
        return None

# Function to get playlist ID from URL
def get_playlist_id(url):
    try:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        return query_params.get('list', [None])[0]
    except Exception as e:
        st.error(f"Error parsing playlist ID: {str(e)}")
        return None

# Function to get videos from a playlist
def get_playlist_videos(playlist_id):
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    videos = []
    try:
        next_page_token = None
        while True:
            request = youtube.playlistItems().list(
                part='snippet',
                playlistId=playlist_id,
                maxResults=50,
                pageToken=next_page_token
            )
            response = request.execute()
            for item in response['items']:
                video_id = item['snippet']['resourceId']['videoId']
                video_title = item['snippet']['title']
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                videos.append({'title': video_title, 'url': video_url})
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break
        return videos
    except Exception as e:
        st.error(f"Error fetching playlist videos: {str(e)}")
        return []

# User Interface
st.title("YouTube Video Downloader")

st.markdown("""
**Download your favorite YouTube videos or playlists quickly and easily.**
""")

# Download options
st.header("Download Options")
download_type = st.radio("Choose download type", ['Single Video', 'Playlist'])

# Quality selection
st.header("Select Quality")
quality = st.selectbox(
    "Choose the quality for the download:",
    ["best", "1080p", "720p", "480p", "360p"]
)

# URL input
url = st.text_input("Enter YouTube URL")

if url:
    if download_type == 'Single Video':
        video_id = get_video_id(url)
        if video_id:
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            video_info = get_video_info(video_id)
            if video_info:
                st.subheader(f"Video Title: {video_info['snippet']['title']}")
                st.image(video_info['snippet']['thumbnails']['high']['url'])
                
                if st.button("Download Video"):
                    download_videos([video_url], quality)
                    st.download_button(
                        label="Download Video",
                        data=open(os.path.join(DOWNLOAD_DIR, f"{video_info['snippet']['title']}.mp4"), "rb").read(),
                        file_name=f"{video_info['snippet']['title']}.mp4",
                        mime="video/mp4"
                    )
        else:
            st.warning("Invalid video URL.")
    
    elif download_type == 'Playlist':
        playlist_id = get_playlist_id(url)
        if playlist_id:
            videos = get_playlist_videos(playlist_id)
            if videos:
                selected_videos = st.multiselect("Select Videos to Download", [v['title'] for v in videos], default=[v['title'] for v in videos])
                
                if st.button("Download Playlist"):
                    selected_urls = [v['url'] for v in videos if v['title'] in selected_videos]
                    if selected_urls:
                        download_videos(selected_urls, quality)
                        zip_buffer = create_zip([os.path.join(DOWNLOAD_DIR, f"{v['title']}.mp4") for v in videos if v['title'] in selected_videos])
                        st.download_button(
                            label="Download Playlist",
                            data=zip_buffer,
                            file_name="playlist.zip",
                            mime="application/zip"
                        )
            else:
                st.warning("Failed to fetch playlist information.")
        else:
            st.warning("Invalid playlist URL.")
else:
    st.info("Please enter a valid YouTube URL to proceed.")

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
