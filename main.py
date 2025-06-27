#!/usr/bin/env python3
import os
import sys
import asyncio
import logging
import tempfile
import subprocess
import shutil
from urllib.parse import urlparse
from yt_dlp import YoutubeDL
from telegram import Update, InputFile
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from telegram.constants import ParseMode

# Configuration
BOT_TOKEN = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
ADMIN_IDS = {xxxxxxxxxxxxx, xxxxxxxxxx}
TARGET_GROUP_ID = xxxxxxxxxxxxx
MAX_PART_MB = 43
SPLIT_THRESHOLD = 50 * 1024 * 1024
SITE_LOG_FILE = "sitelog.txt"

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global variables
download_queue = asyncio.Queue()
processing_task = None
queue_lock = asyncio.Lock()
cancel_requested = False
extra_caption = {"count": 0, "text": ""}
processing_delay = 15
part_upload_delay = 0
full_video_caption = "🔥 Complete Video"

# Load supported sites
SUPPORTED_SITES = set()
if os.path.exists(SITE_LOG_FILE):
    with open(SITE_LOG_FILE, 'r') as f:
        SUPPORTED_SITES.update(line.strip() for line in f if line.strip())

# Downloader configurations
aria2_opts = {
    'format': 'bestvideo+bestaudio/best',
    'outtmpl': '%(title)s.%(ext)s',
    'merge_output_format': 'mp4',
    'quiet': True,
    'noplaylist': True,
    'no_warnings': True,
    'downloader': 'aria2c',
    'downloader_args': {'aria2c': ['-x', '8', '-k', '1M']},
    'age_limit': 18,
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'web'],
            'skip': ['dash', 'hls']
        }
    }
}

internal_opts = aria2_opts.copy()
internal_opts.pop('downloader', None)
internal_opts.pop('downloader_args', None)

# Utility functions
def get_domain(url):
    """Extract scheme://netloc from URL"""
    try:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        return None

def add_supported_site(domain):
    """Add a new domain to supported sites if not already present"""
    if not domain or domain in SUPPORTED_SITES:
        return
    
    SUPPORTED_SITES.add(domain)
    # Atomic write to avoid corruption
    temp_file = f"{SITE_LOG_FILE}.tmp"
    with open(temp_file, 'a') as f:
        f.write(f"{domain}\n")
    os.replace(temp_file, SITE_LOG_FILE)

def check_ffmpeg_installed():
    """Check if ffmpeg and ffprobe are available"""
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["ffprobe", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except FileNotFoundError:
        return False

def extract_thumbnail(video_path, thumb_path, ratio=0.3):
    """Extract thumbnail from video at specified time ratio"""
    try:
        duration = float(subprocess.check_output([
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', video_path
        ]).decode().strip())
        timestamp = duration * ratio
        subprocess.run([
            'ffmpeg', '-y', '-ss', str(timestamp), '-i', video_path,
            '-frames:v', '1', '-q:v', '2', thumb_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return os.path.exists(thumb_path)
    except Exception:
        return False

def split_video_streamcopy(video_path, output_dir, max_part_size_mb):
    """Split video using stream copy (fast but less precise)"""
    os.makedirs(output_dir, exist_ok=True)
    part_paths = []
    size = os.path.getsize(video_path)
    duration = float(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', video_path
    ]).decode().strip())
    bps = size / duration
    target_sec = (max_part_size_mb * 1024 * 1024) / bps

    start = 0
    idx = 1
    while start < duration:
        out_path = os.path.join(output_dir, f"part{idx}.mp4")
        cmd = ['ffmpeg', '-y', '-ss', str(start), '-i', video_path, '-t', str(target_sec),
               '-c', 'copy', '-avoid_negative_ts', 'make_zero', '-movflags', '+faststart', out_path]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            part_paths.append(out_path)
        else:
            break
        start += target_sec
        idx += 1
    return part_paths

def split_video_fallback_reencode(video_path, output_dir, max_part_size_mb):
    """Split video with re-encoding (slower but more reliable)"""
    os.makedirs(output_dir, exist_ok=True)
    part_paths = []
    size = os.path.getsize(video_path)
    duration = float(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', video_path
    ]).decode().strip())
    bps = size / duration
    target_sec = (max_part_size_mb * 1024 * 1024) / bps

    start = 0
    idx = 1
    while start < duration:
        out_path = os.path.join(output_dir, f"part{idx}.mp4")
        cmd = ['ffmpeg', '-y', '-ss', str(start), '-i', video_path, '-t', str(target_sec),
               '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28',
               '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', out_path]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            part_paths.append(out_path)
        else:
            break
        start += target_sec
        idx += 1
    return part_paths

# Command handlers
async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show welcome message with all commands"""
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    commands = [
        "<b>Admin Commands:</b>",
        "/start - Show this menu",
        "/cap &lt;N&gt; &lt;caption&gt; - Add caption to next N videos",
        "/capedit - Edit default full video caption",
        "/delay &lt;N&gt; - Set delay between links (seconds)",
        "/slow &lt;N&gt; - Set delay between parts (0-30s)",
        "/cancel - Stop current download",
        "/clean - Cancel + Clear queue",
        "/skip &lt;N&gt; - Skip next N links",
        "/remain - Show pending links",
        "/support - Show supported sites count"
    ]
    
    await update.message.reply_text(
        "🤖 <b>Video Download Bot</b>\n\n" + 
        "\n".join(commands),
        parse_mode="HTML"
    )

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show menu with all admin commands"""
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    menu_text = """
<b>📋 Admin Command Menu</b>

<b>📝 Caption Management</b>
/cap N caption - Add caption to next N videos
/capedit text - Change default full video caption

<b>⏱️ Timing Control</b>
/delay N - Set delay between links (seconds)
/slow N - Set delay between parts (0-30s)

<b>🛠️ Queue Management</b>
/cancel - Stop current download
/clean - Cancel + Clear queue
/skip N - Skip next N links
/remain - Show pending links

<b>ℹ️ Information</b>
/support - Show supported sites count
/support_file - Get full list of supported sites
"""
    
    await update.message.reply_text(
        menu_text,
        parse_mode=ParseMode.HTML
    )

async def handle_capedit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Edit the default caption for full videos"""
    global full_video_caption
    
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    if not context.args:
        await update.message.reply_text(
            "📝 <b>Caption Editor</b>\n\n"
            f"Current full video caption:\n<code>{full_video_caption}</code>\n\n"
            "To change it:\n<code>/capedit Your new caption</code>",
            parse_mode="HTML"
        )
        return
    
    full_video_caption = ' '.join(context.args)
    await update.message.reply_text(
        f"✅ Full video caption updated to:\n<code>{full_video_caption}</code>",
        parse_mode="HTML"
    )

async def handle_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set delay between processing links"""
    global processing_delay
    
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    if not context.args:
        await update.message.reply_text(f"Current delay between links: {processing_delay} seconds")
        return
    
    try:
        new_delay = int(context.args[0])
        if new_delay < 0:
            raise ValueError("Delay cannot be negative")
        
        processing_delay = new_delay
        await update.message.reply_text(f"✅ Delay between links set to {processing_delay} seconds")
    except ValueError as e:
        await update.message.reply_text(f"Invalid delay value: {e}\nUsage: /delay <seconds>")

async def handle_slow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set delay between uploading parts of the same video"""
    global part_upload_delay
    
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    if not context.args:
        await update.message.reply_text(
            f"⏳ Current delay between parts: {part_upload_delay} seconds\n"
            "Usage: /slow <0-30>"
        )
        return
    
    try:
        new_delay = int(context.args[0])
        if new_delay < 0 or new_delay > 30:
            raise ValueError("Delay must be between 0 and 30 seconds")
        
        part_upload_delay = new_delay
        await update.message.reply_text(f"⏳ Delay between parts set to {part_upload_delay} seconds")
    except ValueError as e:
        await update.message.reply_text(f"❌ Invalid value: {e}\nUsage: /slow <0-30>")

async def handle_cap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add extra caption to next N videos"""
    global extra_caption
    
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    if not context.args or len(context.args) < 2 or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /cap <N> <caption text>")
        return
    
    count = int(context.args[0])
    caption_text = ' '.join(context.args[1:])
    
    extra_caption = {
        "count": count,
        "text": caption_text
    }
    
    await update.message.reply_text(
        f"📝 Extra caption will be added to next {count} videos:\n"
        f"\"{caption_text}\""
    )

async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current download"""
    global cancel_requested, processing_task
    
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    if cancel_requested:
        await update.message.reply_text("⏳ A cancel is already pending!")
        return
    
    if not processing_task or processing_task.done():
        await update.message.reply_text("❌ No active download to cancel")
        return
    
    cancel_requested = True
    processing_task.cancel()
    await update.message.reply_text("🛑 Download cancelled! Cleaning up...")

async def handle_clean(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel + Clear queue"""
    global cancel_requested, processing_task, extra_caption
    
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    if processing_task and not processing_task.done():
        cancel_requested = True
        processing_task.cancel()
    
    async with queue_lock:
        while not download_queue.empty():
            download_queue.get_nowait()
        extra_caption = {"count": 0, "text": ""}
    
    await update.message.reply_text("🧹 Queue cleared! All pending links removed.")

async def handle_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip specified number of links in queue"""
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /skip <number_of_links_to_skip>")
        return
    
    skip_count = int(context.args[0])
    if skip_count <= 0:
        await update.message.reply_text("Please provide a positive number to skip")
        return
    
    async with queue_lock:
        queue_size = download_queue.qsize()
        
        if skip_count >= queue_size:
            await update.message.reply_text(f"⚠️ Skip count {skip_count} is larger than queue size {queue_size}. Clearing queue instead.")
            while not download_queue.empty():
                download_queue.get_nowait()
            extra_caption = {"count": 0, "text": ""}
            return
        
        skipped_links = []
        for _ in range(skip_count):
            if not download_queue.empty():
                link, _ = download_queue.get_nowait()
                skipped_links.append(link)
        
        if skipped_links:
            filename = f"Skipped_{len(skipped_links)}_Links.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(skipped_links))
            
            with open(filename, 'rb') as f:
                await update.message.reply_document(
                    document=InputFile(f, filename=filename),
                    caption=f"⏭️ Skipped {len(skipped_links)} links"
                )
            os.remove(filename)
        
        remaining = download_queue.qsize()
        await update.message.reply_text(
            f"⏭️ Successfully skipped {len(skipped_links)} links\n"
            f"📊 Remaining links in queue: {remaining}"
        )

async def handle_remain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show remaining links in queue"""
    if update.effective_user.id not in ADMIN_IDS:
        return

    links = []
    async with queue_lock:
        for item in list(download_queue._queue):
            links.append(item[0])
    
    if not links:
        await update.message.reply_text("✅ Queue is empty. No remaining links.")
        return

    filename = f"Remain_Links_{len(links)}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        for link in links:
            f.write(link + '\n')

    with open(filename, 'rb') as f:
        await update.message.reply_document(
            document=InputFile(f, filename=filename),
            caption=f"📄 {len(links)} links remaining."
        )
    os.remove(filename)

async def handle_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show supported sites count"""
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    count = len(SUPPORTED_SITES)
    await update.message.reply_text(
        f"🌐 Supported sites: {count}\n"
        "Send /support_file to get full list"
    )

async def handle_support_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send the full list of supported sites"""
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    if not SUPPORTED_SITES:
        await update.message.reply_text("❌ No supported sites recorded yet")
        return
    
    filename = "supported_sites.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("\n".join(sorted(SUPPORTED_SITES)))
    
    with open(filename, 'rb') as f:
        await update.message.reply_document(
            document=InputFile(f, filename=filename),
            caption=f"🌐 Supported Sites ({len(SUPPORTED_SITES)})"
        )
    os.remove(filename)

# Download and processing functions
async def send_video(update, context, path, caption, thumb_path):
    """Send video to chat and target group"""
    global extra_caption
    
    if extra_caption["count"] > 0:
        caption = f"{caption}\n\n{extra_caption['text']}"
        extra_caption["count"] -= 1
    
    try:
        with open(path, 'rb') as video_file:
            kwargs = {
                "video": InputFile(video_file),
                "caption": caption,
                "supports_streaming": True
            }
            if os.path.exists(thumb_path):
                with open(thumb_path, 'rb') as thumb_file:
                    kwargs["thumbnail"] = InputFile(thumb_file)
            
            msg = await update.message.reply_video(**kwargs)
            await asyncio.sleep(2.5)
            await context.bot.copy_message(
                chat_id=TARGET_GROUP_ID,
                from_chat_id=msg.chat.id,
                message_id=msg.message_id,
                protect_content=True
            )
    except Exception as e:
        logger.error(f"Upload failed: {e}")

async def countdown(update, seconds):
    """Show countdown before next download"""
    msg = await update.message.reply_text(f"⏳ Starting next link in {seconds}s...")
    for i in range(seconds - 1, 0, -1):
        await asyncio.sleep(1)
        try:
            await msg.edit_text(f"⏳ Starting next link in {i}s...")
        except Exception:
            break
    await msg.delete()

async def attempt_download(update: Update, url: str, ydl_opts: dict, method_name: str):
    """Attempt download with specific method"""
    global cancel_requested
    
    domain = get_domain(url)
    status_msg = await update.message.reply_text(f"🔄 Attempting {method_name} download...")
    
    try:
        ydl = YoutubeDL(ydl_opts)
        info = ydl.extract_info(url, download=True)
        
        if cancel_requested:
            raise asyncio.CancelledError()
            
        video_path = ydl.prepare_filename(info)
        if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
            await status_msg.edit_text(f"✅ {method_name} succeeded!")
            if domain:
                add_supported_site(domain)
            return info
        else:
            await status_msg.edit_text(f"⚠️ {method_name} failed: Empty file")
            return None
            
    except Exception as e:
        error_msg = str(e)[:200]
        await status_msg.edit_text(f"⚠️ {method_name} failed: {error_msg}")
        return None
    finally:
        await asyncio.sleep(1)  # Small delay between attempts

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    """Handle video download and processing"""
    global cancel_requested, part_upload_delay, full_video_caption
    tmpdir = tempfile.mkdtemp(prefix="tgvidbot_")
    os.chdir(tmpdir)

    def _check_cancel():
        if cancel_requested:
            raise asyncio.CancelledError()

    try:
        # First attempt with aria2c
        info = await attempt_download(update, url, aria2_opts, "aria2c")
        _check_cancel()
        
        # Fallback to yt-dlp if aria2c failed
        if not info:
            info = await attempt_download(update, url, internal_opts, "yt-dlp")
            _check_cancel()
            
            if not info:
                domain = get_domain(url) or url
                await update.message.reply_text(
                    f"❌ Both methods failed!\n"
                    f"Domain: {domain}\n"
                    f"Reason: Could not download video"
                )
                return

        # Process the downloaded video
        video_path = YoutubeDL(internal_opts).prepare_filename(info)
        title = info.get('title', 'Video')
        size = os.path.getsize(video_path)
        _check_cancel()

        if size <= SPLIT_THRESHOLD:
            thumb_path = os.path.join(tmpdir, 'thumb.jpg')
            extract_thumbnail(video_path, thumb_path)
            await update.message.reply_text("📤 Uploading full video...")
            _check_cancel()
            await send_video(update, context, video_path, f"🎬 {title}\n{full_video_caption}", thumb_path)
        else:
            await update.message.reply_text("✂️ Splitting into 45MB parts...")
            parts_dir = os.path.join(tmpdir, "parts")
            os.makedirs(parts_dir, exist_ok=True)
            parts = split_video_streamcopy(video_path, parts_dir, MAX_PART_MB)
            if not parts:
                parts = split_video_fallback_reencode(video_path, parts_dir, MAX_PART_MB)

            for i, part in enumerate(parts, 1):
                _check_cancel()
                thumb_path = os.path.join(tmpdir, f"thumb_{i}.jpg")
                extract_thumbnail(part, thumb_path)
                await update.message.reply_text(f"📤 Uploading part {i}/{len(parts)}...")
                await send_video(update, context, part, f"🎬 Part {i}/{len(parts)} - {title}", thumb_path)
                
                if i < len(parts) and part_upload_delay > 0:
                    await asyncio.sleep(part_upload_delay)

    except asyncio.CancelledError:
        logger.info("Download cancelled by user")
        raise
    except Exception as e:
        logger.error("Exception occurred", exc_info=True)
        await update.message.reply_text(f"❌ Processing error: {str(e)[:200]}")
    finally:
        os.chdir("..")
        shutil.rmtree(tmpdir, ignore_errors=True)

async def process_queue(context: ContextTypes.DEFAULT_TYPE):
    """Process download queue"""
    global processing_task, cancel_requested
    if processing_task and not processing_task.done():
        return

    async def _run():
        global cancel_requested
        processed_count = 0
        while not download_queue.empty():
            queue_size = download_queue.qsize() + processed_count
            cancel_requested = False
            link, update = await download_queue.get()
            try:
                processed_count += 1
                processing_msg = await update.message.reply_text(
                    f"🔄 Processing: {processed_count} / {queue_size}\n🔗 Link: {link}"
                )
                await handle_video(update, context, link)
                await processing_msg.delete()
                remain = queue_size - processed_count
                await update.message.reply_text(
                    f"✅ Last processed link: {processed_count} / {queue_size}\n"
                    f"Remain Links: {remain}\n\n"
                    f"🔗 Link: {link}"
                )
            except asyncio.CancelledError:
                logger.info("Download was cancelled")
                await update.message.reply_text("🛑 Process cancelled successfully!")
                await asyncio.sleep(15)
            except Exception as e:
                logger.error(f"Error processing {link}: {e}")

            remain = download_queue.qsize()
            if processed_count % 5 == 0 and remain > 0:
                filename = f"Remain_Links_{remain}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    for lnk, _ in list(download_queue._queue):
                        f.write(lnk + '\n')
                with open(filename, 'rb') as f:
                    await update.message.reply_document(
                        document=InputFile(f, filename=filename),
                        caption=f"📄 Processing {processed_count}/{queue_size} links in queue\nRemain: {remain}"
                    )
                os.remove(filename)

            if not download_queue.empty() and not cancel_requested:
                await countdown(update, processing_delay)

    processing_task = asyncio.create_task(_run())

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text or document input with URLs"""
    if update.effective_user.id not in ADMIN_IDS:
        return

    new_links = []

    if update.message.document:
        file = await update.message.document.get_file()
        file_path = await file.download_to_drive()
        with open(file_path, 'r') as f:
            lines = f.readlines()
        new_links = [line.strip() for line in lines if line.strip().startswith("http")]
        os.remove(file_path)
    elif update.message.text:
        new_links = [line.strip() for line in update.message.text.splitlines() if line.strip().startswith("http")]

    if not new_links:
        return

    async with queue_lock:
        for link in new_links:
            await download_queue.put((link, update))
        await update.message.reply_text(
            f"🆕 {len(new_links)} links added to list\n📊 Total Links in queue: {download_queue.qsize()}"
        )

    await process_queue(context)

def main():
    """Start the bot"""
    if not check_ffmpeg_installed():
        print("❌ ffmpeg/ffprobe not found. Please install them.")
        sys.exit(1)

    app = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("menu", handle_menu))
    app.add_handler(CommandHandler("capedit", handle_capedit))
    app.add_handler(CommandHandler("delay", handle_delay))
    app.add_handler(CommandHandler("slow", handle_slow))
    app.add_handler(CommandHandler("cap", handle_cap))
    app.add_handler(CommandHandler("cancel", handle_cancel))
    app.add_handler(CommandHandler("clean", handle_clean))
    app.add_handler(CommandHandler("skip", handle_skip))
    app.add_handler(CommandHandler("remain", handle_remain))
    app.add_handler(CommandHandler("support", handle_support))
    app.add_handler(CommandHandler("support_file", handle_support_file))
    
    # Message handlers
    app.add_handler(MessageHandler(filters.TEXT | filters.Document.MimeType("text/plain"), handle_input))
    
    logger.info("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
