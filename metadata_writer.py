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

#import stuff that's needed for both GUI and check mode plus tkinter to make inheritance easier (for now)
import sys
import hashlib
import json
import os
from datetime import datetime
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
    from datetime import datetime
    #import tkintermapview
    from pathlib import Path
    from exif import Image as exifImage
    from fractions import Fraction

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
            create_datetime=int(dt.timestamp())  # Unix epoch time

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
        #"GPS_lat_dec_N": 51.500789280409016,
        #"GPS_long_dec_W": -0.12472196184719725,
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
        data["capture_timestamp"]["capture_duration_seconds"] = float(cap_duration_var.get())
        data["capture_timestamp"]["single_capture_picture"] = one_capture_var.get()
        data["capture_timestamp"]["capture_start_time_offset_seconds"] = float(cap_offset_var.get())
        data["capture_timestamp"]["event_id"] = attribution_event
        data["events"][0]["timestamp"] = int(data["capture_timestamp"]["capture_start_time_offset_seconds"])+int(data["capture_timestamp"]["capture_start_on_original_metadata_timestamp"])  #TODO: don't hardcode this values
        data["events"][0]["timestamp_accuracy_seconds"] = int(cap_accuracy_var.get())  #TODO: don't hardcode this values

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

    #####################
    # Capture timestamp #
    #####################
    capture_timestamp=TitledFrame(editables,[("[2]", ("TkDefaultFont", 12, "bold")),("Capture timestamp", ("TkDefaultFont", 10))])

    #Callback for updating the explanation
    def update_capture_timestamp_description(*args):
        date_value = cap_start_var.get()
        duration_value = cap_duration.get()
        check_value = one_capture_var.get()
        accuracy=cap_accuracy_var.get()

        try:
            duration_value=str(float(duration_value))
            accuracy=float(accuracy)
            date=time.strftime('%A %-d of %B %Y %H:%M:%S',time.gmtime(data["capture_timestamp"]["capture_start_on_original_metadata_timestamp"]+int(cap_offset_var.get())))

            if accuracy != 0.0:
                acc_string=" plus/minus "+str(accuracy)+" seconds"
            else:
                acc_string=""

            if check_value == False:
                explanation_var.set("A multi-picture image (focus stack/exposure stack/etc) that started being taken at " +  date + acc_string + " and took " + str(duration_value) + " seconds to capture" )
            else:
                explanation_var.set("An image taken at " + date + acc_string + " with a "+str(duration_value)+" second shutter speed")
            explanation.config(bg="grey64")
        except ValueError as e:
            explanation_var.set("Invalid values!")
            explanation.config(bg="red")

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
    cap_accuracy_var = tk.StringVar(value=str(data["events"][0]["timestamp_accuracy_seconds"]))
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
    save_frame=TitledFrame(editables,[("[3]", ("TkDefaultFont", 12, "bold")),("Save", ("TkDefaultFont", 10))])
    save_button = tk.Button(save_frame, text="Save and Exit", command=save_and_exit)
    save_button.config(bg='green')

    event_list=[]
    for item in data["events"]:
            if item["event_type"] == "metadata_modification":
                event_list.append("event id "+str(item["event_id"])+" : "+item["text"])

    event_attribution=TitledDropdown(save_frame,"Metadata change event attribution:",event_list,0)

    event_attribution.grid (row=0,column=0,padx=3,pady=3,sticky='we')
    save_button.grid       (row=0,column=1,padx=3,pady=3)
    save_frame.grid_columnconfigure(0, weight=1)

    # ##############
    # # Map widget #
    # ##############
    # map_frame=Frame(root)
    # map_widget = tkintermapview.TkinterMapView(map_frame, width=400, height=400, corner_radius=10)
    # map_widget.set_position(data["GPS_lat_dec_N"], data["GPS_long_dec_W"])
    # marker_1=map_widget.set_marker(data["GPS_lat_dec_N"], data["GPS_long_dec_W"])
    # map_widget.set_zoom(15)
    # map_widget.pack(pady=15)

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
    display_image_frame .grid(row=0,column=0,sticky='n')
    editables           .grid(row=0,column=1,rowspan=2,sticky='ns')
    # map_frame           .grid(row=1,column=0)
    timeline_frame      .grid(row=2,column=0,columnspan=2)

    #editables frame layout
    texts_frame         .grid(row=0,column=0,sticky="we",pady=5)
    capture_timestamp   .grid(row=1,column=0,sticky="we",pady=5)
    save_frame          .grid(row=2,column=0,sticky="we",pady=5)
    constants_frame     .grid(row=3,column=0,sticky="we",pady=5)
    # light_table         .grid(row=6,column=0,sticky="we",pady=5)

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

    def __init__(self, root_window, text, options, default_opt):

        super().__init__(root_window)

        self.titled_dropdown = ttk.Combobox(self,value=options)
        self.titled_dropdown.set(options[default_opt])
        self.titled_dropdown.config(width=8)
        tk.Label(self, text=text).grid (row=0,column=0,sticky='w')
        self.titled_dropdown.grid      (row=0,column=1,sticky='we')
        self.grid_columnconfigure(1, weight=1)
    def get(c):
        return c.titled_dropdown.get()

class TitledEntry(tk.Frame):

    def __init__(self, root_window, text, init_text, input_state=tk.NORMAL, width=None):

        super().__init__(root_window)

        self.title_entry = tk.Entry(self,state=input_state,textvariable=tk.StringVar(value=init_text),width=width)

        self.label=tk.Label(self, text=text)
        self.label.grid(row=0,column=0,sticky='w')
        self.title_entry.grid(row=0,column=1,sticky='we')
        self.grid_columnconfigure(1, weight=1)
    def get(c):
        return c.title_entry.get()

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
    def get(c):
        return c.title_entry.get()


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
