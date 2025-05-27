import sys
import json
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk

def main(image_path):
    def save_and_exit():
        title = title_entry.get()
        description = description_entry.get()
        data = {
            "title": title,
            "description": description
        }

        with open("output.json", "w") as f:
            json.dump(data, f, indent=4)

        root.destroy()

    # GUI setup
    root = tk.Tk()
    root.title("Image Metadata Entry")

    # Load and display image
    img = Image.open(image_path)
    img.thumbnail((400, 400))  # Resize for display
    photo = ImageTk.PhotoImage(img)

    img_label = tk.Label(root, image=photo)
    img_label.image = photo  # keep a reference
    img_label.pack(pady=10)

    # Input fields
    tk.Label(root, text="Title:").pack()
    title_entry = tk.Entry(root, width=50)
    title_entry.pack(pady=5)

    tk.Label(root, text="Description:").pack()
    description_entry = tk.Entry(root, width=50)
    description_entry.pack(pady=5)

    # Save button
    save_button = tk.Button(root, text="Save and Exit", command=save_and_exit)
    save_button.pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py path_to_image")
        sys.exit(1)

    image_path = sys.argv[1]
    main(image_path)
