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

# Function to extract video info
def get_video_info(url):
    ydl_opts = {
        'quiet': True,
        'cookiefile': COOKIES_FILE
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as e:
        if "Sign in to confirm you’re not a bot" in str(e):
            st.warning("Captcha or sign-in required. Please check your cookies file or try to solve the CAPTCHA manually.")
        else:
            st.error(f"Error extracting video info: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Unexpected error extracting video info: {str(e)}")
        return None

# Function to extract videos from a playlist
def get_playlist_videos(playlist_id):
    url = f"https://www.youtube.com/playlist?list={playlist_id}"
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'cookiefile': COOKIES_FILE
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            if 'entries' in info_dict:
                return info_dict['entries']
            else:
                st.warning("This link is not a valid playlist.")
                return []
    except Exception as e:
        st.error(f"Error extracting playlist: {str(e)}")
        return []

# Function to extract available formats of a video
def get_available_formats(url):
    ydl_opts = {
        'quiet': True,
        'cookiefile': COOKIES_FILE
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            formats = info_dict.get('formats', [])
            format_list = []
            for f in formats:
                format_id = f.get('format_id', 'N/A')
                ext = f.get('ext', 'N/A')
                resolution = f.get('height', 'N/A')
                fps = f.get('fps', 'N/A')
                filesize = f.get('filesize', 'N/A')
                
                if ext == 'mp4' and resolution in [1080, 720, 480, 360]:
                    format_entry = f"{format_id} - {ext.upper()} ({resolution}p, {fps}fps, {filesize}B)"
                    format_list.append(format_entry)

            return format_list
    except Exception as e:
        st.error(f"Error extracting available formats: {str(e)}")
        return []

# Function to handle download progress
def progress_hook(d, download_files):
    if d['status'] == 'finished':
        download_files.add(d['filename'])

# Function to download videos with progress tracking
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

# Function to create a ZIP file for all downloaded files
def create_zip(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zip_file:
        for file_path in files:
            file_name = os.path.basename(file_path)
            zip_file.write(file_path, file_name)
    buffer.seek(0)
    return buffer

# Function to get playlist ID from URL
def get_playlist_id(url):
    try:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        return query_params.get('list', [None])[0]
    except Exception as e:
        st.error(f"Error parsing playlist ID: {str(e)}")
        return None

# Function to get the first video URL or exact video URL from playlist
def get_first_or_exact_video(playlist_id, url):
    videos = get_playlist_videos(playlist_id)
    if videos:
        # Assuming the URL is in the playlist
        for video in videos:
            if video['url'] == url:
                return url
        return videos[0]['url']  # Default to first video if exact URL not found
    return None

# Function to check if all files are downloaded
def check_all_files_downloaded(expected_files):
    downloaded_files = set(os.listdir(DOWNLOAD_DIR))
    return all(file in downloaded_files for file in expected_files)

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
download_type = st.radio("Choose download type", ['Single Video', 'Playlist'], key="download_type")

# URL input
url = st.text_input("Enter YouTube URL", key="url_input")

if url:
    playlist_id = get_playlist_id(url)
    
    if playlist_id and download_type == 'Single Video':
        video_url = get_first_or_exact_video(playlist_id, url)
        if video_url:
            video_info = get_video_info(video_url)
        else:
            st.warning("No valid video found in the playlist.")
    elif download_type == 'Playlist':
        video_info = None  # Playlist handling is done later
    else:
        video_info = get_video_info(url)
    
    if video_info and download_type == 'Single Video':
        st.subheader(f"Video Title: {video_info['title']}")
        
        formats = get_available_formats(video_url if playlist_id else url)
        if formats:
            quality_fmt = st.selectbox("Choose quality and format", formats, key="format_select")
            selected_format = quality_fmt.split(" - ")[0]
        else:
            st.warning("No available formats found.")
            selected_format = 'best'
        
        if st.button("Download Video", key="download_button_single"):
            download_videos([video_url if playlist_id else url], quality=selected_format)
            st.success(f"Download of '{video_info['title']}' completed successfully!")
    elif download_type == 'Playlist':
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
                    st.checkbox(video['title'], value=is_selected, key=f"checkbox_{i}")
                    if is_selected:
                        selected_videos.append(video['url'])

            if st.button("Download Selected Videos", key="download_button_playlist"):
                if selected_videos:
                    download_videos(selected_videos, quality='best', fmt='mp4')

                    # Check if all videos are downloaded and provide a ZIP download option
                    if check_all_files_downloaded([os.path.basename(urlparse(v).path) + ".mp4" for v in selected_videos]):
                        zip_buffer = create_zip([os.path.join(DOWNLOAD_DIR, os.path.basename(urlparse(v).path) + ".mp4") for v in selected_videos])
                        st.download_button(
                            label="Download All as ZIP",
                            data=zip_buffer,
                            file_name="videos.zip",
                            mime="application/zip",
                            key="download_zip"
                        )
                    else:
                        st.warning("Not all videos could be downloaded.")
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
