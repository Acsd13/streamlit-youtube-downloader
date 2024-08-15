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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/91.0.4472.124 Safari/537.36',
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

# Function to validate a URL (either single video or playlist)
def validate_url(url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    return 'list' in query_params or 'v' in query_params

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
        
        # Provide download links
        for i, url in enumerate(video_urls):
            video_info = get_video_info(url)
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

# Streamlit UI
st.title("YouTube Video Downloader")

st.write("Download single YouTube videos or entire playlists.")
video_url = st.text_input("Enter the YouTube URL")

quality = st.selectbox("Select Quality", options=["best", "worst", "high", "medium", "low"], index=0)
fmt = st.selectbox("Select Format", options=["mp4", "webm", "mkv", "flv"], index=0)

if st.button("Download"):
    if validate_url(video_url):
        video_info = get_video_info(video_url)
        if video_info:
            if 'entries' in video_info:  # If it's a playlist
                st.write(f"Playlist detected: {video_info['title']} with {len(video_info['entries'])} videos")
                video_urls = [entry['webpage_url'] for entry in video_info['entries']]
            else:  # Single video
                st.write(f"Video detected: {video_info['title']}")
                video_urls = [video_info['webpage_url']]
            
            download_videos(video_urls, quality, fmt)
        else:
            st.error("Failed to retrieve video information. Please check the URL and try again.")
    else:
        st.error("Invalid YouTube URL. Please enter a valid video or playlist URL.")

# Display a global download progress bar
if 'download_status' in st.session_state:
    st.text(st.session_state.download_status)

# Footer Section
st.markdown("""---""")
st.markdown(
    """
    <div style='text-align: center;'>
        <p>Created by Chohaidi Abdessamad | <a href='mailto:your-email@example.com'>Contact Us</a></p>
        <p>Connect with us on: 
            <a href='https://www.instagram.com/yourusername' target='_blank'>Instagram</a> | 
            <a href='https://www.facebook.com/yourusername' target='_blank'>Facebook</a> | 
            <a href='https://www.linkedin.com/in/yourusername' target='_blank'>LinkedIn</a>
        </p>
        <p>Created on: August 15, 2024</p>
        <p>Demo Version</p>
    </div>
    """, unsafe_allow_html=True
)
