# (Lines 1 - 149 of your file... e.g., imports, class definition, setup)
import tkinter as tk
from tkinter import messagebox
import queue
import threading
import time

class ProtonGUI(tk.Tk): # Assuming ProtonGUI inherits from tk.Tk or tk.Frame
    def __init__(self):
        super().__init__()
        # ... other initialization code ...
        
        self.queue_check_delay = 100 # Example delay in ms
        self.ui_queue = queue.Queue() # Example queue

        # --- OLD, PROBLEMATIC LINE REMOVED ---
        # Line 150: self.after(self.queue_check_delay, self.check_ui_queue)
        
        # ... rest of __init__ methods ...

    def check_ui_queue(self):
        """
        Checks the queue for new messages and updates the UI (main thread only).
        This method must also schedule its next run.
        """
        try:
            while True:
                task = self.ui_queue.get_nowait()
                # Process the task (e.g., update a label, show a message box)
                if task['type'] == 'message':
                    messagebox.showinfo("Update", task['content'])
                # Add more task processing logic here...
                self.ui_queue.task_done()
        except queue.Empty:
            pass # No updates in the queue
        except Exception as e:
            print(f"Error processing UI queue: {e}")
        
        # Line 160 (or wherever this method ends): 
        # CRITICAL: Schedule the next run of this method.
        self.after(self.queue_check_delay, self.check_ui_queue)

    # ... other methods like start_processing_thread, send_message_to_queue, etc. ...

# --- Main execution block ---
if __name__ == "__main__":
    try:
        app = ProtonGUI()
        
        # FIX: Delay the first call to check_ui_queue by a tiny amount (e.g., 50ms).
        # This ensures the 'app' object is fully instantiated before we call '.after()' on it.
        app.after(50, app.check_ui_queue) 
        
        app.mainloop() # Line 262 (or nearby)
        
    except Exception as e:
        print(f"An error occurred during application startup: {e}")
