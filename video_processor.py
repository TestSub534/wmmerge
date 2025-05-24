import os
import uuid
import subprocess
import logging
import asyncio
from pathlib import Path

# Configure logger
logger = logging.getLogger(__name__)

# Create temp directory if it doesn't exist
TEMP_DIR = Path("./temp")
TEMP_DIR.mkdir(exist_ok=True)

# Watermark configuration
WATERMARK_TEXT = "Insta / Telegram - @supplywalah"
EMAIL_TEXT = "Supplywalah@proton.me"  # Email text for top center
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"  # Default font on many Linux distros
FONT_SIZE = 20
FONT_COLOR = "white"
POSITION = "bottom-right"  # Options: center, bottom-right, top-left, etc.

async def store_video(telegram_file, user_id):
    """Download and store a video file from Telegram."""
    # Create user-specific directory if it doesn't exist
    user_dir = TEMP_DIR / str(user_id)
    user_dir.mkdir(exist_ok=True)
    
    # Generate a unique filename
    file_path = user_dir / f"{uuid.uuid4()}.mp4"
    
    # Download the file
    await telegram_file.download_to_drive(str(file_path))
    
    logger.info(f"Stored video for user {user_id} at {file_path}")
    return str(file_path)

async def apply_watermark(input_path, output_path):
    """Apply watermark to a video using FFmpeg."""
    try:
        # Define watermark position coordinates based on the POSITION setting
        position_map = {
            "center": "x=(w-text_w)/2:y=(h-text_h)/2",
            "bottom": "x=(w-text_w)/2:y=h-th-10",
            "bottom-right": "x=w-tw-10:y=h-th-10",
            "top-left": "x=10:y=10",
            "top-right": "x=w-tw-10:y=10",
        }
        
        position_coords = position_map.get(POSITION, "x=w-tw-10:y=h-th-10")  # Default to bottom-right
        
        # Create filter for watermark text at bottom-right and email at top center
        # Use separate quotes for FFmpeg text to avoid escape issues
        filter_text = f"drawtext=text='{WATERMARK_TEXT}':fontfile={FONT_PATH}:" \
                     f"{position_coords}:fontcolor={FONT_COLOR}:fontsize={FONT_SIZE}:" \
                     f"shadowcolor=black:shadowx=2:shadowy=2"
        
        # Add email text at top center
        filter_text += f", drawtext=text='{EMAIL_TEXT}':fontfile={FONT_PATH}:" \
                      f"x=(w-text_w)/2:y=10:fontcolor={FONT_COLOR}:fontsize={FONT_SIZE}:" \
                      f"shadowcolor=black:shadowx=2:shadowy=2"
        
        # Build FFmpeg command
        cmd = [
            "ffmpeg",
            "-i", input_path,
            "-vf", filter_text,
            "-codec:a", "copy",
            "-y",  # Overwrite output files without asking
            output_path
        ]
        
        # Run the FFmpeg command
        logger.info(f"Applying watermark to {input_path}")
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"FFmpeg watermark error: {stderr.decode()}")
            raise Exception("Failed to apply watermark")
            
    except Exception as e:
        logger.error(f"Error applying watermark: {e}")
        raise

async def merge_videos(video_paths, user_id):
    """Merge multiple videos and apply watermark to the final result."""
    # Create user-specific directory if it doesn't exist
    user_dir = TEMP_DIR / str(user_id)
    user_dir.mkdir(exist_ok=True)
    
    # Create a list file for ffmpeg
    list_file = user_dir / f"list_{uuid.uuid4()}.txt"
    merged_path = user_dir / f"merged_{uuid.uuid4()}.mp4"
    watermarked_path = user_dir / f"watermarked_{uuid.uuid4()}.mp4"
    
    try:
        # Create the list file for ffmpeg concat
        with open(list_file, "w") as f:
            for path in video_paths:
                f.write(f"file '{os.path.abspath(path)}'\n")
        
        # Merge videos
        logger.info(f"Merging {len(video_paths)} videos for user {user_id}")
        merge_cmd = [
            "ffmpeg", 
            "-f", "concat", 
            "-safe", "0", 
            "-i", str(list_file), 
            "-c", "copy",
            "-y",  # Overwrite output files without asking
            str(merged_path)
        ]
        
        merge_process = await asyncio.create_subprocess_exec(
            *merge_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await merge_process.communicate()
        
        if merge_process.returncode != 0:
            logger.error(f"FFmpeg merge error: {stderr.decode()}")
            raise Exception("Failed to merge videos")
        
        # Apply watermark to the merged video
        await apply_watermark(str(merged_path), str(watermarked_path))
        
        return str(watermarked_path)
        
    except Exception as e:
        logger.error(f"Error in merge_videos: {e}")
        raise
    finally:
        # Remove the list file
        if list_file.exists():
            list_file.unlink()

def clean_user_videos(user_id, video_paths, result_path=None):
    """Clean up temporary video files for a user."""
    try:
        # Delete individual video files
        for path in video_paths:
            if os.path.exists(path):
                os.remove(path)
                logger.info(f"Removed video file: {path}")
        
        # Delete the result file if provided
        if result_path and os.path.exists(result_path):
            os.remove(result_path)
            logger.info(f"Removed result file: {result_path}")
            
        # Try to remove any other temporary files in the user's directory
        user_dir = TEMP_DIR / str(user_id)
        if user_dir.exists():
            for file in user_dir.glob("*"):
                try:
                    file.unlink()
                    logger.info(f"Removed temporary file: {file}")
                except:
                    pass
    except Exception as e:
        logger.error(f"Error cleaning up user videos: {e}")
