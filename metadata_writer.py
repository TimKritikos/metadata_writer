#!/bin/env python

#  metadata_writer.py -- Single file python app to create metadata
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
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.  */

#TODO:
#Weather image is cropped
#Make save button red if any data is unparsable
#Make it so that each module doesn't have an event id, instead store on the event data which modules got changed
#Add timezone setting for exif date
#Change the background of TitledFrames from the wnidow background

#import stuff that's needed for both GUI and check mode plus tkinter to make inheritance easier (for now)
import sys
import hashlib
import json
import os
from datetime import datetime
from datetime import timezone
import tkinter as tk
from tkinter import ttk

def main():
    if len(sys.argv) < 2:
        print("Usage: python script.py path_to_image")
        sys.exit(1)

    image_path = sys.argv[1]

    import matplotlib.pyplot
    import numpy
    import time
    from tkinter import messagebox
    from tkinter import Frame
    from tkcalendar import Calendar
    from PIL import Image, ImageTk
    from PIL.ExifTags import TAGS
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from time import strftime, localtime
    import tkintermapview
    from pathlib import Path
    from exif import Image as exifImage
    from fractions import Fraction
    import gpxpy
    import gpxpy.gpx

    device_data = {
                "lights": [ { "id": 0, "brand":"",        "name": "other"     },
                            { "id": 1, "brand":"",        "name": "Sun"       },
                            { "id": 2, "brand":"Godox",   "name": "AD200 Pro" },
                            { "id": 3, "brand":"Aputure", "name": "600D"      }
                    ],
                "cameras": [
                            {
                                "id": 0,
                                "brand":"Unknown",
                                "model":"unknown",
                                "serial_number":None
                            },{
                                "id": 1,
                                "brand":"Sony",
                                "model":"ILCE7R4",
                                "serial_number":"ThE_S3r4l_#"
                            },{
                                "id": 2,
                                "brand":"Insta360",
                                "model":"x3",
                                "serial_number":"7777777777"
                            }
                    ]
            }

    #Get current timestamp
    current_event_timestamp=int(time.time())

    #Get exif from image file
    image = Image.open(image_path)
    exif_data = image._getexif()

    shutter_speed_apex = None
    exposure_time = None
    create_datetime= None

    for tag_id, value in exif_data.items():
        tag = TAGS.get(tag_id, tag_id)
        if tag == 'ExposureTime':
            exposure_time = float(Fraction(value))
        elif tag == 'DateTimeOriginal':
            dt_str = value
            dt = datetime.strptime(dt_str, '%Y:%m:%d %H:%M:%S')
            utc_dt = dt.replace(tzinfo=timezone.utc)
            create_datetime=int(utc_dt.timestamp())  # Unix epoch time

    #JSON output template
    data = {
        "program_version": "v1.0-dev",
        "data_spec_version": "v1.0-dev",

        "texts": {
            "title" : "",
            "description" : "",
            "event_id" : -1
        },
        "capture_timestamp": {
            "capture_start_on_original_metadata_timestamp": create_datetime,
            "capture_duration_seconds": exposure_time,
            "single_capture_picture": True,
            "capture_start_time_offset_seconds": 0,
            "event_id" : -1
        },
        "constants": {
            "image_sha512": sha512Checksum(image_path),
            "image_file_full_path": os.path.realpath(sys.argv[1])
        },
        "events" : [{ "event_id":0, "event_type": "capture_start",         "timestamp": 0, "timestamp_accuracy_seconds": 0, "text": "" },
                    #{ "event_id":2, "event_type": "data_modification",     "timestamp": 1741745288, "text": "Raw file developed"},
                    { "event_id":1, "event_type": "metadata_modification", "timestamp": current_event_timestamp, "timestamp_accuracy_seconds": 0, "text": "Initial metadata written" },
                    #{ "event_id":5, "event_type": "version_upgrade",       "timestamp": 1759876088, "text": "Metadata version updated" }
                    ],
        "geolocation_data" : {
            "have_data": False,
            "valid_data_source": "uninitialised",
            "source_gpx_file":{
                "have_data": False,
                "GPS_latitude_decimal": 0,
                "GPS_longitude_decimal": 0,
                "gpx_device_time_offset_seconds": 0,
                "gpx_file_path": "",
            },
            "source_original_media_file":{
                "have_data": False,
                "GPS_latitude_decimal": 0,
                "GPS_longitude_decimal": 0,
            },
            "source_manual_entry":{
                "have_data": False,
                "GPS_latitude_decimal": 0,
                "GPS_longitude_decimal": 0,
            }
        }
        #"lights": [{ "source":2, "type":"Flash",      "Usage":"pointing to his face" },
        #           { "source":3, "type":"continuous", "Usage":"hair light" },
        #           { "source":1, "type":"continuous", "Usage":"doing its thing" },
        #           { "source":0, "type":"continuous", "Usage":"street light" }
        #           ]
    }


    def save_and_exit():
        try:
            attribution_event=int(event_attribution.get().split()[2])
        except ValueError as e:
            print("Error: internal error getting event id for save")
            return -1

        #Texts
        data["texts"]["title"] = title.get()
        data["texts"]["description"] = description.get("1.0",'end-1c')
        data["texts"]["event_id"] = attribution_event

        #Capture Timestamp
        data["capture_timestamp"]["event_id"] = attribution_event

        output_path = Path(data["constants"]["image_file_full_path"]).with_suffix(".json")

        with open(output_path, "w") as f:
            json.dump(data, f, indent=4)

        root.destroy()

    # GUI setup
    root = tk.Tk()
    root.title("Metadata Writer")
    background_color=root.cget('bg')


    editables=Frame()

    #################
    # display image #
    #################
    display_image_frame=TitledFrame(root, [("Image", ("TkDefaultFont", 10))] )
    img = Image.open(image_path)
    img.thumbnail((400, 400))  # Resize for display
    photo = ImageTk.PhotoImage(img)
    img_label = tk.Label(display_image_frame, image=photo, borderwidth=4)

    img_label.grid(row=0,column=0)

    #########
    # Texts #
    #########
    texts_frame=TitledFrame(editables,[("[1]", ("TkDefaultFont", 12, "bold")),("Texts", ("TkDefaultFont", 10))])

    title = TitledEntry(texts_frame,"Title","",input_state=tk.NORMAL)
    description = TextScrollCombo(texts_frame,"Description:")

    title.grid       (row=0,column=0,sticky='we',padx=3,pady=3)
    description.grid (row=1,column=0,sticky='we',padx=3,pady=3)
    texts_frame.grid_columnconfigure(0, weight=1)

    ####################
    # Geolocation data #
    ####################
    def try_gpx_file(filepath):
        gpx_file = open(filepath, 'r')
        gpx = gpxpy.parse(gpx_file)
        point_found=0
        data["geolocation_data"]["source_gpx_file"]["have_data"]=False
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    if(point.time == datetime.fromtimestamp(data["events"][0]["timestamp"]-data["geolocation_data"]["source_gpx_file"]["gpx_device_time_offset_seconds"],tz=timezone.utc)): #TODO don't hardcode this value
                        data["geolocation_data"]["source_gpx_file"]["GPS_longitude_decimal"]=point.longitude
                        data["geolocation_data"]["source_gpx_file"]["GPS_latitude_decimal"]=point.latitude
                        data["geolocation_data"]["source_gpx_file"]["gpx_file_path"]=filepath
                        data["geolocation_data"]["source_gpx_file"]["gpx_file_sha512sum"]=sha512Checksum(filepath)
                        data["geolocation_data"]["source_gpx_file"]["have_data"]=True
                        point_found=1
                        break
                if point_found==1:
                    break
            if point_found==1:
                break
        if point_found==0:
            return 1
        else:
            return 0

    def Geolocation_update(*args):
        manual_lat=gnss_manual_entry_source.get_lat()
        manual_long=gnss_manual_entry_source.get_long()
        data["geolocation_data"]["valid_data_source"]=human_name_to_source[gnss_source_selection.get()]
        try:
            manual_lat=float(manual_lat)
            manual_long=float(manual_long)
            data["geolocation_data"]["source_manual_entry"]["GPS_latitude_decimal"]=manual_lat
            data["geolocation_data"]["source_manual_entry"]["GPS_longitude_decimal"]=manual_long
            data["geolocation_data"]["source_manual_entry"]["have_data"]=True
        except ValueError as e:
            data["geolocation_data"]["source_manual_entry"]["have_data"]=False

        global map_marker
        if data["geolocation_data"][data["geolocation_data"]["valid_data_source"]]["have_data"] == True:
            new_lat=data["geolocation_data"][data["geolocation_data"]["valid_data_source"]]["GPS_latitude_decimal"]
            new_long=data["geolocation_data"][data["geolocation_data"]["valid_data_source"]]["GPS_longitude_decimal"]
            if map_marker == None:
                map_marker=map_widget.set_marker(new_lat,new_long)
            else:
                map_marker.set_position(new_lat,new_long)
            map_widget.set_position(new_lat,new_long)
            data["geolocation_data"]["have_data"]=True
        else:
            data["geolocation_data"]["have_data"]=False
            if map_marker != None:
                map_marker.delete()
                map_marker = None

    def Geolocation_update_time(*args):
        try:
            data["geolocation_data"]["source_gpx_file"]["gpx_device_time_offset_seconds"]=float(gpx_device_time_offset.get())
        except ValueError as e:
            data["geolocation_data"]["source_gpx_file"]["gpx_device_time_offset_seconds"]=0
        for file in os.listdir("/home/user/gnss_test/"):
            if file.endswith(".gpx"):
                #print("Trying "+str(os.path.join("/home/user/gnss_test/", file)))
                if try_gpx_file(os.path.join("/home/user/gnss_test/", file)) == 0:
                    break
        if data["geolocation_data"]["source_gpx_file"]["have_data"] == True :
            gnss_gpx_file_source.update_lat( data["geolocation_data"]["source_gpx_file"]["GPS_latitude_decimal"])
            gnss_gpx_file_source.update_long( data["geolocation_data"]["source_gpx_file"]["GPS_longitude_decimal"])
        else:
            gnss_gpx_file_source.update_lat("")
            gnss_gpx_file_source.update_long("")
        Geolocation_update()

    gnss_location_data_frame=TitledFrame(root,[("[3]", ("TkDefaultFont", 12, "bold")),("Geolocation data", ("TkDefaultFont", 10))])

    #Map Widget
    map_widget = tkintermapview.TkinterMapView(gnss_location_data_frame, width=400, height=250, corner_radius=10)
    map_widget.set_position(data["geolocation_data"]["source_gpx_file"]["GPS_latitude_decimal"], data["geolocation_data"]["source_gpx_file"]["GPS_longitude_decimal"])
    map_widget.set_zoom(15)
    global map_marker
    map_marker=None #map_widget.set_marker(data["geolocation_data"]["source_gpx_file"]["GPS_latitude_decimal"], data["geolocation_data"]["source_gpx_file"]["GPS_longitude_decimal"])

    gnss_source_selection=TitledDropdown(gnss_location_data_frame,"Select geolocation source:",
                                         ("Original media file",
                                          "GPX file",
                                          "Manual entry")
                                         ,0,callback=Geolocation_update)
    human_name_to_source = {
            "Original media file": "source_original_media_file",
            "GPX file": "source_gpx_file",
            "Manual entry": "source_manual_entry"
    }
    gpx_device_time_offset=TitledEntry(gnss_location_data_frame,"GPX device time offset (seconds)",data["geolocation_data"]["source_gpx_file"]["gpx_device_time_offset_seconds"],callback=Geolocation_update_time)

    #Sources
    gnss_gpx_file_source=Geolocation_source(gnss_location_data_frame,
                                         "GPX file:",
                                         data["geolocation_data"]["source_gpx_file"]["GPS_latitude_decimal"],
                                         data["geolocation_data"]["source_gpx_file"]["GPS_longitude_decimal"],
                                         tk.DISABLED)

    gnss_original_media_file_source=Geolocation_source(gnss_location_data_frame,
                                         "Original media file:",
                                         data["geolocation_data"]["source_original_media_file"]["GPS_latitude_decimal"],
                                         data["geolocation_data"]["source_original_media_file"]["GPS_longitude_decimal"],
                                         tk.DISABLED)

    gnss_manual_entry_source=Geolocation_source(gnss_location_data_frame,
                                        "Original media file:",
                                        "",
                                        "",
                                        tk.NORMAL, callback=Geolocation_update)

    map_widget.grid                      (row=0,column=0,pady=(0,3),padx=5)
    gnss_source_selection.grid           (row=1,column=0,pady=(5,2),sticky='we')
    gpx_device_time_offset.grid          (row=2,column=0,pady=(2,5),sticky='w')
    gnss_gpx_file_source.grid            (row=3,column=0,sticky='we')
    gnss_original_media_file_source.grid (row=4,column=0,sticky='we')
    gnss_manual_entry_source.grid        (row=5,column=0,sticky='we')

    #Geolocation_update_time() #Note, not needed because the capture timestamp callback will call it

    #####################
    # Capture timestamp #
    #####################
    capture_timestamp=TitledFrame(editables,[("[2]", ("TkDefaultFont", 12, "bold")),("Capture timestamp", ("TkDefaultFont", 10))])

    #Callback for updating the explanation
    def update_capture_timestamp_description(*args):
        image_creation_event_id=0#TODO: don't hardcode this value
        try:
            data["capture_timestamp"]["capture_start_time_offset_seconds"] = float(cap_offset_var.get())
            #If the capture time changes, update it and a list of thing that depend on it
            if data["events"][image_creation_event_id]["timestamp"] != int(data["capture_timestamp"]["capture_start_time_offset_seconds"])+int(data["capture_timestamp"]["capture_start_on_original_metadata_timestamp"]):
                data["events"][image_creation_event_id]["timestamp"] = int(data["capture_timestamp"]["capture_start_time_offset_seconds"])+int(data["capture_timestamp"]["capture_start_on_original_metadata_timestamp"])
                Geolocation_update_time()
            data["capture_timestamp"]["capture_duration_seconds"] = float(cap_duration_var.get())
            data["capture_timestamp"]["single_capture_picture"] = one_capture_var.get()
            data["events"][image_creation_event_id]["timestamp_accuracy_seconds"] = float(cap_accuracy_var.get())
        except ValueError as e:
            explanation_var.set("Invalid values!")
            explanation.config(bg="red")
            return

        date=time.strftime('%A %-d of %B %Y %H:%M:%S',time.gmtime(data["capture_timestamp"]["capture_start_on_original_metadata_timestamp"]+int(cap_offset_var.get())))

        if data["events"][image_creation_event_id]["timestamp_accuracy_seconds"] != 0.0:
            acc_string=" plus/minus "+str(data["events"][image_creation_event_id]["timestamp_accuracy_seconds"])+" seconds"
        else:
            acc_string=""

        if data["capture_timestamp"]["capture_duration_seconds"] == False:
            explanation_var.set("A multi-picture image (focus stack/exposure stack/etc) that started being taken at " + date + acc_string + " and took " + str(data["capture_timestamp"]["capture_duration_seconds"]) + " seconds to capture" )
        else:
            explanation_var.set("An image taken at " + date + acc_string + " with a " + str(data["capture_timestamp"]["capture_duration_seconds"]) + " second shutter speed")
        explanation.config(bg="grey64")

    # explanation text
    explanation_var = tk.StringVar()
    explanation = tk.Label(capture_timestamp, textvariable=explanation_var, wraplength=450)
    explanation.config(width=70)

    # Original capture date
    cap_start_var = tk.StringVar(value=strftime('%Y-%m-%d %H:%M:%S', time.gmtime(data["capture_timestamp"]["capture_start_on_original_metadata_timestamp"]) ))
    cap_start_label=tk.Label(capture_timestamp, text="Original capture start date:")
    cap_start = tk.Entry(capture_timestamp,textvariable=cap_start_var,state=tk.DISABLED)

    # Capture date offset
    cap_offset_var = tk.StringVar(value=data["capture_timestamp"]["capture_start_time_offset_seconds"])
    cap_offset_var.trace_add("write", update_capture_timestamp_description)
    cap_offset_label=tk.Label(capture_timestamp, text="Capture start date offset seconds:")
    cap_offset = tk.Entry(capture_timestamp,textvariable=cap_offset_var)

    # Capture duration
    cap_duration_var = tk.StringVar(value=str(data["capture_timestamp"]["capture_duration_seconds"]))
    cap_duration_var.trace_add("write", update_capture_timestamp_description)
    cap_duration_label=tk.Label(capture_timestamp, text="Capture duration (seconds):")
    cap_duration = tk.Entry(capture_timestamp,textvariable=cap_duration_var)

    # Capture accuracy
    cap_accuracy_var = tk.StringVar(value=str(data["events"][0]["timestamp_accuracy_seconds"])) #TODO: don't hardcode this value
    cap_accuracy_var.trace_add("write", update_capture_timestamp_description)
    cap_accuracy_label=tk.Label(capture_timestamp, text="Capture start accuracy (±seconds):")
    cap_accuracy = tk.Entry(capture_timestamp,textvariable=cap_accuracy_var)

    # One shot checkbox
    one_capture_var = tk.BooleanVar()
    one_capture_var.trace_add( "write", update_capture_timestamp_description)
    one_capture = tk.Checkbutton(capture_timestamp, text="Final picture is comprised of one capture",variable=one_capture_var )
    one_capture.select() #this also calls update_capture_timestamp_description. If removed place a call to it to write the initial value on the text box


    cap_start_label.grid     (row=0,column=0,padx=3,pady=3)
    cap_start.grid           (row=0,column=1,padx=3,pady=3)
    cap_duration_label.grid  (row=0,column=2,padx=3,pady=3)
    cap_duration.grid        (row=0,column=3,padx=3,pady=3)
    cap_offset_label.grid    (row=1,column=0,padx=3,pady=3)
    cap_offset.grid          (row=1,column=1,padx=3,pady=3)
    cap_accuracy_label.grid  (row=1,column=2,padx=3,pady=3)
    cap_accuracy.grid        (row=1,column=3,padx=3,pady=3)
    one_capture.grid         (row=2,column=3,padx=3,pady=3)
    explanation.grid         (row=2,column=0,padx=3,pady=3,columnspan=3)

    #############
    # Constants #
    #############
    constants_frame=TitledFrame(editables,[("Constants", ("TkDefaultFont", 10))])

    sha512sum=TitledEntry(constants_frame,"Image SHA512",data["constants"]["image_sha512"],input_state=tk.DISABLED)
    sha512sum=TitledEntry(constants_frame,"Image SHA512",data["constants"]["image_sha512"],input_state=tk.DISABLED)
    filename=TitledEntry(constants_frame,"Image Filename",data["constants"]["image_file_full_path"],input_state=tk.DISABLED)
    program_version=TitledEntry(constants_frame,"Program version",data["program_version"],width=8,input_state=tk.DISABLED)
    data_spec_version=TitledEntry(constants_frame,"Data specification version",data["data_spec_version"],width=8,input_state=tk.DISABLED)

    filename.grid          (row=0,column=0,padx=3,pady=3,columnspan=2,sticky='we')
    sha512sum.grid         (row=1,column=0,padx=3,pady=3,columnspan=2,sticky='we')
    program_version.grid   (row=2,column=0,padx=3,pady=3,sticky='we')
    data_spec_version.grid (row=2,column=1,padx=3,pady=3,sticky='we')
    constants_frame.grid_columnconfigure(0, weight=1)
    constants_frame.grid_columnconfigure(1, weight=1)

    ########
    # Save #
    ########
    save_frame=TitledFrame(editables,[("[4]", ("TkDefaultFont", 12, "bold")),("Save", ("TkDefaultFont", 10))])
    save_button = tk.Button(save_frame, text="Write and Exit", command=save_and_exit)
    save_button.config(bg='green')

    event_list=[]
    for item in data["events"]:
            if item["event_type"] == "metadata_modification":
                event_list.append("event id "+str(item["event_id"])+" : "+item["text"])

    event_attribution=TitledDropdown(save_frame,"Metadata change event attribution:",event_list,0)

    event_attribution.grid (row=0,column=0,padx=3,pady=3,sticky='we')
    save_button.grid       (row=0,column=1,padx=3,pady=3)
    save_frame.grid_columnconfigure(0, weight=1)

    ##################
    # timeline field #
    ##################
    def events_to_tags(json_events):
        capture_start=-1
        return_data=[]
        for item in json_events:
            if item["event_type"] == "capture_start":
                capture_start=item["timestamp"]
            else:
                return_data.append({"timestamp":item["timestamp"],"text":item["text"]})
                return_data.append({"timestamp":capture_start,"text":"Captured data"})
        return return_data

    timeline_frame=TitledFrame(root,[("Timeline", ("TkDefaultFont", 10))])
    timeline = event_timeline(timeline_frame,events_to_tags(data["events"]),matplotlib.pyplot,numpy,FigureCanvasTkAgg,background_color)
    timeline.configure(bg=background_color)
    timeline.grid(row=0,column=0)


    #####################
    # Media acquisition #
    #####################
    #media_acquisition=TitledDropdown(root,"Media Acquisition",["unknown","Direct digital off of taking device","Received digital unmodified from taking device","Received digital re-encoded and or metadata stripped","Received digital edited"],0)

    ##########
    # Lights #
    ##########

    # #light table
    # table=[]
    # for item in data["lights"]:
    #     for device in device_data["lights"]:
    #         if device["id"] == item["source"]:
    #             table.append([device["brand"]+device["name"],item["type"],item["Usage"]])

    # light_table=TitledTable(editables,"List of lights / flashes used:",table,["Device","Type","Usage"],[140,100,450],['w','w','w'])


    #Root frame layout
    display_image_frame      .grid(row=0,column=0,sticky='n')
    editables                .grid(row=0,column=1,rowspan=2,sticky='ns')
    gnss_location_data_frame .grid(row=1,column=0)
    timeline_frame           .grid(row=2,column=0,columnspan=2)

    #editables frame layout
    texts_frame       .grid(row=0,column=0,sticky="we",pady=5)
    capture_timestamp .grid(row=1,column=0,sticky="we",pady=5)
    save_frame        .grid(row=2,column=0,sticky="we",pady=5)
    constants_frame   .grid(row=3,column=0,sticky="we",pady=5)
    # light_table       .grid(row=6,column=0,sticky="we",pady=5)

    #This updates the default gnss source after the timestamp callback calls the gnss callback that looks through all the files
    if data["geolocation_data"]["source_original_media_file"]["have_data"] == True :
        gnss_source_selection.set(0)
    elif data["geolocation_data"]["source_gpx_file"]["have_data"] == True :
        gnss_source_selection.set(1)
    else:
        gnss_source_selection.set(2)

    root.mainloop()



#Got md5Checksum (sha512Checksum now) from someones blog https://www.joelverhagen.com/blog/2011/02/md5-hash-of-file-in-python/
def sha512Checksum(filePath):
    with open(filePath, 'rb') as fh:
        m = hashlib.sha512()
        while True:
            data = fh.read(8192)
            if not data:
                break
            m.update(data)
        return m.hexdigest()

#Got TextScrollCombo from stack overflow https://stackoverflow.com/questions/13832720/how-to-attach-a-scrollbar-to-a-text-widget
class TextScrollCombo(tk.Frame):

    def __init__(self, root_window, title):

        super().__init__(root_window)

        # implement stretchability
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # create a Text widget
        self.txt = tk.Text(self,height=10)
        self.txt.config(height=5)

        tk.Label(self, text=title).grid(row=0, column=0, sticky="w")
        self.txt.grid(row=1, column=0, sticky="we")

        # create a Scrollbar and associate it with txt
        scrollb = tk.Scrollbar(self, command=self.txt.yview)
        scrollb.grid(row=1, column=1, sticky='nsew')
        self.txt['yscrollcommand'] = scrollb.set

    def get(c,a,b):
        return c.txt.get(a,b)

class TitledDropdown(tk.Frame):

    def __init__(self, root_window, text, options, default_opt, callback=None):

        super().__init__(root_window)

        self.titled_dropdown = ttk.Combobox(self,value=options)
        self.titled_dropdown.set(options[default_opt])
        self.titled_dropdown.config(width=8)
        tk.Label(self, text=text).grid (row=0,column=0,sticky='w')
        self.titled_dropdown.grid      (row=0,column=1,sticky='we')
        self.grid_columnconfigure(1, weight=1)
        self.callback=callback
        if callback != None:
            self.titled_dropdown.bind('<<ComboboxSelected>>', callback)
    def get(c):
        return c.titled_dropdown.get()
    def set(self,n):
        self.titled_dropdown.current(n)
        if self.callback != None:
            self.callback()

class TitledEntry(tk.Frame):

    def __init__(self, root_window, text, init_text, input_state=tk.NORMAL, width=None, callback=None):

        super().__init__(root_window)

        self.titled_entry_var=tk.StringVar(value=init_text)
        self.titled_entry = tk.Entry(self,state=input_state,textvariable=self.titled_entry_var,width=width)
        if callback != None:
            self.titled_entry_var.trace_add("write", callback)

        self.label=tk.Label(self, text=text)
        self.label.grid(row=0,column=0,sticky='w')
        self.titled_entry.grid(row=0,column=1,sticky='we')
        self.grid_columnconfigure(1, weight=1)
    def get(c):
        return c.titled_entry.get()

class TitledTable(tk.Frame):

    def __init__(self, root_window, text, table, header, widths, anchors):

        super().__init__(root_window)

        header_=header.copy()
        del header_[0]
        self.treeview = ttk.Treeview(self,columns=(header_),height=3)

        for row in table:
                row_=row.copy()
                del row_[0]
                self.treeview.insert("",tk.END,text=row[0],values=(row_))

        for i in range(len(header)):
            if i==0:
                self.treeview.heading("#0", text=header[i])
                self.treeview.column("#0", width = widths[i], anchor=anchors[i])
            else:
                self.treeview.heading(header[i], text=header[i])
                self.treeview.column(header[i], width = widths[i], anchor=anchors[i])


        self.scrollb = tk.Scrollbar(self, command=self.treeview.yview)

        self.utility_frame=tk.Frame(self)
        self.modify_button=tk.Button(self.utility_frame,text="Modify",width=8)
        self.add_button=tk.Button(self.utility_frame,text="Add",width=8)

        self.add_button.pack()
        self.modify_button.pack()

        tk.Label(self, text=text).grid(row=0,column=0,sticky="w")
        self.treeview.grid(row=1,column=0,sticky='we')
        self.scrollb.grid(row=1,column=1,sticky='ns')
        self.treeview['yscrollcommand'] = self.scrollb.set
        self.utility_frame.grid(row=1,column=2,sticky='n')

class Geolocation_source(tk.Frame):

    def __init__(self, root, text, lat_source, long_source, state, callback=None):

        super().__init__(root)

        self.separator = ttk.Separator(self, orient=tk.HORIZONTAL)
        self.separator_label = tk.Label(self, text=text)
        self.paste_button = tk.Button(self, text="Paste",state=state, command=self.paste_callback)

        self.root=root

        self.fields=tk.Frame(self)
        self.lat_var = tk.StringVar(value=lat_source)
        self.lat_label = tk.Label(self.fields, text="Latitude:")
        self.lat = tk.Entry(self.fields,textvariable=self.lat_var,state=state)
        self.long_var = tk.StringVar(value=long_source)
        self.long_label = tk.Label(self.fields, text="Longtitude:")
        self.long = tk.Entry(self.fields,textvariable=self.long_var,state=state)

        self.lat_label.grid        (row=0,column=0,pady=3)
        self.lat.grid              (row=0,column=1,pady=3)
        self.long_label.grid       (row=0,column=2,pady=3)
        self.long.grid             (row=0,column=3,pady=3)

        self.separator.grid        (row=0,column=0,columnspan=2,pady=4,sticky='we')
        self.separator_label.grid  (row=1,column=0,sticky='w')
        self.paste_button.grid     (row=1,column=1,sticky='e')
        self.fields.grid           (row=2,column=0,columnspan=2,sticky='w')

        if callback != None:
            self.lat_var.trace_add("write", callback)
            self.long_var.trace_add("write", callback)
    def get_lat(self):
        return self.lat_var.get()
    def get_long(self):
        return self.long_var.get()
    def update_lat(self,value):
        self.lat_var.set(value)
    def update_long(self,value):
        self.long_var.set(value)
    def paste_callback(self):
        clipboard=self.root.clipboard_get()
        self.lat_var.set(clipboard.split()[0])
        self.long_var.set(clipboard.split()[1])



def event_timeline(window,events,plt,np,FigureCanvasTkAgg,background_color):
    plot_line_width=0.8

    fig, ax = plt.subplots(figsize=(12, 1.8), constrained_layout=True)
    ax.set_facecolor('none') # Comment out to debug out of bound graph
    fig.patch.set_facecolor('none')
    ax.set_position([.01,0,0.8,1])

    timelines=[]
    labels=[]
    for item in events:
        labels.append(item["text"])
        timelines.append(datetime.fromtimestamp(item["timestamp"]))

    offsets= [3,2,1]
    levels = np.tile(offsets, int(np.ceil(len(timelines)/len(offsets))))[:len(timelines)]

    ax.axhline(0, c="black",linewidth=2)
    ax.vlines(timelines, 0, levels, color='black',linewidth=plot_line_width ) #Draw event lines
    ax.plot(timelines, np.zeros_like(timelines), "-o", color="k", markerfacecolor="w",linewidth=plot_line_width ) #Draw the line with the points

    for t, l, b in zip(timelines, levels, labels):
        ax.annotate(b+"\n"+t.strftime("%d/%m/%Y"), xy=(t, l),
                    xytext=(0, -20), textcoords='offset points',
                    horizontalalignment='left',
                    verticalalignment='bottom' if l > 0 else 'top',
                    color='black',
                    fontsize=9,bbox=dict(facecolor=background_color, edgecolor='black', boxstyle='round,pad=.5', linewidth=plot_line_width)
                   )

    ax.yaxis.set_visible(False)
    ax.spines[["left", "top", "right"]].set_visible(False)
    ax.spines['bottom'].set_position(('data', -8000))

    canvas = FigureCanvasTkAgg(fig, master = window)
    canvas.draw()
    plt.close()

    return canvas.get_tk_widget()

def TitledFrame(root, title_parts):
    lf = ttk.Labelframe(root, padding=2,borderwidth=4,relief="ridge")
    title = ttk.Frame(lf)
    for text, font in title_parts:
        ttk.Label(title, text=text, font=font).pack(side="left")
    lf.configure(labelwidget=title)  # managed by the labelframe itself
    return lf


if __name__ == "__main__":
    main()
