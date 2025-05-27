#!/bin/env python

import time
import sys
import json
import tkinter as tk
import hashlib
from time import strftime, localtime
from tkinter import messagebox
from tkinter import Frame
from tkcalendar import Calendar
from PIL import Image, ImageTk

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
        self.txt.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        # create a Scrollbar and associate it with txt
        scrollb = tk.Scrollbar(self, command=self.txt.yview)
        scrollb.grid(row=0, column=1, sticky='nsew')
        self.txt['yscrollcommand'] = scrollb.set
    def get(c,a,b):
        return c.txt.get(a,b)

#Got md5Checksum from someones blog https://www.joelverhagen.com/blog/2011/02/md5-hash-of-file-in-python/
def md5Checksum(filePath):
    with open(filePath, 'rb') as fh:
        m = hashlib.md5()
        while True:
            data = fh.read(8192)
            if not data:
                break
            m.update(data)
        return m.hexdigest()

def main(image_path):

    def save_and_exit():
        title = title_entry.get()
        description = description_entry.get("1.0",'end-1c')
        data = {
            "version": "v0.0-dev",
            "title": title,
            "capture_time_start": int(time.mktime(time.strptime(timestamp_start.get(), '%Y-%m-%d %H:%M:%S'))),
            "capture_time_end": int(time.mktime(time.strptime(timestamp_end.get(), '%Y-%m-%d %H:%M:%S'))),
            "image_md5": md5Checksum(image_path),
            "description": description
        }

        with open("output.json", "w") as f:
            json.dump(data, f, indent=4)

        root.destroy()

    # GUI setup
    root = tk.Tk()
    root.title("Metadata Writer")

    # Load and display image
    img = Image.open(image_path)
    img.thumbnail((400, 400))  # Resize for display
    photo = ImageTk.PhotoImage(img)

    img_label = tk.Label(root, image=photo)
    img_label.image = photo  # keep a reference


    time_start=1347517370
    time_end=1547517370

    timestamp=Frame(root)
    start_var = tk.StringVar(value=strftime('%Y-%m-%d %H:%M:%S', localtime(time_start)))
    end_var = tk.StringVar(value=strftime('%Y-%m-%d %H:%M:%S', localtime(time_end)))
    timestamp_start = tk.Entry(timestamp,textvariable=start_var)
    timestamp_end = tk.Entry(timestamp,textvariable=end_var)
    tk.Label(timestamp, text="Shot time/date start:").grid(row=0,column=0)
    tk.Label(timestamp, text="Shot time/date end:").grid(row=0,column=2)
    timestamp_start.grid(row=0,column=1)
    timestamp_end.grid(row=0,column=3)

    # Input fields
    title_frame=Frame(root)
    title_entry = tk.Entry(title_frame)
    tk.Label(title_frame, text="Title:").pack(side=tk.LEFT)
    title_entry.pack(fill=tk.X)

    description=Frame(root)
    tk.Label(description, text="Description:").pack(side=tk.LEFT)
    description_entry = TextScrollCombo(description,height=10)
    description_entry.pack()

    description_entry.config(width=600, height=100)

    # Save button
    save_button = tk.Button(root, text="Save and Exit", command=save_and_exit)


    img_label                          .grid(row=0,column=0,rowspan=5,sticky='n')
    title_frame                        .grid(row=0,column=1,sticky="we")
    description                        .grid(row=2,column=1,sticky="we")
    timestamp                          .grid(row=3,column=1,sticky="we")
    save_button                        .grid(row=4,column=1)


    root.mainloop()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py path_to_image")
        sys.exit(1)

    image_path = sys.argv[1]
    main(image_path)
