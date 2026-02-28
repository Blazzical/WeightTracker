# WeightTracker

A simple, self-hosted calorie and weight tracking web app that runs locally on your PC and is accessible from your phone.

## Quick Start (Windows)

### 1. Install Python

Download Python from [python.org](https://www.python.org/downloads/) (3.10 or newer).

During installation, **check the box that says "Add Python to PATH"**. This is important.

### 2. Download WeightTracker

Either clone this repo or download and extract the ZIP:

```
git clone https://github.com/Blazzical/WeightTracker.git
```

### 3. Install Dependencies

Double-click **`setup.bat`** in the WeightTracker folder. This installs Flask, pystray, and Pillow.

Alternatively, open a terminal in the folder and run:

```
pip install -r requirements.txt
```

### 4. Run the App

Double-click **`run.bat`**. This will:

- Start the web server on port 5001
- Add a green **W** icon to your system tray
- Open the app in your browser at [http://localhost:5001](http://localhost:5001)

Right-click the tray icon to **Open in Browser**, **Restart**, or **Quit**.

You can also run it manually with:

```
python app.py
```

This opens the browser but doesn't create the tray icon.

## Accessing from Your Phone (Tailscale)

Tailscale lets you securely access your PC from your phone over the internet, without port forwarding.

### 1. Create a Tailscale Account

Go to [tailscale.com](https://tailscale.com/) and sign up (it's free for personal use).

### 2. Install Tailscale on Your PC

Download from [tailscale.com/download](https://tailscale.com/download) and sign in.

Once running, Tailscale assigns your PC a name (e.g. `my-desktop`) and an IP (e.g. `100.x.y.z`). You can find these in the Tailscale system tray icon.

### 3. Install Tailscale on Your Phone

Download the Tailscale app from the App Store (iOS) or Google Play (Android) and sign in with the same account.

### 4. Open WeightTracker on Your Phone

With both devices on Tailscale, open your phone's browser and go to:

```
http://my-desktop:5001
```

Replace `my-desktop` with your PC's Tailscale name or IP. Bookmark it for easy access.

> **Tip:** Your PC needs to be on and running WeightTracker for this to work. Tailscale handles the rest, even across different Wi-Fi networks.

## Usage Overview

- **Today** - Log meals, weight, and exercise for the current day
- **Components** - Individual food items with nutritional info (kJ, calories, protein)
- **Meals** - Combine components into reusable meals
- **History** - View past days with trend charts and stats
- **Targets** - Set daily calorie/protein goals and quick-add shortcuts

## Data Storage

All data is stored locally in a SQLite database file (`weight_tracker.db`) in the app folder. Back up this file to preserve your data.
