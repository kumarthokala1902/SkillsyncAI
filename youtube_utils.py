import re
import urllib.request as r
from datetime import datetime
import json
import os

# Utility to parse the tech_roadmap_youtube_playlists.md file
def parse_roadmap_md(file_path):
    if not os.path.exists(file_path):
        return []

    with open(file_path, 'r') as f:
        content = f.read()

    categories = []
    current_category = None
    current_instructor = None

    # Line by line parsing
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if not line: continue

        # Category: ## 1. Salesforce Admin / Dev
        cat_match = re.match(r'^##\s+\d*\.?\s*(.*)', line)
        if cat_match:
            current_category = {
                "name": cat_match.group(1).strip(),
                "courses": []
            }
            categories.append(current_category)
            continue

        # Instructor: ### Apex Hours
        inst_match = re.match(r'^###\s+(.*)', line)
        if inst_match:
            current_instructor = inst_match.group(1).strip()
            continue

        # Link: - [Full Salesforce Admin Playlist (30+ videos)](https://www.youtube.com/playlist?list=PLaGX-30v1lh1BaUKgXa05gqrOP0vUg_6i)
        link_match = re.search(r'-\s+\[(.*?)\]\((.*?)\)', line)
        if link_match and current_category:
            title = link_match.group(1).strip()
            url = link_match.group(2).strip()
            
            # Extract playlist ID or video ID
            playlist_id = None
            video_id = None
            
            if 'list=' in url:
                playlist_id = re.search(r'list=([a-zA-Z0-9_-]+)', url).group(1)
            elif 'watch?v=' in url:
                video_id = re.search(r'v=([a-zA-Z0-9_-]+)', url).group(1)
            elif 'youtu.be/' in url:
                video_id = re.search(r'youtu.be/([a-zA-Z0-9_-]+)', url).group(1)

            if playlist_id or video_id:
                current_category["courses"].append({
                    "title": title,
                    "url": url,
                    "playlist_id": playlist_id,
                    "video_id": video_id,
                    "instructor": current_instructor or "Expert",
                    "thumbnail": f"https://img.youtube.com/vi/{video_id}/0.jpg" if video_id else f"https://i.ytimg.com/vi/placeholder/0.jpg"
                })

    return categories

# Fetch playlist videos without API Key (Regex Scraping)
def get_playlist_videos(playlist_id):
    if not playlist_id: return []
    
    url = f'https://www.youtube.com/playlist?list={playlist_id}'
    try:
        req = r.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        with r.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
            
            # Try multiple patterns for video data extraction
            video_data = []
            seen_ids = set()

            # Robust Strategy: Extract ytInitialData JSON
            try:
                json_data_match = re.search(r'var ytInitialData = (\{.*?\});', html)
                if json_data_match:
                    data = json.loads(json_data_match.group(1))
                    # Navigate the deep nested structure of a playlist page
                    contents = data.get('contents', {}).get('twoColumnBrowseResultsRenderer', {}).get('tabs', [{}])[0].get('tabRenderer', {}).get('content', {}).get('sectionListRenderer', {}).get('contents', [{}])[0].get('itemSectionRenderer', {}).get('contents', [{}])[0].get('playlistVideoListRenderer', {}).get('contents', [])
                    
                    for item in contents:
                        v_render = item.get('playlistVideoRenderer')
                        if v_render:
                            vid = v_render.get('videoId')
                            title = v_render.get('title', {}).get('runs', [{}])[0].get('text', 'Video')
                            if vid and vid not in seen_ids:
                                video_data.append({"id": vid, "title": title, "thumbnail": f"https://img.youtube.com/vi/{vid}/mqdefault.jpg"})
                                seen_ids.add(vid)
            except Exception as jse:
                print(f"JSON parsing failed, falling back to regex: {jse}")

            # Fallback Pattern 1: Standard playlistVideoRenderer
            if not video_data:
                p1 = re.finditer(r'\"videoId\":\"(?P<id>[a-zA-Z0-9_-]+)\".*?\"title\":\{\"runs\":\[\{\"text\":\"(?P<title>.*?)\"\}\]', html)
                for m in p1:
                    vid, title = m.group('id'), m.group('title').encode('utf-8').decode('unicode_escape')
                    if vid not in seen_ids:
                        video_data.append({"id": vid, "title": title, "thumbnail": f"https://img.youtube.com/vi/{vid}/mqdefault.jpg"})
                        seen_ids.add(vid)

            # Fallback Pattern 2: Generic videoId + title (for different layouts)
            if not video_data:
                p2 = re.finditer(r'\"videoId\":\"(?P<id>[a-zA-Z0-9_-]+)\".*?\"simpleText\":\"(?P<title>.*?)\"', html)
                for m in p2:
                    vid, title = m.group('id'), m.group('title').encode('utf-8').decode('unicode_escape')
                    if vid not in seen_ids:
                        video_data.append({"id": vid, "title": title, "thumbnail": f"https://img.youtube.com/vi/{vid}/mqdefault.jpg"})
                        seen_ids.add(vid)
            
            # Pattern 3: Fallback for very minimal JSON
            if not video_data:
                p3 = re.finditer(r'\"videoId\":\"(?P<id>[a-zA-Z0-9_-]+)\"', html)
                for m in p3:
                    vid = m.group('id')
                    if vid not in seen_ids and len(vid) == 11:
                        video_data.append({"id": vid, "title": f"Video {len(video_data)+1}", "thumbnail": f"https://img.youtube.com/vi/{vid}/mqdefault.jpg"})
                        seen_ids.add(vid)

            return video_data
    except Exception as e:
        print(f"Error fetching playlist {playlist_id}: {e}")
        return []

# Helper to provide a single video as a 1-lesson course list
def get_single_video_as_list(video_id, title):
    return [{
        "id": video_id,
        "title": title,
        "thumbnail": f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
    }]
