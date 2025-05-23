#!/usr/bin/env python3
"""
This is a legacy entry point that imports from the refactored code structure.
For better maintainability, please use main.py instead.
"""

import tkinter as tk
from gui.app import InvestoApp

if __name__ == "__main__":
    root = tk.Tk()
    app = InvestoApp(root)
    root.mainloop() 