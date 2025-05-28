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

background_color='#DDDDDD'

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
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from time import strftime, localtime

    data = {
        "version": "v0.0-dev",
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
    root.configure(background=background_color)

    # Load and display image
    img = Image.open(image_path)
    img.thumbnail((400, 400))  # Resize for display
    photo = ImageTk.PhotoImage(img)
    img_label = tk.Label(root, image=photo, bg=background_color)

    #Start/end timestamp fields
    timestamp=Frame(root)
    timestamp.configure(bg=background_color)
    start_var = tk.StringVar(value=strftime('%Y-%m-%d %H:%M:%S', localtime(data["capture_time_start"])))
    end_var = tk.StringVar(value=strftime('%Y-%m-%d %H:%M:%S', localtime(data["capture_time_end"])))
    timestamp_start = tk.Entry(timestamp,textvariable=start_var)
    timestamp_end = tk.Entry(timestamp,textvariable=end_var)
    tk.Label(timestamp, text="Shot time/date start:", bg=background_color).grid(row=0,column=0)
    tk.Label(timestamp, text="Shot time/date end:",bg=background_color).grid(row=0,column=2)
    timestamp_start.grid(row=0,column=1)
    timestamp_end.grid(row=0,column=3)

    #Description field
    description=Frame(root)
    tk.Label(description, text="Description:",bg=background_color).pack(side=tk.LEFT)
    description_entry = TextScrollCombo(description)
    description_entry.pack()
    description.configure(bg=background_color)
    description_entry.config(width=600, height=100)

    #title field
    title=TitledEntry(root,"Ttile",tk.NORMAL,"")

    #sha512 field
    sha512sum=TitledEntry(root,"Image SHA512",tk.DISABLED,data["image_sha512"])

    #version field
    version=TitledEntry(root,"Version",tk.DISABLED,data["version"])

    #timeline field
    timeline = event_timeline(root,data["events"],matplotlib.pyplot,numpy,FigureCanvasTkAgg)
    timeline.configure(bg=background_color)

    # Save button
    save_button = tk.Button(root, text="Save and Exit", command=save_and_exit, bg=background_color)

    #Window layout
    img_label     .grid(row=0,column=0,rowspan=6,sticky='n')
    title         .grid(row=0,column=1,sticky="we")
    description   .grid(row=1,column=1,sticky="we")
    timestamp     .grid(row=2,column=1,sticky="we")
    sha512sum     .grid(row=3,column=1,sticky="we")
    version       .grid(row=4,column=1,sticky="we")
    save_button   .grid(row=5,column=1)
    timeline      .grid(row=6,column=0,columnspan=2)

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
        self.txt = tk.Text(self,height=10,bg=background_color)
        self.txt.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        # create a Scrollbar and associate it with txt
        scrollb = tk.Scrollbar(self, command=self.txt.yview,bg=background_color)
        scrollb.grid(row=0, column=1, sticky='nsew')
        self.txt['yscrollcommand'] = scrollb.set
        self.configure(background=background_color)

    def get(c,a,b):
        return c.txt.get(a,b)


class TitledEntry(tk.Frame):

    def __init__(self, root_window, text, input_state, init_text):

        super().__init__(root_window)

        self.title_entry = tk.Entry(self,state=input_state,textvariable=tk.StringVar(value=init_text),bg=background_color)
        tk.Label(self, text=text, bg=background_color).pack(side=tk.LEFT)
        self.title_entry.pack(fill=tk.X)
    def get(c):
        return c.title_entry.get()


def event_timeline(window,events,plt,np,FigureCanvasTkAgg):
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
