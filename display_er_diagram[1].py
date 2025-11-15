import tkinter as tk
from PIL import ImageTk, Image
import os

def display_er_diagram():
    script_dir = os.path.dirname(__file__)
    image_path = os.path.join(script_dir, 'data', 'decomposed', 'er_diagram.png')

    root = tk.Tk()
    root.title("ER Diagram")

    if not os.path.exists(image_path):
        error_label = tk.Label(root, text=f"Error: Image not found at {image_path}")
        error_label.pack()
        root.mainloop()
        return

    try:
        img = Image.open(image_path)
        img = ImageTk.PhotoImage(img)

        panel = tk.Label(root, image=img)
        panel.image = img
        panel.pack(side="bottom", fill="both", expand="yes")

    except Exception as e:
        error_label = tk.Label(root, text=f"Error loading image: {e}")
        error_label.pack()

    root.mainloop()

if __name__ == "__main__":
    display_er_diagram()
