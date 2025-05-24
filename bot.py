import os
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    ContextTypes, 
    filters
)

from video_processor import (
    store_video,
    merge_videos,
    clean_user_videos
)

# Configure logger
logger = logging.getLogger(__name__)

# Dictionary to store video paths per user
user_videos = {}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    await update.message.reply_text(
        "Welcome to the Video Merger Bot! 🎬\n\n"
        "Send me 2 or more videos, and I'll merge them together and add a watermark.\n\n"
        "Commands:\n"
        "/start - Show this help message\n"
        "/merge - Merge your uploaded videos\n"
        "/reset - Clear your video list"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a help message when the command /help is issued."""
    await update.message.reply_text(
        "Video Merger Bot Help 🎬\n\n"
        "1. Send me videos one by one\n"
        "2. Use /merge to combine them\n"
        "3. Use /reset to clear your uploads\n\n"
        "The videos will be merged in the order you sent them."
    )

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle video messages from the user."""
    user_id = update.effective_user.id
    
    try:
        # Getting the file size before downloading
        file_size_mb = update.message.video.file_size / (1024 * 1024)  # Convert to MB
        
        if file_size_mb > 50:  # Limit file size to 50MB
            await update.message.reply_text(
                "⚠️ This video is too large (over 50MB). Please send smaller videos."
            )
            return
            
        # Inform user that processing has started
        status_message = await update.message.reply_text("📥 Downloading your video...")
        
        # Download and store the video
        video_file = await update.message.video.get_file()
        file_path = await store_video(video_file, user_id)
        
        # Update user's video list
        if user_id not in user_videos:
            user_videos[user_id] = []
        user_videos[user_id].append(file_path)
        
        # Inform the user
        await status_message.edit_text(
            f"✅ Video {len(user_videos[user_id])} saved successfully!\n\n"
            f"You have uploaded {len(user_videos[user_id])} video(s). "
            f"Send more or type /merge to combine them."
        )
        
    except Exception as e:
        logger.error(f"Error handling video: {e}")
        await update.message.reply_text(
            "❌ There was an error processing your video. Please try again."
        )

async def merge_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Merge the videos when the command /merge is issued."""
    user_id = update.effective_user.id
    
    # Check if the user has uploaded any videos
    if user_id not in user_videos or len(user_videos[user_id]) < 2:
        await update.message.reply_text(
            "⚠️ Please send at least 2 videos before merging."
        )
        return
    
    try:
        # Inform user that merging has started
        status_message = await update.message.reply_text(
            "🔄 Merging your videos and adding watermark...\n"
            "This may take a while depending on the size of your videos."
        )
        
        # Process the videos
        result_path = await merge_videos(user_videos[user_id], user_id)
        
        # Send the result back to the user
        await status_message.edit_text("✅ Merge complete! Sending your video...")
        
        # Send the merged video
        with open(result_path, "rb") as video_file:
            await update.message.reply_video(
                video=video_file,
                caption="🎬 Here's your merged video with watermark!"
            )
        
        # Clean up the user's videos
        clean_user_videos(user_id, user_videos[user_id], result_path)
        user_videos[user_id] = []
        
        await status_message.edit_text("✅ Your videos have been merged and sent!")
        
    except Exception as e:
        logger.error(f"Error merging videos: {e}")
        await update.message.reply_text(
            "❌ There was an error merging your videos. Please try again or /reset and start over."
        )

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset the user's video list when the command /reset is issued."""
    user_id = update.effective_user.id
    
    if user_id in user_videos and user_videos[user_id]:
        # Clean up the user's videos
        clean_user_videos(user_id, user_videos[user_id])
        user_videos[user_id] = []
        
        await update.message.reply_text("🧹 Your video list has been cleared.")
    else:
        await update.message.reply_text("ℹ️ You don't have any videos to clear.")

def create_bot():
    """Create and configure the bot with all handlers."""
    # Get bot token from environment variables with fallback
    token = os.getenv("TELEGRAM_BOT_TOKEN", "8030054623:AAGikywtErMITectFywCSOJOtccvfjo3gb8")
    
    # Create the application
    application = ApplicationBuilder().token(token).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("merge", merge_command))
    application.add_handler(CommandHandler("reset", reset_command))
    
    # Add message handlers
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))
    
    # Add a general message handler for other types of messages
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            lambda update, context: update.message.reply_text(
                "Please send me videos or use one of the available commands:\n"
                "/start - Show help\n"
                "/merge - Merge uploaded videos\n"
                "/reset - Clear your video list"
            )
        )
    )
    
    return application
