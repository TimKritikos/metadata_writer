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
import argparse
import gzip
import hashlib
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime
from datetime import timezone
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory, send_file
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import gpxpy
import gpxpy.gpx
import time
import base64
import io
import secrets
from fractions import Fraction

app = Flask(__name__)

# Global state to hold current image data
current_data = {}
current_image_path = None
session_key = None
gramps_people = []

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

        "events" : [
            #{
            #    "event_id":2,
            #    "event_type": "data_modification",
            #    "time": {
            #        "mode": "dated",
            #        "start": 0.0,
            #        "end": 0.0,
            #        "provenance": {"type": "text", "description": ""}
            #    },
            #    "text": "Raw file developed"
            #},
            {
                "event_id":1,
                "event_type": "metadata_modification",
                "time": {
                    "mode": "dated",
                    "start": time.time(),
                    "end": time.time(),
                    "provenance": {
                        "type": "template",
                        "template": "current_time"
                    }
                },
                "text": "Initial metadata written",
                "modified_metadata_modules":[
                    "texts",
                    "capture_timestamp",
                    "constants",
                    "geolocation_data"
                ]
            }
        ],
        "texts": {
            "title" : "",
            "description" : "",
        },
        "geolocation_data" : {
            "have_data": False,
            "valid_data_source": "uninitialised",
            "display_map_tile_server" : "Google Maps satellite online",
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
        "exposure_data": {
            "multiple_exposures": False,
            "source": "source_manual",
            "source_exif": {
                "have_data": False,
                "iso": None,
                "aperture": None,
                "shutter_speed": None
            },
            "source_manual": {
                "iso": None,
                "aperture": None,
                "shutter_speed": None
            }
        },
        "constants": {
            "image_sha512": sha512Checksum(image_path),
            "image_file_full_path": os.path.realpath(image_path)
        },
        "subjects": {
            "gramps_file_path": "",
            "gramps_file_sha512": "",
            "list": []
        }
    }

    # Get exif from image file
    image = Image.open(image_path)
    exif_data = image._getexif()

    if exif_data:
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == 'DateTimeOriginal':
                dt_str = value
                dt = datetime.strptime(dt_str, '%Y:%m:%d %H:%M:%S')
                utc_dt = dt.replace(tzinfo=timezone.utc)
                ts = utc_dt.timestamp()
                data["events"].insert(0, {
                    "event_id": 0,
                    "event_type": "capture_start",
                    "time": {
                        "mode": "dated",
                        "start": ts,
                        "end": ts,
                        "provenance": {
                            "type": "derived",
                            "exif_timestamp": ts,
                            "clock_drift_offset": 0.0,
                            "extra_offset": 0.0
                        }
                    },
                    "text": ""
                })
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
            elif tag == 'ISOSpeedRatings':
                try:
                    iso_val = value[0] if isinstance(value, (tuple, list)) else value
                    data["exposure_data"]["source_exif"]["iso"] = int(iso_val)
                    data["exposure_data"]["source_exif"]["have_data"] = True
                    data["exposure_data"]["source"] = "source_exif"
                except (TypeError, ValueError, IndexError):
                    pass
            elif tag == 'FNumber':
                try:
                    data["exposure_data"]["source_exif"]["aperture"] = float(value)
                    data["exposure_data"]["source_exif"]["have_data"] = True
                    data["exposure_data"]["source"] = "source_exif"
                except (TypeError, ValueError):
                    pass
            elif tag == 'ExposureTime':
                try:
                    if hasattr(value, 'numerator') and hasattr(value, 'denominator'):
                        num, den = int(value.numerator), int(value.denominator)
                    elif isinstance(value, tuple) and len(value) == 2:
                        num, den = int(value[0]), int(value[1])
                    else:
                        f = Fraction(float(value)).limit_denominator(100000)
                        num, den = f.numerator, f.denominator
                    if num > 0 and den > 0:
                        data["exposure_data"]["source_exif"]["shutter_speed"] = {"numerator": num, "denominator": den}
                        data["exposure_data"]["source_exif"]["have_data"] = True
                        data["exposure_data"]["source"] = "source_exif"
                except (TypeError, ValueError):
                    pass

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
    capture_start_event = next((e for e in data['events'] if e.get('event_type') == 'capture_start'), None)
    if capture_start_event:
        capture_timestamp = capture_start_event.get('time', {}).get('start', 0.0)

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
    data["geolocation_data"]["source_gnss_track_file"]["Longitude_decimal"] = 100000
    data["geolocation_data"]["source_gnss_track_file"]["Latitude_decimal"] = 100000
    data["geolocation_data"]["source_gnss_track_file"]["file_path"] = ""
    data["geolocation_data"]["source_gnss_track_file"]["file_sha512sum"] = ""
    data["geolocation_data"]["source_gnss_track_file"]["file_type"] = ""
    data["geolocation_data"]["source_gnss_track_file"]["have_data"] = False
    return

def load_gramps_people(file_path):
    """Load people from a Gramps gzipped XML export (.gramps) file."""
    people = []
    try:
        with gzip.open(file_path, 'rb') as f:
            tree = ET.parse(f)
        root = tree.getroot()
        ns = ''
        if root.tag.startswith('{'):
            ns = root.tag[:root.tag.index('}') + 1]
        for person_el in root.iter(f'{ns}person'):
            gramps_id = person_el.get('id', '')
            if not gramps_id:
                continue
            name_el = None
            for n in person_el.findall(f'{ns}name'):
                if n.get('type', '') == 'Birth Name':
                    name_el = n
                    break
            if name_el is None:
                name_el = person_el.find(f'{ns}name')
            if name_el is not None:
                first = (name_el.findtext(f'{ns}first') or '').strip()
                surname_el = name_el.find(f'.//{ns}surname')
                surname = ((surname_el.text or '').strip()) if surname_el is not None else ''
                full_name = ' '.join(filter(None, [first, surname])) or gramps_id
            else:
                full_name = gramps_id
            people.append({'id': gramps_id, 'name': full_name})
    except Exception as e:
        print(f"Warning: Could not load Gramps file: {e}")
    return sorted(people, key=lambda p: p['name'].lower())


@app.route('/api/gramps/people')
def get_gramps_people():
    """Return people loaded from the Gramps database"""
    return jsonify({"people": gramps_people})


@app.route('/')
def index():
    """Main page"""
    if not current_image_path:
        return "No image loaded. Please start the application with an image path.", 400
    return render_template('index.html', session_key=session_key)

@app.route('/api/metadata', methods=['GET'])
def get_metadata():
    """Get current metadata"""
    return jsonify({"data": current_data, "session_key": session_key})

@app.route('/api/metadata', methods=['POST'])
def update_metadata():
    """Update metadata with validation"""
    global current_data
    updates = request.json

    # Validate session key
    if 'session_key' not in updates or updates['session_key'] != session_key:
        return jsonify({"success": False, "error": "invalid_session", "message": "Session expired. Please reload the page."}), 403

    errors = {}

    # Update texts (no validation needed for strings)
    if 'texts' in updates:
        current_data['texts'].update(updates['texts'])

    # Update user events
    USER_EVENT_TYPES = {'capture_start', 'film_scan', 'print_scan', 'film_development', 'print'}
    if 'events' in updates:
        preserved = [e for e in current_data['events'] if e.get('event_type') not in USER_EVENT_TYPES]
        new_user_events = []
        for ev in updates['events']:
            event_type = str(ev.get('event_type', ''))
            if event_type not in USER_EVENT_TYPES:
                continue
            time_obj = ev.get('time', {})
            time_mode = str(time_obj.get('mode', 'dated'))
            if time_mode not in ('dated', 'annual'):
                errors['events'] = 'Invalid time mode'
                break
            try:
                start_s = float(time_obj['start'])
                end_s = float(time_obj['end'])
            except (KeyError, ValueError, TypeError):
                errors['events'] = 'Invalid timestamp'
                break
            provenance = time_obj.get('provenance', {'type': 'text', 'description': ''})
            if provenance.get('type') == 'derived':
                try:
                    exif_ts = float(provenance['exif_timestamp'])
                    drift = float(provenance.get('clock_drift_offset', 0.0))
                    extra = float(provenance.get('extra_offset', 0.0))
                    start_s = exif_ts + drift + extra
                    end_s = start_s
                    provenance = {
                        'type': 'derived',
                        'exif_timestamp': exif_ts,
                        'clock_drift_offset': drift,
                        'extra_offset': extra
                    }
                except (KeyError, ValueError, TypeError):
                    errors['events'] = 'Invalid derived provenance'
                    break
            if end_s < start_s:
                errors['events'] = 'End time must not be before start time'
                break
            new_user_events.append({
                'event_id': int(ev.get('event_id', int(time.time() * 1000))),
                'event_type': event_type,
                'time': {
                    'mode': time_mode,
                    'start': start_s,
                    'end': end_s,
                    'provenance': provenance
                },
                'text': str(ev.get('text', ''))
            })
        if 'events' not in errors:
            current_data['events'] = preserved + new_user_events
            try_gpx_files(current_data, current_image_path)

    # Update geolocation
    if 'geolocation_data' in updates:
        if 'source_manual_entry' in updates['geolocation_data']:
            manual_entry = updates['geolocation_data']['source_manual_entry']

            # Check if both fields are provided
            if 'Latitude_decimal' in manual_entry and 'Longitude_decimal' in manual_entry:
                lat_str = str(manual_entry['Latitude_decimal']).strip()
                lon_str = str(manual_entry['Longitude_decimal']).strip()

                # Both empty is valid (no data)
                if lat_str == '' and lon_str == '':
                    current_data['geolocation_data']['source_manual_entry']['Latitude_decimal'] = 100000
                    current_data['geolocation_data']['source_manual_entry']['Longitude_decimal'] = 100000
                    current_data['geolocation_data']['source_manual_entry']['have_data'] = False
                # Both must have valid values
                elif lat_str != '' and lon_str != '':
                    try:
                        lat = float(lat_str)
                        lon = float(lon_str)

                        lat_valid = -90 <= lat <= 90
                        lon_valid = -180 <= lon <= 180

                        if lat_valid and lon_valid:
                            current_data['geolocation_data']['source_manual_entry']['Latitude_decimal'] = lat
                            current_data['geolocation_data']['source_manual_entry']['Longitude_decimal'] = lon
                            current_data['geolocation_data']['source_manual_entry']['have_data'] = True
                        else:
                            # Both invalid if either is out of range
                            if not lat_valid:
                                errors['Latitude_decimal'] = 'Must be between -90 and 90'
                            if not lon_valid:
                                errors['Longitude_decimal'] = 'Must be between -180 and 180'
                            # Mark both as invalid
                            errors['Latitude_decimal'] = errors.get('Latitude_decimal', 'Both fields must be valid or both empty')
                            errors['Longitude_decimal'] = errors.get('Longitude_decimal', 'Both fields must be valid or both empty')
                    except (ValueError, TypeError):
                        # Both invalid if either can't be parsed
                        errors['Latitude_decimal'] = 'Must be a valid number'
                        errors['Longitude_decimal'] = 'Must be a valid number'
                else:
                    # One empty, one not - both invalid
                    errors['Latitude_decimal'] = 'Both fields must be filled or both empty'
                    errors['Longitude_decimal'] = 'Both fields must be filled or both empty'

        if 'valid_data_source' in updates['geolocation_data']:
            current_data['geolocation_data']['valid_data_source'] = updates['geolocation_data']['valid_data_source']
            source = current_data['geolocation_data']['valid_data_source']
            current_data['geolocation_data']['have_data'] = current_data['geolocation_data'][source]['have_data']

        if 'display_map_tile_server' in updates['geolocation_data']:
            current_data['geolocation_data']['display_map_tile_server'] = updates['geolocation_data']['display_map_tile_server']

        if 'source_gnss_track_file' in updates['geolocation_data']:
            if 'gnss_device_time_offset_seconds' in updates['geolocation_data']['source_gnss_track_file']:
                try:
                    offset = float(updates['geolocation_data']['source_gnss_track_file']['gnss_device_time_offset_seconds'])
                    current_data['geolocation_data']['source_gnss_track_file']['gnss_device_time_offset_seconds'] = offset
                    try_gpx_files(current_data, current_image_path)
                except (ValueError, TypeError):
                    errors['gnss_device_time_offset_seconds'] = 'Must be a valid number'

    # Update exposure data
    if 'exposure_data' in updates:
        exp = updates['exposure_data']
        if 'multiple_exposures' in exp:
            current_data['exposure_data']['multiple_exposures'] = bool(exp['multiple_exposures'])
        if 'source' in exp:
            src = str(exp['source'])
            if src in ('source_manual', 'source_exif'):
                current_data['exposure_data']['source'] = src
        if 'source_manual' in exp:
            manual = exp['source_manual']
            if 'iso' in manual:
                if manual['iso'] is None or str(manual['iso']).strip() == '':
                    current_data['exposure_data']['source_manual']['iso'] = None
                else:
                    try:
                        iso = int(float(str(manual['iso'])))
                        if iso > 0:
                            current_data['exposure_data']['source_manual']['iso'] = iso
                        else:
                            errors['iso'] = 'Must be a positive number'
                    except (ValueError, TypeError):
                        errors['iso'] = 'Must be a valid number'
            if 'aperture' in manual:
                if manual['aperture'] is None or str(manual['aperture']).strip() == '':
                    current_data['exposure_data']['source_manual']['aperture'] = None
                else:
                    try:
                        ap = float(str(manual['aperture']))
                        if ap > 0:
                            current_data['exposure_data']['source_manual']['aperture'] = ap
                        else:
                            errors['aperture'] = 'Must be a positive number'
                    except (ValueError, TypeError):
                        errors['aperture'] = 'Must be a valid number'
            if 'shutter_speed' in manual:
                if manual['shutter_speed'] is None or str(manual['shutter_speed']).strip() == '':
                    current_data['exposure_data']['source_manual']['shutter_speed'] = None
                else:
                    val_str = str(manual['shutter_speed']).strip()
                    try:
                        if '/' in val_str:
                            num_s, den_s = val_str.split('/', 1)
                            num, den = int(float(num_s)), int(float(den_s))
                        else:
                            f = Fraction(val_str).limit_denominator(100000)
                            num, den = f.numerator, f.denominator
                        if num > 0 and den > 0:
                            current_data['exposure_data']['source_manual']['shutter_speed'] = {"numerator": num, "denominator": den}
                        else:
                            errors['shutter_speed'] = 'Must be a positive number'
                    except (ValueError, TypeError, ZeroDivisionError):
                        errors['shutter_speed'] = 'Must be a valid number or fraction (e.g. 1/125)'

    # Update subjects (people in photo)
    if 'subjects' in updates and 'list' in updates['subjects']:
        validated_people = []
        for person in updates['subjects']['list']:
            if not isinstance(person, dict):
                continue
            gramps_id = str(person.get('gramps_id', ''))
            name = str(person.get('name', ''))
            bb = person.get('face_bounding_box')
            validated_bb = None
            if isinstance(bb, dict):
                try:
                    x = float(bb['x'])
                    y = float(bb['y'])
                    w = float(bb['w'])
                    h = float(bb['h'])
                    if 0 <= x <= 1 and 0 <= y <= 1 and 0 < w <= 1 and 0 < h <= 1:
                        validated_bb = {'x': x, 'y': y, 'w': w, 'h': h}
                except (KeyError, ValueError, TypeError):
                    pass
            validated_people.append({
                'gramps_id': gramps_id,
                'name': name,
                'face_bounding_box': validated_bb
            })
        current_data['subjects']['list'] = validated_people

    if errors:
        return jsonify({"success": False, "errors": errors, "data": current_data})
    else:
        return jsonify({"success": True, "data": current_data})

@app.route('/api/save', methods=['POST'])
def save_metadata():
    """Save metadata to JSON file"""
    updates = request.json

    # Validate session key
    if 'session_key' not in updates or updates['session_key'] != session_key:
        return jsonify({"success": False, "error": "invalid_session", "message": "Session expired. Please reload the page."}), 403

    output_path = Path(current_data["constants"]["image_file_full_path"]).with_suffix(".json")

    with open(output_path, "w") as f:
        json.dump(current_data, f, indent=4)

    return jsonify({"success": True, "path": str(output_path)})

@app.route('/api/image')
def get_image():
    """Serve a thumbnail of the current image"""
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

@app.route('/api/image/full')
def get_image_full():
    """Serve the full resolution image file"""
    if not current_image_path:
        return "No image loaded", 404
    return send_file(current_image_path)

def main():
    global current_data, current_image_path, session_key, gramps_people

    parser = argparse.ArgumentParser(description='Metadata Writer')
    parser.add_argument('image_path', help='Path to image file')
    parser.add_argument('--gramps', metavar='FILE',
                        help='Gramps XML export file (.gramps) for people tagging')
    args = parser.parse_args()

    current_image_path = args.image_path

    if not os.path.exists(current_image_path):
        print(f"Error: Image file not found: {current_image_path}")
        sys.exit(1)

    if args.gramps:
        if not os.path.exists(args.gramps):
            print(f"Error: Gramps file not found: {args.gramps}")
            sys.exit(1)
        gramps_people = load_gramps_people(args.gramps)
        print(f"Loaded {len(gramps_people)} people from Gramps file: {args.gramps}")

    # Generate unique session key for this server instance
    session_key = secrets.token_hex(16)

    print(f"Loading metadata for: {current_image_path}")
    current_data = load_image_metadata(current_image_path)

    if args.gramps:
        current_data['subjects']['gramps_file_path'] = os.path.realpath(args.gramps)
        current_data['subjects']['gramps_file_sha512'] = sha512Checksum(args.gramps)

    print("\nStarting web server...")
    print("Open your browser to: http://localhost:5000")
    print("Press Ctrl+C to stop the server and exit")

    app.run(debug=True, port=5000)

if __name__ == "__main__":
    main()
