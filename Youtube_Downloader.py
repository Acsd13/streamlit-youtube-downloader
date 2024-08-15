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
        
        if st.sidebar.button("Rechercher Video"):
            download_videos([video_url if playlist_id else url], quality=selected_format)
            st.success(f"Preparation of '{video_info['title']}' completed successfully!")

            # Add a button to download the video from the server to the user's device
            video_file_path = os.path.join(DOWNLOAD_DIR, f"{video_info['title']}.{selected_format}")
            if os.path.isfile(video_file_path):
                with open(video_file_path, "rb") as file:
                    st.download_button(
                        label="Download Video",
                        data=file.read(),
                        file_name=f"{video_info['title']}.{selected_format}",
                        mime="video/mp4"
                    )
        else:
            st.warning("Video file not found.")
    elif download_type == 'Playlist':
        st.subheader("Playlist Download")
        playlist_videos = get_playlist_videos(playlist_id)
        
        if playlist_videos:
            video_titles = [v['title'] for v in playlist_videos]
            selected_videos = st.multiselect(
                "Select videos to download from the playlist",
                options=video_titles,
                default=video_titles,
                help="Choose specific videos to download or download all"
            )
            
            if selected_videos:
                selected_urls = [v['url'] for v in playlist_videos if v['title'] in selected_videos]
                selected_format = 'best'  # Default to best available format
                
                if st.sidebar.button("Download Playlist"):
                    download_videos(selected_urls, quality=selected_format)
                    st.success("Playlist download completed successfully!")

                    # Option to download each video to the user's device
                    for video in selected_videos:
                        video_info = next(v for v in playlist_videos if v['title'] == video)
                        video_file_path = os.path.join(DOWNLOAD_DIR, f"{video_info['title']}.{selected_format}")
                        if os.path.isfile(video_file_path):
                            with open(video_file_path, "rb") as file:
                                st.download_button(
                                    label=f"Download {video_info['title']}",
                                    data=file.read(),
                                    file_name=f"{video_info['title']}.{selected_format}",
                                    mime="video/mp4"
                                )
                        else:
                            st.warning(f"File for {video_info['title']} not found.")
            else:
                st.warning("No videos selected for download.")
        else:
            st.warning("No videos found in the playlist.")
else:
    st.warning("Please enter a valid YouTube URL.")
