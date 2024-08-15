import streamlit as st
import yt_dlp
from time import sleep
from urllib.parse import urlparse, parse_qs
import os

# Define the download directory
DOWNLOAD_DIR = 'downloads'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Function to extract video info with cookies
def get_video_info(url):
    ydl_opts = {
        'quiet': True,
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        },
        'geo_bypass': True,
        'retries': 10,
        'sleep_interval': 5,
        'max_sleep_interval': 10,
        'cookiefile': 'cookies.txt',  # Add this line for cookies
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
    except Exception as e:
        st.error(f"Error extracting video info: {str(e)}")
        return None

# Function to extract videos from a playlist
def get_playlist_videos(playlist_id):
    url = f"https://www.youtube.com/playlist?list={playlist_id}"
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        },
        'geo_bypass': True,
        'cookiefile': 'cookies.txt',  # Add this line for cookies
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

# Function to check if a link is a playlist and extract the ID
def get_playlist_id(url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    return query_params.get('list', [None])[0]

# Extract the first video or the exact video equivalent from the playlist
def get_first_or_exact_video(playlist_id, video_url):
    videos = get_playlist_videos(playlist_id)
    if not videos:
        return None
    
    # Parse the video URL to get the video ID
    parsed_url = urlparse(video_url)
    video_id = parse_qs(parsed_url.query).get('v', [None])[0]
    
    # If there's a specific video ID, try to find the matching video in the playlist
    if video_id:
        for video in videos:
            if video['id'] == video_id:
                return video['url']
    
    # Otherwise, return the first video in the playlist
    return videos[0]['url'] if videos else None

# Function to extract available formats of a video
def get_available_formats(url):
    ydl_opts = {
        'quiet': True,
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        },
        'geo_bypass': True,
        'cookiefile': 'cookies.txt',  # Add this line for cookies
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

# Function to download videos with progress tracking
def download_videos(video_urls, quality='best', fmt='mp4'):
    def hook(d):
        if d['status'] == 'downloading':
            speed = d.get('speed', 0) / 1024  # Convert speed to KB/s
            downloaded_bytes = d.get('downloaded_bytes', 0)
            total_bytes = d.get('total_bytes', 0)
            percentage = (downloaded_bytes / total_bytes) * 100 if total_bytes > 0 else 0
            st.session_state.download_status = f"Downloading: {percentage:.2f}% - Speed: {speed:.2f} KB/s"
    
    ydl_opts = {
        'format': f'{quality}/{fmt}',
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
        'continuedl': True,
        'ignoreerrors': True,
        'progress_hooks': [hook],
        'noplaylist': True,  # Ensure only single videos are downloaded
        'cookiefile': 'cookies.txt',  # Add this line for cookies
    }
    
    total_videos = len(video_urls)
    overall_progress = st.progress(0)
    status_container = st.empty()

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            for i, url in enumerate(video_urls):
                status_container.subheader(f"Downloading {i+1}/{total_videos}...")
                st.session_state.download_status = "Starting download..."
                ydl.download([url])
                overall_progress.progress((i + 1) / total_videos)
                sleep(0.1)  # Simulate delay for smooth progress bar update
    except Exception as e:
        st.error(f"Error during download: {str(e)}")
    finally:
        overall_progress.empty()
        status_container.subheader("Download completed!")

# User Interface
st.title("YouTube Downloader Demo")

st.markdown("""
**Welcome to YouTube Downloader Demo**: 
The ultimate solution for downloading videos or playlists from YouTube with ease.
""")

# Download options
st.sidebar.header("Download Options")
download_type = st.sidebar.radio("Choose download type", ['Single Video', 'Playlist'])

# URL input
url = st.sidebar.text_input("Enter YouTube URL")

if url:
    playlist_id = get_playlist_id(url)
    
    if playlist_id and download_type == 'Single Video':
        # Get the first or exact video in the playlist
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
            # Automatically select the best quality
            selected_format = 'best'
        else:
            st.warning("No available formats found.")
            selected_format = 'best'
        
        if st.sidebar.button("Download Video"):
            download_videos([video_url if playlist_id else url], quality=selected_format)
            st.success(f"Download of '{video_info['title']}' completed successfully!")

            # Provide download link
            video_file_path = os.path.join(DOWNLOAD_DIR, f"{video_info['title']}.{selected_format}")
            if os.path.isfile(video_file_path):
                with open(video_file_path, "rb") as file:
                    st.download_button(
                        label="Download Video",
                        data=file.read(),
                        file_name=f"{video_info['title']}.{selected_format}",
                        mime="video/mp4"
                    )
    elif download_type == 'Playlist':
        videos = get_playlist_videos(playlist_id)
        
        if videos:
            st.subheader("Video Selection Options")

            select_all = st.checkbox("Select all videos", value=False)
            deselect_all = st.checkbox("Deselect all videos", value=False)
            
            start_range = st.number_input("Start range", min_value=1, max_value=len(videos), value=1)
            end_range = st.number_input("End range", min_value=1, max_value=len(videos), value=len(videos))

            selected_videos = []

            for video in videos[start_range-1:end_range]:
                if select_all:
                    selected_videos.append(video['url'])
                elif deselect_all:
                    continue
                else:
                    if st.checkbox(video['title'], value=False, key=video['id']):
                        selected_videos.append(video['url'])

            if st.sidebar.button("Download Selected Videos"):
                download_videos(selected_videos, quality='best')
                st.success("Download of selected videos completed successfully!")
                
                # Provide download links
                for video_url in selected_videos:
                    video_info = get_video_info(video_url)
                    if video_info:
                        video_file_path = os.path.join(DOWNLOAD_DIR, f"{video_info['title']}.mp4")
                        if os.path.isfile(video_file_path):
                            with open(video_file_path, "rb") as file:
                                st.download_button(
                                    label=f"Download {video_info['title']}",
                                    data=file.read(),
                                    file_name=f"{video_info['title']}.mp4",
                                    mime="video/mp4"
                                )
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
