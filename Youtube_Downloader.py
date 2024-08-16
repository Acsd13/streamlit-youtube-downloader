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
API_KEY = 'AIzaSyDtHIlY1Z_urTEHSKNqeNMZ9Iynoco8AUU'  # Replace with your YouTube Data API key

# Initialize session state for download files and tracking
if 'download_files' not in st.session_state:
    st.session_state.download_files = set()
if 'download_progress' not in st.session_state:
    st.session_state.download_progress = {}

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

# Function to handle progress updates
def progress_hook(d):
    if d['status'] == 'finished':
        st.session_state.download_progress[d['filename']] = 'Completed'
    elif d['status'] == 'downloading':
        st.session_state.download_progress[d['filename']] = f"Downloading {d['downloaded_bytes'] / d['total_bytes']:.1%}"

# Function to download videos with progress tracking and retry
def download_videos(video_urls, fmt='mp4', max_retries=3):
    ydl_opts = {
        'format': fmt,
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
        'continuedl': True,
        'ignoreerrors': True,
        'cookiefile': COOKIES_FILE,
        'progress_hooks': [progress_hook]
    }

    failed_videos = []
    overall_progress = st.progress(0)
    status_container = st.empty()
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            for i, url in enumerate(video_urls):
                retries = 0
                while retries < max_retries:
                    try:
                        status_container.subheader(f"Downloading {i+1}/{len(video_urls)}...")
                        ydl.download([url])
                        st.session_state.download_progress[url] = 'Completed'
                        overall_progress.progress((i + 1) / len(video_urls))
                        sleep(0.1)
                        break
                    except yt_dlp.utils.DownloadError as e:
                        st.error(f"Error downloading video {url}: {str(e)}")
                        retries += 1
                        if retries == max_retries:
                            st.session_state.download_progress[url] = 'Failed'
                            failed_videos.append(url)
                        else:
                            st.warning(f"Retrying video {url} ({retries}/{max_retries})...")
                        sleep(2)  # Adding a short delay before retrying
                    except Exception as e:
                        st.error(f"Unexpected error: {str(e)}")
                        retries += 1
                        if retries == max_retries:
                            st.session_state.download_progress[url] = 'Failed'
                            failed_videos.append(url)
                        else:
                            st.warning(f"Retrying video {url} ({retries}/{max_retries})...")
                        sleep(2)  # Adding a short delay before retrying
    except Exception as e:
        st.error(f"Error during download: {str(e)}")
    finally:
        overall_progress.empty()
        status_container.subheader("Download completed!")

    if failed_videos:
        st.warning("Retrying failed downloads...")
        download_videos(failed_videos, fmt=fmt, max_retries=max_retries)

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

# Function to get videos from a playlist using YouTube Data API
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
    if download_type == 'Single Video':
        video_id = get_video_id(url)
        if video_id:
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            video_info = get_video_info(video_id)
            if video_info:
                st.subheader(f"Video Title: {video_info['snippet']['title']}")
                st.image(video_info['snippet']['thumbnails']['high']['url'])  # Display thumbnail
                
                if st.button("Download Video", key="download_button_single"):
                    download_videos([video_url], fmt='mp4')
                    st.success(f"Download of '{video_info['snippet']['title']}' completed successfully!")
                    
                    # Provide download link
                    zip_buffer = create_zip([os.path.join(DOWNLOAD_DIR, f"{video_info['snippet']['title']}.mp4")])
                    st.download_button(
                        label="Download Video",
                        data=zip_buffer,
                        file_name=f"{video_info['snippet']['title']}.zip",
                        mime="application/zip",
                        key="download_single_video_zip"
                    )
            else:
                st.warning("Failed to fetch video information.")
        else:
            st.warning("Invalid video URL.")
    
    elif download_type == 'Playlist':
        playlist_id = get_playlist_id(url)
        if playlist_id:
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
                        checked = st.checkbox(video['title'], value=select_all and (start_range <= i + 1 <= end_range), key=f"video_{i}")
                        if checked:
                            selected_videos.append(video['url'])
                    
                if st.button("Download Selected Videos", key="download_button_playlist"):
                    download_videos(selected_videos, fmt='mp4')
                    st.success("Download of selected videos completed successfully!")

                    # Provide zip download link
                    zip_files = [os.path.join(DOWNLOAD_DIR, f"{video['title']}.mp4") for video in videos if video['url'] in selected_videos]
                    if zip_files:
                        zip_buffer = create_zip(zip_files)
                        st.download_button(
                            label="Download Playlist",
                            data=zip_buffer,
                            file_name="playlist.zip",
                            mime="application/zip",
                            key="download_playlist_zip"
                        )
            else:
                st.warning("Failed to fetch playlist videos.")
        else:
            st.warning("Invalid playlist URL.")

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
