import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import os.path
import shutil
from datetime import datetime

class FileSelectionFrame(ttk.Frame):
    """Frame for selecting and validating the Degiro Account.csv file"""
    def __init__(self, parent, on_file_selected, on_cancel):
        super().__init__(parent)
        self.parent = parent
        self.on_file_selected = on_file_selected
        self.on_cancel = on_cancel
        
        self.create_widgets()
        self.check_existing_file()
        
    def create_widgets(self):
        # Title
        title_label = ttk.Label(self, text="Select Your Degiro Account Data", font=('Arial', 18, 'bold'))
        title_label.pack(pady=20)
        
        # Instructions frame
        instruction_frame = ttk.LabelFrame(self, text="How to obtain your Degiro account file")
        instruction_frame.pack(fill=tk.X, padx=20, pady=10)
        
        instructions = (
            "1. Log in to your Degiro account\n"
            "2. Go to Inbox > Account Statements (rekeningenoverzicht)\n"
            "3. Update the start date to the earliest date of your account\n"
            "4. Click 'Download as CSV'\n"
            "5. Select the downloaded file below"
        )
        
        ttk.Label(instruction_frame, text=instructions, justify=tk.LEFT, padding=10).pack(fill=tk.X)
        
        # File selection frame
        self.file_frame = ttk.Frame(self)
        self.file_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Existing file info (will be populated in check_existing_file)
        self.existing_file_frame = ttk.LabelFrame(self.file_frame, text="Existing Account File")
        self.existing_file_frame.pack(fill=tk.X, pady=5)
        
        self.existing_file_info = ttk.Label(self.existing_file_frame, text="Checking for existing file...", padding=10)
        self.existing_file_info.pack(fill=tk.X)
        
        self.existing_file_date_range = ttk.Label(self.existing_file_frame, text="", padding=5)
        self.existing_file_date_range.pack(fill=tk.X)
        
        # File selection buttons
        self.button_frame = ttk.Frame(self)
        self.button_frame.pack(fill=tk.X, padx=20, pady=20)
        
        self.select_new_button = ttk.Button(
            self.button_frame, 
            text="Select New Account File", 
            command=self.select_new_file
        )
        self.select_new_button.pack(side=tk.LEFT, padx=5)
        
        self.use_existing_button = ttk.Button(
            self.button_frame, 
            text="Use Existing File", 
            command=self.use_existing_file,
            state=tk.DISABLED
        )
        self.use_existing_button.pack(side=tk.LEFT, padx=5)
        
        self.cancel_button = ttk.Button(
            self.button_frame, 
            text="Cancel", 
            command=self.on_cancel
        )
        self.cancel_button.pack(side=tk.RIGHT, padx=5)
    
    def check_existing_file(self):
        """Check if an Account.csv file already exists and get its date range"""
        if os.path.exists('Account.csv'):
            try:
                # Load the CSV file
                df = pd.read_csv('Account.csv', delimiter=',')
                
                # Check if there's a date column (different versions of Degiro CSVs)
                date_col = None
                for col in ['Datum', 'Date', 'Datum_Tijd', 'Date_Time']:
                    if col in df.columns:
                        date_col = col
                        break
                
                if date_col:
                    # Convert dates
                    if 'Tijd' in date_col or 'Time' in date_col:
                        df[date_col] = pd.to_datetime(df[date_col], format='%d-%m-%Y %H:%M')
                    else:
                        df[date_col] = pd.to_datetime(df[date_col], format='%d-%m-%Y')
                    
                    # Get date range
                    min_date = df[date_col].min().strftime('%d-%m-%Y')
                    max_date = df[date_col].max().strftime('%d-%m-%Y')
                    
                    self.existing_file_info.config(
                        text=f"Found existing Account.csv file with {len(df)} transactions"
                    )
                    self.existing_file_date_range.config(
                        text=f"Date range: {min_date} to {max_date}",
                        foreground="green"
                    )
                    
                    # Enable the use existing button
                    self.use_existing_button.config(state=tk.NORMAL)
                else:
                    self.existing_file_info.config(
                        text="Found existing Account.csv file but could not determine its date range"
                    )
                    self.existing_file_date_range.config(
                        text="The file might not be a valid Degiro account statement",
                        foreground="orange"
                    )
            except Exception as e:
                self.existing_file_info.config(
                    text=f"Found existing Account.csv file but encountered an error: {str(e)}"
                )
                self.existing_file_date_range.config(
                    text="The file might be corrupted or in an unexpected format",
                    foreground="red"
                )
        else:
            self.existing_file_info.config(
                text="No existing Account.csv file found"
            )
            self.existing_file_date_range.config(
                text="Please select a new account statement file",
                foreground="blue"
            )
    
    def select_new_file(self):
        """Open file dialog to select a new Account.csv file"""
        file_path = filedialog.askopenfilename(
            title="Select Degiro Account CSV File",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        
        if file_path:
            # Check if we should back up the existing file
            if os.path.exists('Account.csv'):
                # Create a backup with timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = f'Account_backup_{timestamp}.csv'
                
                try:
                    # Copy the existing file to the backup location
                    shutil.copy2('Account.csv', backup_path)
                    
                    self.existing_file_date_range.config(
                        text=f"Existing file backed up as {backup_path}",
                        foreground="green"
                    )
                except Exception as e:
                    messagebox.showwarning("Backup Failed", 
                                         f"Could not back up existing file: {str(e)}")
            
            try:
                # Copy the selected file to Account.csv
                shutil.copy2(file_path, 'Account.csv')
                
                # Verify the new file
                self.check_existing_file()
                
                # If verification successful, call the callback
                if self.use_existing_button.cget('state') == 'normal':
                    messagebox.showinfo("File Selected", 
                                      "New Account.csv file has been successfully imported")
                    self.on_file_selected()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import the selected file: {str(e)}")
    
    def use_existing_file(self):
        """Use the existing Account.csv file"""
        if os.path.exists('Account.csv'):
            self.on_file_selected()
        else:
            messagebox.showerror("Error", "The Account.csv file could not be found. Please select a new file.") 