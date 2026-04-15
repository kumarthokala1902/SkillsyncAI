import os
import sys

# Add current directory to path so we can import local modules
sys.path.append(os.getcwd())

from app import app
from models import db, CourseCategory, Course
from youtube_utils import parse_roadmap_md, get_playlist_videos

def migrate():
    print("🚀 Starting Migration: Recordings Markdown -> Database")
    
    with app.app_context():
        # Create tables
        db.create_all()
        
        md_path = 'Cources_links/tech_roadmap_youtube_playlists.md'
        categories_data = parse_roadmap_md(md_path)
        
        if not categories_data:
            print("❌ No data found in markdown file.")
            return

        for cat_data in categories_data:
            # Check if category exists
            category = CourseCategory.query.filter_by(name=cat_data['name']).first()
            if not category:
                category = CourseCategory(name=cat_data['name'])
                db.session.add(category)
                db.session.commit()
                print(f"✅ Created Category: {category.name}")
            
            for course_data in cat_data['courses']:
                # Check if course exists
                existing_course = Course.query.filter_by(playlist_link=course_data['url']).first()
                if not existing_course:
                    print(f"   📺 Processing Course: {course_data['title']}...")
                    
                    # Fetch videos if it's a playlist
                    videos = []
                    if course_data.get('playlist_id'):
                        videos = get_playlist_videos(course_data['playlist_id'])
                    elif course_data.get('video_id'):
                        videos = [{
                            "id": course_data['video_id'],
                            "title": course_data['title'],
                            "thumbnail": f"https://img.youtube.com/vi/{course_data['video_id']}/mqdefault.jpg"
                        }]
                    
                    new_course = Course(
                        title=course_data['title'],
                        instructor=course_data['instructor'],
                        thumbnail=course_data['thumbnail'],
                        playlist_id=course_data['playlist_id'] or course_data['video_id'],
                        playlist_link=course_data['url'],
                        category_id=category.id
                    )
                    new_course.set_videos(videos)
                    
                    db.session.add(new_course)
                    print(f"      ✨ Added: {new_course.title} ({len(videos)} videos)")
            
            db.session.commit()

    print("🎉 Migration Complete!")

if __name__ == "__main__":
    migrate()
