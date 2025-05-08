import sys
import tkinter as tk

class TextRedirector:
    """Redirects print statements to both console and a tkinter Text widget"""
    def __init__(self, text_widget, original_stdout=None):
        self.text_widget = text_widget
        self.original_stdout = original_stdout or sys.stdout

    def write(self, string):
        self.original_stdout.write(string)
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)  # Auto-scroll to the end
        self.text_widget.update_idletasks()

    def flush(self):
        self.original_stdout.flush() 