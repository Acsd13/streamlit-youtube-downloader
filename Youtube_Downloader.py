import streamlit as st
import yt_dlp
from time import sleep
from urllib.parse import urlparse, parse_qs
import base64
import os
import tempfile

# Directory to store downloaded files temporarily
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Function to extract video info
def get_video_info(url):
    ydl_opts = {'quiet': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
    except Exception as e:
        st.error(f"Error extracting video info: {str(e)}")
        return None

# Function to extract videos from a playlist
def get_playlist_videos(playlist_id):
    url = f"https://www.youtube.com/playlist?list={playlist_id}"
    ydl_opts = {'quiet': True, 'extract_flat': True}
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
    
    parsed_url = urlparse(video_url)
    video_id = parse_qs(parsed_url.query).get('v', [None])[0]
    
    if video_id:
        for video in videos:
            if video['id'] == video_id:
                return video['url']
    
    return videos[0]['url'] if videos else None

# Function to extract available formats of a video
def get_available_formats(url):
    ydl_opts = {'quiet': True}
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

# Function to generate download link
def generate_download_link(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    href = f'<a href="data:file/mp4;base64,{b64}" download="{os.path.basename(file_path)}">Download {os.path.basename(file_path)}</a>'
    return href

# Function to handle download progress updates
def progress_hook(d):
    if d['status'] == 'finished':
        st.write(f"Downloaded: {d['filename']}")

# Function to download videos with progress tracking
def download_videos(video_urls, quality='best', fmt='mp4'):
    ydl_opts = {
        'format': f'{quality}/{fmt}',
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
        'continuedl': True,
        'ignoreerrors': True,
        'progress_hooks': [progress_hook],  # Add a progress hook for tracking download progress
    }

    total_videos = len(video_urls)
    overall_progress = st.progress(0)
    status_container = st.empty()
    download_links = []

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            for i, url in enumerate(video_urls):
                try:
                    status_container.subheader(f"Downloading {i+1}/{total_videos}...")
                    ydl.download([url])
                    overall_progress.progress((i + 1) / total_videos)

                    # Create download link for the downloaded file
                    for file in os.listdir(DOWNLOAD_DIR):
                        if file.endswith(fmt):
                            file_path = os.path.join(DOWNLOAD_DIR, file)
                            download_links.append(file_path)

                    sleep(0.1)  # Simulate delay for smooth progress bar update
                except Exception as e:
                    st.error(f"Error downloading video {url}: {str(e)}")
                    continue  # Skip to the next video in case of an error
    except Exception as e:
        st.error(f"Error during download: {str(e)}")
    finally:
        overall_progress.empty()
        status_container.subheader("Download completed!")

        # Display download links and automatically trigger downloads
        if download_links:
            st.subheader("Starting automatic downloads...")
            for file_path in download_links:
                download_link = generate_download_link(file_path)
                st.markdown(download_link, unsafe_allow_html=True)
                # Automatically click the link to start the download
                st.write(f'<script>document.querySelector("a[href=\'data:file/mp4;base64,{base64.b64encode(open(file_path, "rb").read()).decode()}\']").click();</script>', unsafe_allow_html=True)
        else:
            st.warning("No videos were downloaded successfully.")

# User Interface
st.title("YouTube Downloader Pro")

st.markdown("""
**Welcome to YouTube Downloader Pro**: 
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
            quality_fmt = st.sidebar.selectbox("Choose quality and format", formats)
            selected_format = quality_fmt.split(" - ")[0]
        else:
            st.warning("No available formats found.")
            selected_format = 'best'
        
        if st.sidebar.button("Download Video"):
            download_videos([video_url if playlist_id else url], quality=selected_format)
            st.success(f"Download of '{video_info['title']}' completed successfully!")
    elif download_type == 'Playlist':
        videos = get_playlist_videos(playlist_id)
        
        if videos:
            st.subheader("Video Selection Options")

            select_all = st.checkbox("Select all videos", value=False)
            deselect_all = st.checkbox("Deselect all videos", value=False)
            
            start_range = st.number_input("Start range", min_value=1, max_value=len(videos), value=1)
            end_range = st.number_input("End range", min_value=1, max_value=len(videos), value=len(videos))

            st.subheader("Playlist Preview")
            selected_videos = []

            with st.expander("Video List"):
                for i, video in enumerate(videos):
                    if select_all:
                        selected_videos.append(video['url'])
                        st.checkbox(video['title'], value=True, key=video['id'], disabled=True)
                    elif deselect_all:
                        st.checkbox(video['title'], value=False, key=video['id'], disabled=True)
                    elif start_range - 1 <= i <= end_range - 1:
                        selected_videos.append(video['url'])
                        st.checkbox(video['title'], value=True, key=video['id'])
                    else:
                        st.checkbox(video['title'], value=False, key=video['id'])

            if st.sidebar.button("Download Selected Videos"):
                if selected_videos:
                    download_videos(selected_videos, quality='best', fmt='mp4')
                    st.success("Download of selected videos completed successfully!")
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
