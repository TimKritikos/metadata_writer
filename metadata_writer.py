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

#import stuff that's needed for both gui and check mode plus tkinter to make inheritance easier (for now)
import sys
import hashlib
import json
from datetime import datetime
import tkinter as tk

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
    from tkinter import ttk
    from tkcalendar import Calendar
    from PIL import Image, ImageTk
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from time import strftime, localtime
    import tkintermapview

    light_data = {
            "lights": [ { "id": 0, "brand":"",        "name": "other"     },
                        { "id": 1, "brand":"",        "name": "Sun"       },
                        { "id": 2, "brand":"Godox",   "name": "AD200 Pro" },
                        { "id": 3, "brand":"Aputure", "name": "600D"      }
                ]
            }

    data = {
        "program_version": "v0.0-dev",
        "data_spec_version": "v0.0-dev",
        "title": "",
        "capture_time_start": 0,
        "capture_time_end": 0,
        "image_sha512": sha512Checksum(image_path),
        "description": "",
            "events" : [{ "time": 1733055790, "text": "Data captured" },
                        { "time": 1741745288, "text": "Raw file developed"},
                        { "time": 1747012088, "text": "Metadata written" },
                        { "time": 1747876088, "text": "Metadata modified" },
                        { "time": 1759876088, "text": "Metadata version updated" }
                        ],
        "GPS_lat_dec_N": 51.500789280409016,
        "GPS_long_dec_W": -0.12472196184719725,
        "lights": [{ "source":2, "type":"Flash",      "Usage":"pointing to his face" },
                   { "source":3, "type":"continious", "Usage":"hair light" },
                   { "source":1, "type":"continious", "Usage":"doing its thing" },
                   { "source":0, "type":"continious", "Usage":"street light" }
                   ]
    }

    def save_and_exit():
        description_value = description_entry.get("1.0",'end-1c')
        data["title"] = title.get()
        data["capture_time_start"] = int(time.mktime(time.strptime(timestamp_start.get(), '%Y-%m-%d %H:%M:%S')))
        data["capture_time_end"] = int(time.mktime(time.strptime(timestamp_end.get(), '%Y-%m-%d %H:%M:%S')))
        data["description"] = description_value

        with open("output.json", "w") as f:
            json.dump(data, f, indent=4)

        root.destroy()

    # GUI setup
    root = tk.Tk()
    root.title("Metadata Writer")
    background_color=root.cget('bg')

    # Load and display image
    img = Image.open(image_path)
    img.thumbnail((400, 400))  # Resize for display
    photo = ImageTk.PhotoImage(img)
    img_label = tk.Label(root, image=photo, borderwidth=15)

    editables=Frame()

    #title field
    title=TitledEntry(editables,"Ttile",tk.NORMAL,"")

    #Description field
    description=Frame(editables)
    tk.Label(description, text="Description:").pack(side=tk.LEFT)
    description_entry = TextScrollCombo(description)
    description_entry.pack()
    description_entry.config(width=600, height=100)

    #Start/end timestamp fields
    timestamp=Frame(editables)
    start_var = tk.StringVar(value=strftime('%Y-%m-%d %H:%M:%S', localtime(data["capture_time_start"])))
    end_var = tk.StringVar(value=strftime('%Y-%m-%d %H:%M:%S', localtime(data["capture_time_end"])))
    timestamp_start = tk.Entry(timestamp,textvariable=start_var)
    timestamp_end = tk.Entry(timestamp,textvariable=end_var)
    tk.Label(timestamp, text="Shot time/date start:").grid(row=0,column=0,padx=(0,5))
    tk.Label(timestamp, text="Shot time/date end:").grid(row=0,column=2,padx=5)
    timestamp_start.grid(row=0,column=1)
    timestamp_end.grid(row=0,column=3)


    #sha512 field
    sha512sum=TitledEntry(editables,"Image SHA512",tk.DISABLED,data["image_sha512"])

    #version field
    versions=Frame(editables)
    program_version=TitledEntry(versions,"Program version",tk.DISABLED,data["program_version"],width=8)
    data_spec_version=TitledEntry(versions,"Data specification version",tk.DISABLED,data["data_spec_version"],width=8)
    program_version.grid(row=0,column=0,padx=(0,5))
    data_spec_version.grid(row=0,column=1,padx=5)

    # Save button
    save_button = tk.Button(editables, text="Save and Exit", command=save_and_exit)

    # Map widget
    map_frame=Frame(root)
    map_widget = tkintermapview.TkinterMapView(map_frame, width=400, height=400, corner_radius=10)
    map_widget.set_position(data["GPS_lat_dec_N"], data["GPS_long_dec_W"])
    marker_1=map_widget.set_marker(data["GPS_lat_dec_N"], data["GPS_long_dec_W"])
    map_widget.set_zoom(15)
    map_widget.pack(pady=15)

    #timeline field
    timeline = event_timeline(root,data["events"],matplotlib.pyplot,numpy,FigureCanvasTkAgg,background_color)
    timeline.configure(bg=background_color)

    #media_aqusition=TitledDropdown(root,"Media Aquisition",["unkown","Direct digital off of taking device","Received digitial unmodified from taking device","Received digital re-encoded and or metadata stripped","Received digital editied"],0)


    #light table
    table=[]
    for item in data["lights"]:
        for device in light_data["lights"]:
            if device["id"] == item["source"]:
                table.append([device["brand"]+device["name"],item["type"],item["Usage"]])

    light_table=TitledTable(editables,"List of lights / flashes used:",ttk,table,["Device","Type","Usage"],[140,100,450],['w','w','w'])


    #Window layout
    img_label     .grid(row=0,column=0,sticky='n')
    editables     .grid(row=0,column=1,rowspan=2,sticky='ns')
    map_frame     .grid(row=1,column=0)
    timeline      .grid(row=2,column=0,columnspan=2)

    title         .grid(row=0,column=0,sticky="we",pady=(10,5))
    description   .grid(row=1,column=0,sticky="we",pady=5)
    timestamp     .grid(row=2,column=0,sticky="we",pady=5)
    sha512sum     .grid(row=3,column=0,sticky="we",pady=5)
    versions      .grid(row=4,column=0,sticky="we",pady=5)
    light_table   .grid(row=5,column=0,sticky="we",pady=5)
    save_button   .grid(row=6,column=0,pady=(20,5))

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

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # ensure a consistent GUI size
        self.grid_propagate(False)
        # implement stretchability
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # create a Text widget
        self.txt = tk.Text(self,height=10)
        self.txt.grid(row=0, column=0, sticky="nsew")

        # create a Scrollbar and associate it with txt
        scrollb = tk.Scrollbar(self, command=self.txt.yview)
        scrollb.grid(row=0, column=1, sticky='nsew')
        self.txt['yscrollcommand'] = scrollb.set

    def get(c,a,b):
        return c.txt.get(a,b)

#TODO: delete if unused before release
#class TitledDropdown(tk.Frame):
#
#    def __init__(self, root_window, text, options, default_opt):
#
#        super().__init__(root_window)
#
#        self.titled_dropdown = tk.OptionMenu(self,tk.StringVar(value=options[default_opt]),*options)
#        self.titled_dropdown.config(width=8)
#        tk.Label(self, text=text).pack(side=tk.LEFT)
#        self.titled_dropdown.pack(fill=tk.X)
#    def get(c):
#        return c.titled_dropdown.get()

class TitledEntry(tk.Frame):

    def __init__(self, root_window, text, input_state, init_text, width=None):

        super().__init__(root_window)

        self.title_entry = tk.Entry(self,state=input_state,textvariable=tk.StringVar(value=init_text),width=width)

        tk.Label(self, text=text).pack(side=tk.LEFT)
        self.title_entry.pack(fill=tk.X)
    def get(c):
        return c.title_entry.get()

class TitledTable(tk.Frame):

    def __init__(self, root_window, text, ttk, table, header, widths, anchors):

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
        timelines.append(datetime.fromtimestamp(item["time"]))

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

if __name__ == "__main__":
    main()
