import os
import shutil
import json
import subprocess
from datetime import datetime, timedelta
from assistant.selah_brain import call_gemini

def get_downloads_folder():
    """
    Returns the standard downloads folder for the user on Windows.
    """
    return os.path.join(os.environ.get('USERPROFILE', os.path.expanduser('~')), 'Downloads')

def clean_downloads_folder(days=7):
    """
    Moves files in the Downloads folder that are older than N days into an Archive folder.
    """
    downloads = get_downloads_folder()
    if not os.path.exists(downloads):
        return f"Error: Downloads directory '{downloads}' does not exist."

    archive_dir = os.path.join(downloads, "Archived_Downloads")
    os.makedirs(archive_dir, exist_ok=True)

    moved_files = []
    errors = []
    cutoff = datetime.now() - timedelta(days=days)

    for item in os.listdir(downloads):
        item_path = os.path.join(downloads, item)
        # Skip directories
        if os.path.isdir(item_path):
            continue
        
        # Check file modification time
        mtime = datetime.fromtimestamp(os.path.getmtime(item_path))
        if mtime < cutoff:
            try:
                shutil.move(item_path, os.path.join(archive_dir, item))
                moved_files.append(item)
            except Exception as e:
                errors.append(f"Error moving {item}: {str(e)}")

    log = f"[SYS_AGENT] Scanned: {downloads}\n"
    if moved_files:
        log += f"✅ Successfully archived {len(moved_files)} files older than {days} days:\n"
        log += "\n".join(f"- {f} -> Archived_Downloads/" for f in moved_files)
    else:
        log += "🟢 No files older than the specified age found to clean."

    if errors:
        log += "\n⚠️ Warnings:\n" + "\n".join(errors)
    return log

def convert_png_to_jpg(folder="downloads"):
    """
    Scans a folder (default: Downloads) and converts all PNG files to JPEG format.
    """
    target_dir = get_downloads_folder() if folder == "downloads" else folder
    if not os.path.exists(target_dir):
        return f"Error: Directory '{target_dir}' does not exist."

    try:
        from PIL import Image
    except ImportError:
        return "Error: Image conversion requires the 'Pillow' library. Run: pip install Pillow"

    converted_files = []
    errors = []

    for item in os.listdir(target_dir):
        if item.lower().endswith('.png'):
            png_path = os.path.join(target_dir, item)
            jpg_name = os.path.splitext(item)[0] + ".jpg"
            jpg_path = os.path.join(target_dir, jpg_name)
            
            try:
                with Image.open(png_path) as img:
                    # Convert transparent background to white if present
                    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                        bg = Image.new('RGB', img.size, (255, 255, 255))
                        bg.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else img.convert('RGBA').split()[3])
                        bg.save(jpg_path, 'JPEG', quality=90)
                    else:
                        img.convert('RGB').save(jpg_path, 'JPEG', quality=90)
                
                # Archive the original PNG in an 'Archived_PNGs' subfolder
                archive_dir = os.path.join(target_dir, "Archived_PNGs")
                os.makedirs(archive_dir, exist_ok=True)
                shutil.move(png_path, os.path.join(archive_dir, item))
                
                converted_files.append(f"{item} -> {jpg_name}")
            except Exception as e:
                errors.append(f"Failed to convert {item}: {str(e)}")

    log = f"[SYS_AGENT] Scanned Directory: {target_dir}\n"
    if converted_files:
        log += f"✅ Converted {len(converted_files)} PNG files to JPEG format:\n"
        log += "\n".join(f"- {entry}" for entry in converted_files)
    else:
        log += "🟢 No PNG files found to convert."

    if errors:
        log += "\n⚠️ Warnings:\n" + "\n".join(errors)
    return log

def start_dev_environment():
    """
    Spawns a new Windows Command Prompt terminal running 'npm run dev' inside the frontend project.
    """
    frontend_dir = "c:\\Repo\\SELAH\\selah-frontend"
    if not os.path.exists(frontend_dir):
        return f"Error: Frontend directory '{frontend_dir}' not found."

    try:
        # Launch cmd.exe in a separate subprocess, executing the dev server and leaving the window open (/k)
        subprocess.Popen("start cmd /k npm run dev", shell=True, cwd=frontend_dir)
        return "[SYS_AGENT] ✅ Dev Environment Initialized:\n- Spawns terminal at `c:\\Repo\\SELAH\\selah-frontend`\n- Triggered `npm run dev` script."
    except Exception as e:
        return f"Error spawning dev server: {str(e)}"

def execute_raw_system_command(cmd_string):
    """
    Executes a raw system shell command securely inside a subprocess,
    capturing and returning stdout and stderr.
    """
    cmd_clean = cmd_string.strip()
    if cmd_clean.lower().startswith("cd "):
        return (
            f"[SYS_EXEC] Command: {cmd_clean}\n"
            f"⚠️ Note: 'cd' in a stateless terminal session does not persist directory changes.\n"
            f"Tip: Chain your commands using '&&' (e.g., 'cd my_dir && dir') to execute within a specific folder."
        )

    try:
        # Standard shell execution allows commands like dir, echo, git, npm, etc.
        result = subprocess.run(
            cmd_clean,
            shell=True,
            capture_output=True,
            text=True,
            timeout=15, # 15 second timeout to prevent blocking
            cwd=os.environ.get('USERPROFILE', os.path.expanduser('~'))
        )
        
        output = f"[SYS_EXEC] Command: {cmd_string}\n"
        if result.returncode == 0:
            stdout_text = result.stdout.strip()
            output += f"✅ Success (exit code 0):\n{stdout_text if stdout_text else '[No stdout output]'}"
        else:
            stderr_text = result.stderr.strip()
            stdout_text = result.stdout.strip()
            output += f"❌ Failed (exit code {result.returncode}):\n{stderr_text if stderr_text else stdout_text}"
        return output
    except subprocess.TimeoutExpired:
        return f"[SYS_EXEC] ❌ Command timed out after 15 seconds: {cmd_string}"
    except Exception as e:
        return f"[SYS_EXEC] ❌ Execution failed: {str(e)}"

def dispatch_os_command(natural_query):
    """
    Translates user query using Gemini into a structured JSON dispatch action,
    or executes a raw system command directly.
    """
    q = natural_query.strip()
    q_lower = q.lower()

    # 1. Direct Prefix Check (extremely fast bypass)
    if q_lower.startswith("cmd:") or q_lower.startswith("run:"):
        raw_cmd = q.split(":", 1)[1].strip()
        return execute_raw_system_command(raw_cmd)

    # 2. Check if the user query matches one of our three specific custom natural language automation tasks.
    is_clean = any(kw in q_lower for kw in ["clean downloads", "clean up downloads", "archive downloads", "sweep downloads"])
    is_dev = any(kw in q_lower for kw in ["start dev", "dev environment", "start developer", "initialize dev", "npm run dev"])
    is_convert = any(kw in q_lower for kw in ["convert png", "convert images", "png to jpg", "png to jpeg"])

    if is_clean:
        import re
        days_match = re.search(r'\b(\d+)\b', q)
        days = int(days_match.group(1)) if days_match else 7
        return clean_downloads_folder(days)
    elif is_dev:
        return start_dev_environment()
    elif is_convert:
        return convert_png_to_jpg("downloads")

    # 3. For any other query, execute it instantly as a raw shell command!
    # This provides a real, fast terminal prompt experience.
    return execute_raw_system_command(q)
