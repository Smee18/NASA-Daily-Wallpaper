import requests
import os
import ctypes
import sys
import shutil
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from datetime import datetime, timedelta


shutil.rmtree('images/mars_pics', ignore_errors=True)
API_KEY = {} ##SET YOUR API HERE AS A STRING

manifest_url = f"https://api.nasa.gov/mars-photos/api/v1/manifests/curiosity?api_key={API_KEY}"
manifest_response = requests.get(manifest_url)
manifest_data = manifest_response.json()['photo_manifest']
max_sol = manifest_data['max_sol']
landing_date_str = manifest_data['landing_date']
landing_date = datetime.strptime(landing_date_str, "%Y-%m-%d")
print(f"Latest sol with photos: {max_sol}")

url_APOD = f"https://api.nasa.gov/planetary/apod?api_key={API_KEY}"
url_MARS = f"https://api.nasa.gov/mars-photos/api/v1/rovers/curiosity/photos?sol={max_sol}&api_key={API_KEY}"

response_APOD = requests.get(url_APOD)
if response_APOD.status_code != 200:
    raise Exception(f"Failed to fetch APOD: {response_APOD.status_code}")

response_MARS = requests.get(url_MARS)
if response_MARS.status_code != 200:
    raise Exception(f"Failed to fetch Rover pics: {response_MARS.status_code}")

data_APOD = response_APOD.json()
data_MARS = response_MARS.json()

print(data_APOD, '\n')

print(data_MARS)

# Only proceed if it's an image
if data_APOD.get('media_type') != 'image':
    print(f"Today's APOD is not an image. It's a {data_APOD['media_type']}. URL: {data_APOD['url']}")
    sys.exit(1)

image_url = data_APOD.get('hdurl') or data_APOD.get('url')
image_date = data_APOD.get('date')
mars_photos = data_MARS['photos']

# Ensure 'images' and 'mars_pics' directory exists
os.makedirs('images', exist_ok=True)
os.makedirs('images/mars_pics', exist_ok=True)

for i, photo in enumerate(mars_photos, start=1):
    img_url = photo['img_src']
    camera = photo['camera']['name']
    img_data = requests.get(img_url).content
    file_path = f'images/mars_pics/sol_{max_sol}-{camera}_{i}.jpg'
    with open(file_path, 'wb') as file:
        file.write(img_data)
    print(f"Saved {file_path}")


img_response = requests.get(image_url)
if img_response.status_code == 200:
    image_path = f'images/{image_date}.jpg'
    with open(image_path, 'wb') as file:
        file.write(img_response.content)
    print(f"Saved: {image_path}")
else:
    raise Exception(f"Failed to download image: {img_response.status_code}")

# --- CONFIG ---
wallpaper_size = (1920, 1080)
left_width = wallpaper_size[0] // 2 + 50
right_width = wallpaper_size[0] - left_width
background_color = (0, 0, 0)

apod_path = image_path
rover_paths = []

directory = Path("images/mars_pics")
mars_files = list(directory.glob("*.jpg")) + list(directory.glob("*.jpeg"))
for img in mars_files:
    if len(rover_paths) == 4:
        break
    elif 'NAV' in img.name:
        rover_paths.append(img)


# --- Create blank wallpaper ---
wallpaper = Image.new("RGB", wallpaper_size, background_color)

# --- LEFT HALF: APOD IMAGE ---
apod_img = Image.open(apod_path)

# Fit APOD image into left half (maintain aspect ratio)
apod_img.thumbnail((left_width, wallpaper_size[1] - 150), Image.LANCZOS)
apod_x = (left_width - apod_img.width) // 2
apod_y = 50
wallpaper.paste(apod_img, (apod_x, apod_y))

# --- RIGHT HALF: ROVER PICS (1x3 grid) ---
cols, rows = 2, 2
img_w = round(right_width / (cols + 0.6))
img_h = round(wallpaper_size[1] / (rows + 0.6))

for idx, rover_path in enumerate(rover_paths[:4]):
    img = Image.open(rover_path)
    img.thumbnail((img_w, img_h), Image.LANCZOS)
    x = left_width + (idx % cols) * img_w + (img_w - img.width) // 2
    y = (idx // cols) * img_h + (img_h - img.height) // 2
    wallpaper.paste(img, (x + ((30 * idx) %60), y + 20))

sol_length_hours = 24 + 39/60 + 35/3600

now = datetime.now()
elapsed_hours = (now - landing_date).total_seconds() / 3600
current_sol = int(elapsed_hours / sol_length_hours)
days_since_landing = (now - landing_date).days

# Text
d = ImageDraw.Draw(wallpaper)
myFont = ImageFont.load_default(size=30)
d.text((1200, 860), f"Pictures taken on sol {max_sol}", fill=(255, 255, 255, 255), font=myFont)
d.text((970, 950), f"Curiosity has been on Mars for {current_sol} sols or {days_since_landing} earth days", fill=(255, 255, 255, 255), font=myFont)


# Save
wallpaper.save("final_wallpaper.jpg")
print("Wallpaper created: final_wallpaper.jpg")


abs_path = os.path.abspath("final_wallpaper.jpg")

# Windows API constants
SPI_SETDESKWALLPAPER = 20
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDWININICHANGE = 0x02

try:
    ctypes.windll.user32.SystemParametersInfoW(
        SPI_SETDESKWALLPAPER, 0, abs_path, SPIF_UPDATEINIFILE | SPIF_SENDWININICHANGE
    )
    print(f"Wallpaper set successfully to {abs_path}")
except Exception as e:
    print(f"Error changing wallpaper: {e}")
