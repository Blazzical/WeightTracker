"""Run WeightTracker as a system tray icon."""

import subprocess
import sys
import threading
import webbrowser
import os

# Ensure we're in the right directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from PIL import Image, ImageDraw, ImageFont
import pystray

from app import app

URL = 'http://localhost:5001'


def create_icon_image():
    """Create a simple green 'W' icon."""
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([2, 2, 62, 62], fill='#198754')
    try:
        font = ImageFont.truetype('arial.ttf', 36)
    except OSError:
        font = ImageFont.load_default()
    draw.text((32, 30), 'W', fill='white', font=font, anchor='mm')
    return img


def open_browser(icon, item):
    webbrowser.open(URL)


def restart_app(icon, item):
    icon.stop()
    pythonw = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
    subprocess.Popen(
        [pythonw, os.path.abspath(__file__)],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        creationflags=subprocess.DETACHED_PROCESS,
    )
    os._exit(0)


def quit_app(icon, item):
    icon.stop()
    os._exit(0)


def run_flask():
    app.run(debug=False, host='0.0.0.0', port=5001, use_reloader=False)


if __name__ == '__main__':
    server = threading.Thread(target=run_flask, daemon=True)
    server.start()

    threading.Timer(1.5, lambda: webbrowser.open(URL)).start()

    icon = pystray.Icon(
        'WeightTracker',
        create_icon_image(),
        'WeightTracker',
        menu=pystray.Menu(
            pystray.MenuItem('Open in Browser', open_browser, default=True),
            pystray.MenuItem('Restart', restart_app),
            pystray.MenuItem('Quit', quit_app),
        )
    )
    icon.run()
