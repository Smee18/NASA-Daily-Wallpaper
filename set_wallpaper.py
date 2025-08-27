import requests
import os
import ctypes
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from datetime import datetime
import shutil
from dotenv import load_dotenv

# --- CONFIG ---
load_dotenv() # This loads the .env file
API_KEY = os.getenv("API_KEY")
wallpaper_size = (1920, 1080)
padding = 20
background_color = (0, 0, 0)
text_color = (255, 255, 255)
font_path = "arial.ttf"  # Ensure this exists on your system
font_small = ImageFont.truetype(font_path, 28)
shutil.rmtree('images/mars_pics', ignore_errors=True)
shutil.rmtree('images/APOD', ignore_errors=True)

# --- Get Manifest Data ---
manifest_url = f"https://api.nasa.gov/mars-photos/api/v1/manifests/perseverance?api_key={API_KEY}"
manifest_response = requests.get(manifest_url)
if manifest_response.status_code != 200:
    raise Exception(f"Failed to fetch Rover info: {manifest_response.status_code}")

manifest_data = manifest_response.json()['photo_manifest']
max_sol = manifest_data['max_sol']
landing_date_str = manifest_data['landing_date']
landing_date = datetime.strptime(landing_date_str, "%Y-%m-%d")
print(f"Latest sol with photos: {max_sol}")



# --- Fetch APOD ---
url_APOD = f"https://api.nasa.gov/planetary/apod?api_key={API_KEY}"
response_APOD = requests.get(url_APOD)
if response_APOD.status_code != 200:
    raise Exception(f"Failed to fetch APOD: {response_APOD.status_code}")

data_APOD = response_APOD.json()
if data_APOD.get('media_type') != 'image':
    print(f"Today's APOD is not an image. It's a {data_APOD['media_type']}. URL: {data_APOD['url']}")

image_url = data_APOD.get('hdurl') or data_APOD.get('url')
image_date = data_APOD.get('date')
explanation = data_APOD.get('explanation')

# Fetch Mastcam-Z images, loop backwards if none found
url_MARS = "https://api.nasa.gov/mars-photos/api/v1/rovers/perseverance/photos"
sol = max_sol
mars_photos = []

while sol > 0 and not mars_photos:
    params = {"sol": sol, "camera": "MCZ_LEFT", "api_key": API_KEY}
    response = requests.get(url_MARS, params=params)
    response.raise_for_status()
    mars_photos = response.json().get('photos', [])
    if mars_photos:
        print(f"Found Mastcam-Z images on sol {sol}")
        break
    sol -= 1

if not mars_photos:
    raise Exception("No Mastcam-Z images available at all.")

# --- Ensure Directories ---
os.makedirs('images/APOD', exist_ok=True)
os.makedirs('images/mars_pics', exist_ok=True)

# --- Download new images ---
for i, photo in enumerate(mars_photos, start=1):
    img_url = photo['img_src']
    camera = photo['camera']['name']
    img_data_mars = requests.get(img_url)
    if img_data_mars.status_code == 200:
        file_path = f'images/mars_pics/sol_{max_sol}-{camera}_{i}.jpg'
        with open(file_path, 'wb') as file:
            file.write(img_data_mars.content)
        print(f"Saved {file_path}")

# --- Save APOD ---
img_data_APOD = requests.get(image_url)
if img_data_APOD.status_code == 200:
    APOD_image_path = f'images/APOD/{image_date}.jpg'
    with open(APOD_image_path, 'wb') as file:
        file.write(img_data_APOD.content)
    print(f"Saved APOD: {APOD_image_path}")
else:
    raise Exception(f"Failed to download APOD image: {img_data_APOD.status_code}")

# --- Select Mastcam Images ---
mars_files = list(Path("images/mars_pics").glob("*.jpg")) + list(Path("images/mars_pics").glob("*.jpeg"))

# Find the largest file by size
max_size = 0
max_i = 0
for i, img_path in enumerate(mars_files):
    size_mb = img_path.stat().st_size / (1024 * 1024)  # Convert bytes to MB
    if size_mb > max_size:
        max_i = i
        max_size = size_mb


# --- Config ---
wallpaper_size = (1920, 1080)
padding = 30
background_color = (0, 0, 0)
text_color = (255, 255, 255)
font_path = "arial.ttf"  # Replace with a valid font path
font_small = ImageFont.truetype(font_path, 20)
font_medium = ImageFont.truetype(font_path, 25)

# --- Paths ---
apod_path = APOD_image_path
rover_paths = [mars_files[max_i]]

# --- Wallpaper base ---
wallpaper = Image.new("RGB", wallpaper_size, background_color)
draw = ImageDraw.Draw(wallpaper)

left_width = wallpaper_size[0] // 2
right_width = wallpaper_size[0] - left_width

# --- LEFT: APOD ---
apod_img = Image.open(apod_path)
max_apod_height = wallpaper_size[1] - 2 * padding - 350  # leave 300px for text
apod_img.thumbnail((left_width - 2 * padding, max_apod_height), Image.LANCZOS)
apod_x = (left_width - apod_img.width) // 2
apod_y = padding
wallpaper.paste(apod_img, (apod_x, apod_y))

# APOD explanation text box
text_box_x0 = padding + 50
text_box_y0 = apod_y + apod_img.height + 20
text_box_x1 = left_width - padding
text_box_y1 = wallpaper_size[1] - padding
text_box_width = text_box_x1 - text_box_x0


# Simple line-wrapping function
def draw_text_box(draw, text, font, box_x0, box_y0, box_x1, box_y1, line_spacing=4):
    words = text.split()
    lines = []
    line = ""
    for word in words:
        test_line = line + " " + word if line else word
        bbox = draw.textbbox((0, 0), test_line, font=font)
        w = bbox[2] - bbox[0]
        if w <= (box_x1 - box_x0 - 2*padding):
            line = test_line
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)

    x, y = box_x0 + padding, box_y0
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_height = bbox[3] - bbox[1]
        if y + line_height > box_y1:
            break  # Stop if we exceed box
        draw.text((x, y), line, fill=text_color, font=font)
        y += line_height + line_spacing

draw_text_box(draw, explanation, font_small, text_box_x0, text_box_y0, text_box_x1, text_box_y1)

# --- RIGHT: Mastcam ---
rover_img = Image.open(rover_paths[0])
rover_img.thumbnail((right_width - 3 * padding, wallpaper_size[1] - 3 * padding), Image.LANCZOS)
rover_x = left_width + (right_width - rover_img.width) // 2
rover_y = (wallpaper_size[1] - rover_img.height) // 2
wallpaper.paste(rover_img, (rover_x - 80, rover_y))

# Mastcam info
now = datetime.now()
sol_length_hours = 24 + 39/60 + 35/3600
elapsed_hours = (now - landing_date).total_seconds() / 3600
current_sol = int(elapsed_hours / sol_length_hours)
days_since_landing = (now - landing_date).days

info_textA = f"Perseverance Mastcam - Latest Sol: {max_sol}"
info_textB = f"On Mars for {current_sol} sols ({days_since_landing} Earth days)"
draw_text_box(draw, info_textA, font_medium, left_width + padding, rover_y + rover_img.height + 10,
            wallpaper_size[0] - padding, wallpaper_size[1] - padding)
draw_text_box(draw, info_textB, font_medium, left_width + padding, rover_y + rover_img.height + 50,
            wallpaper_size[0] - padding, wallpaper_size[1] - padding)


# --- Save ---
wallpaper.save("final_wallpaper.jpg")
print("Wallpaper created: final_wallpaper.jpg")


# --- Set as Windows Wallpaper ---
abs_path = os.path.abspath("final_wallpaper.jpg")
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

