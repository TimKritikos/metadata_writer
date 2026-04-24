#!/usr/bin/env python

#  web_metadata_writer.py --  python app to record media metadata
#
#   Copyright 2025 Efthymios Kritikos
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.

#TODO:
#Weather image is cropped
#Make save button red if any data is unparsable
#Add timezone setting for exif date
#Change the background of TitledFrames from the window background
#Make computationally heavy processes like searching for a point in gpx file in a separate thread asynchronously
#Do doable TODOs
#Maybe add these colors to widgets:
#   RED: assumed need to check
#   GREEN: previously written
#   GREY: recorded as not recorded

import sys
import hashlib
import json
import os
from datetime import datetime
from datetime import timezone
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from fractions import Fraction
import gpxpy
import gpxpy.gpx
import time
import base64
import io

app = Flask(__name__)

# Global state to hold current image data
current_data = {}
current_image_path = None

def sha512Checksum(filePath):
    with open(filePath, 'rb') as fh:
        m = hashlib.sha512()
        while True:
            data = fh.read(8192)
            if not data:
                break
            m.update(data)
        return m.hexdigest()

def nautical_to_decimal(value):
    d = float(value[0])
    m = float(value[1])
    s = float(value[2])
    return d + (m / 60.0) + (s / 3600.0)

def load_image_metadata(image_path):
    """Load metadata from image file"""
    data = {
        "program_version": "v1.0-dev",
        "data_spec_version": "v1.0-dev",

        "events" : [{
                        "event_id":0,
                        "event_type": "capture_start",
                        "timestamp": 0,
                        "timestamp_accuracy_seconds": 0,

                        "text": ""
                    },
                    #{
                    #   "event_id":2,
                    #   "event_type": "data_modification",
                    #   "timestamp": 1741745288,
                    #   "text": "Raw file developed"
                    #},
                    {
                        "event_id":1,
                        "event_type": "metadata_modification",
                        "timestamp": int(time.time()),
                        "timestamp_accuracy_seconds": 0,

                        "text": "Initial metadata written",
                        "modified_metadata_modules":[
                                "texts",
                                "capture_timestamp",
                                "constants",
                                "geolocation_data"
                            ]
                    },
                    ],
        "texts": {
            "title" : "",
            "description" : "",
        },
        "capture_timestamp": {
            "capture_start_on_original_metadata_timestamp": -1,
            "capture_duration_seconds": -1,
            "single_capture_picture": True,
            "capture_start_time_offset_seconds": 0,
        },
        "geolocation_data" : {
            "have_data": False,
            "valid_data_source": "uninitialised",
            "display_map_tile_server" : "",
            "source_gnss_track_file":{
                "have_data": False,
                "Latitude_decimal": 100000,
                "Longitude_decimal": 100000,
                "gnss_device_time_offset_seconds": 0,
                "file_path": "",
                "file_sha512sum":"",
                "file_type": ""
            },
            "source_original_media_file":{
                "have_data": False,
                "Latitude_decimal": 100000,
                "Longitude_decimal": 100000,
            },
            "source_manual_entry":{
                "have_data": False,
                "Latitude_decimal": 100000,
                "Longitude_decimal": 100000,
            }
        },
        "constants": {
            "image_sha512": sha512Checksum(image_path),
            "image_file_full_path": os.path.realpath(image_path)
        }
    }

    # Get exif from image file
    image = Image.open(image_path)
    exif_data = image._getexif()

    if exif_data:
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == 'ExposureTime':
                data["capture_timestamp"]["capture_duration_seconds"] = float(Fraction(value))
            elif tag == 'DateTimeOriginal':
                dt_str = value
                dt = datetime.strptime(dt_str, '%Y:%m:%d %H:%M:%S')
                utc_dt = dt.replace(tzinfo=timezone.utc)
                data["capture_timestamp"]["capture_start_on_original_metadata_timestamp"] = int(utc_dt.timestamp())
                data["events"][0]["timestamp"] = int(utc_dt.timestamp())
            elif tag == 'GPSInfo':
                latitude_nautical = None
                latitude_nautical_ref = None
                longitude_nautical = None
                longitude_nautical_ref = None
                for t in value:
                    sub_decoded = GPSTAGS.get(t, t)
                    if sub_decoded == "GPSLatitude":
                        latitude_nautical = value[t]
                    elif sub_decoded == "GPSLatitudeRef":
                        latitude_nautical_ref = value[t]
                    elif sub_decoded == "GPSLongitude":
                        longitude_nautical = value[t]
                    elif sub_decoded == "GPSLongitudeRef":
                        longitude_nautical_ref = value[t]

                if latitude_nautical and latitude_nautical_ref and longitude_nautical and longitude_nautical_ref:
                    latitude_decimal = nautical_to_decimal(latitude_nautical)
                    if latitude_nautical_ref != "N":
                        latitude_decimal = 0 - latitude_decimal

                    longitude_decimal = nautical_to_decimal(longitude_nautical)
                    if longitude_nautical_ref != "E":
                        longitude_decimal = 0 - longitude_decimal

                    data["geolocation_data"]["source_original_media_file"]["Latitude_decimal"] = latitude_decimal
                    data["geolocation_data"]["source_original_media_file"]["Longitude_decimal"] = longitude_decimal
                    data["geolocation_data"]["source_original_media_file"]["have_data"] = True

    # Try to find GPX file
    try_gpx_files(data, image_path)

    # Set default geolocation source
    if data["geolocation_data"]["source_original_media_file"]["have_data"]:
        data["geolocation_data"]["valid_data_source"] = "source_original_media_file"
        data["geolocation_data"]["have_data"] = True
    elif data["geolocation_data"]["source_gnss_track_file"]["have_data"]:
        data["geolocation_data"]["valid_data_source"] = "source_gnss_track_file"
        data["geolocation_data"]["have_data"] = True

    return data

def try_gpx_files(data, image_path):
    """Search for GPX files and extract location data"""
    gpx_search_dir = os.path.dirname(image_path)
    capture_timestamp = data["events"][0]["timestamp"]

    for file in os.listdir(gpx_search_dir):
        if file.endswith(".gpx"):
            filepath = os.path.join(gpx_search_dir, file)
            try:
                with open(filepath, 'r') as gpx_file:
                    gpx = gpxpy.parse(gpx_file)
                    for track in gpx.tracks:
                        for segment in track.segments:
                            for point in segment.points:
                                offset = data["geolocation_data"]["source_gnss_track_file"]["gnss_device_time_offset_seconds"]
                                if point.time == datetime.fromtimestamp(capture_timestamp - offset, tz=timezone.utc):
                                    data["geolocation_data"]["source_gnss_track_file"]["Longitude_decimal"] = point.longitude
                                    data["geolocation_data"]["source_gnss_track_file"]["Latitude_decimal"] = point.latitude
                                    data["geolocation_data"]["source_gnss_track_file"]["file_path"] = filepath
                                    data["geolocation_data"]["source_gnss_track_file"]["file_sha512sum"] = sha512Checksum(filepath)
                                    data["geolocation_data"]["source_gnss_track_file"]["file_type"] = "gpx"
                                    data["geolocation_data"]["source_gnss_track_file"]["have_data"] = True
                                    return
            except:
                continue

@app.route('/')
def index():
    """Main page"""
    if not current_image_path:
        return "No image loaded. Please start the application with an image path.", 400
    return render_template('index.html')

@app.route('/api/metadata', methods=['GET'])
def get_metadata():
    """Get current metadata"""
    return jsonify(current_data)

@app.route('/api/metadata', methods=['POST'])
def update_metadata():
    """Update metadata"""
    global current_data
    updates = request.json

    # Update texts
    if 'texts' in updates:
        current_data['texts'].update(updates['texts'])

    # Update capture timestamp
    if 'capture_timestamp' in updates:
        current_data['capture_timestamp'].update(updates['capture_timestamp'])
        # Update event timestamp
        current_data['events'][0]['timestamp'] = (
            current_data['capture_timestamp']['capture_start_on_original_metadata_timestamp'] +
            int(current_data['capture_timestamp']['capture_start_time_offset_seconds'])
        )
        # Re-search GPX files if timestamp changed
        try_gpx_files(current_data, current_image_path)

    # Update geolocation
    if 'geolocation_data' in updates:
        if 'source_manual_entry' in updates['geolocation_data']:
            current_data['geolocation_data']['source_manual_entry'].update(
                updates['geolocation_data']['source_manual_entry']
            )
        if 'valid_data_source' in updates['geolocation_data']:
            current_data['geolocation_data']['valid_data_source'] = updates['geolocation_data']['valid_data_source']
            source = current_data['geolocation_data']['valid_data_source']
            current_data['geolocation_data']['have_data'] = current_data['geolocation_data'][source]['have_data']
        if 'display_map_tile_server' in updates['geolocation_data']:
            current_data['geolocation_data']['display_map_tile_server'] = updates['geolocation_data']['display_map_tile_server']
        if 'source_gnss_track_file' in updates['geolocation_data']:
            if 'gnss_device_time_offset_seconds' in updates['geolocation_data']['source_gnss_track_file']:
                current_data['geolocation_data']['source_gnss_track_file']['gnss_device_time_offset_seconds'] = \
                    updates['geolocation_data']['source_gnss_track_file']['gnss_device_time_offset_seconds']
                try_gpx_files(current_data, current_image_path)

    return jsonify(current_data)

@app.route('/api/save', methods=['POST'])
def save_metadata():
    """Save metadata to JSON file"""
    output_path = Path(current_data["constants"]["image_file_full_path"]).with_suffix(".json")

    with open(output_path, "w") as f:
        json.dump(current_data, f, indent=4)

    return jsonify({"success": True, "path": str(output_path)})

@app.route('/api/image')
def get_image():
    """Serve the current image"""
    if not current_image_path:
        return "No image loaded", 404

    # Create thumbnail
    img = Image.open(current_image_path)
    img.thumbnail((800, 800))

    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG')
    img_str = base64.b64encode(buffer.getvalue()).decode()

    return jsonify({"image": f"data:image/jpeg;base64,{img_str}"})

def main():
    global current_data, current_image_path

    if len(sys.argv) < 2:
        print("Usage: python web_metadata_writer.py path_to_image")
        sys.exit(1)

    current_image_path = sys.argv[1]

    if not os.path.exists(current_image_path):
        print(f"Error: Image file not found: {current_image_path}")
        sys.exit(1)

    print(f"Loading metadata for: {current_image_path}")
    current_data = load_image_metadata(current_image_path)

    print("\nStarting web server...")
    print("Open your browser to: http://localhost:5000")
    print("Press Ctrl+C to stop the server and exit")

    app.run(debug=True, port=5000)

if __name__ == "__main__":
    main()
