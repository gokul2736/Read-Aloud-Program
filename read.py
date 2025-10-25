import tkinter as tk
from tkinter import ttk, messagebox
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.alert import Alert
from selenium.common.exceptions import TimeoutException, NoAlertPresentException
import pyttsx3
import sounddevice as sd
import numpy as np
import time
import os
from threading import Thread
import uuid

class ReadAloudApp:
    # FIX 1: Changed _init_ to __init__ (double underscores)
    def __init__(self, root):
        self.root = root
        self.root.title("ReadAloud Automation")
        self.root.geometry("600x450")
        
        self.urls = []
        self.username = tk.StringVar(value="24000042")
        self.password = tk.StringVar(value="1005")
        self.status_var = tk.StringVar(value="Ready to start")
        self.remove_completed_var = tk.BooleanVar(value=True) 
        
        self.create_widgets()
        
    def create_widgets(self):
        # Username and Password
        tk.Label(self.root, text="Username:").pack(pady=5)
        tk.Entry(self.root, textvariable=self.username).pack()
        tk.Label(self.root, text="Password:").pack(pady=5)
        tk.Entry(self.root, textvariable=self.password, show="*").pack()
        
        # URL Input
        tk.Label(self.root, text="Enter URLs (one per line):").pack(pady=5)
        self.url_text = tk.Text(self.root, height=5, width=50)
        self.url_text.pack()
        
        # Buttons Frame
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=5)
        
        tk.Button(button_frame, text="Add URLs", command=self.add_urls).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Start Processing", command=self.start_processing).pack(side=tk.LEFT, padx=5)
        # NEW: Button to remove selected URLs
        tk.Button(button_frame, text="Remove Selected", command=self.remove_selected_urls).pack(side=tk.LEFT, padx=5)
        
        # Checkbox
        tk.Checkbutton(self.root, text="Remove completed URLs from list", variable=self.remove_completed_var).pack(pady=5)
        
        # Status
        tk.Label(self.root, textvariable=self.status_var, wraplength=500).pack(pady=10)
        
        # URL Listbox
        # MODIFIED: Added selectmode=tk.EXTENDED to allow multi-selection
        self.url_listbox = tk.Listbox(self.root, height=10, width=80, selectmode=tk.EXTENDED)
        self.url_listbox.pack(pady=5, padx=10)
        
    # NEW: Method to remove user-selected URLs from the list
    def remove_selected_urls(self):
        """Removes all currently selected items from the URL list and listbox."""
        # .curselection() returns a tuple of indices of selected items
        selected_indices = self.url_listbox.curselection()
        
        if not selected_indices:
            self.status_var.set("No URLs selected to remove.")
            return

        # We must iterate backwards when deleting to avoid index shifting issues.
        # For example, if we delete index 2, what was at index 3 becomes the new index 2.
        # Deleting from the end preserves the indices of the items yet to be deleted.
        for index in reversed(selected_indices):
            self.url_listbox.delete(index)
            self.urls.pop(index)
            
        self.status_var.set(f"Removed {len(selected_indices)} URLs. Total remaining: {len(self.urls)}")


    def add_urls(self):
        urls = self.url_text.get("1.0", tk.END).strip().split("\n")
        added_count = 0
        for url in urls:
            if url.strip() and url not in self.urls:
                self.urls.append(url.strip())
                self.url_listbox.insert(tk.END, url.strip())
                added_count += 1
        self.url_text.delete("1.0", tk.END)
        self.status_var.set(f"Added {added_count} new URLs. Total: {len(self.urls)}")
        
    def start_processing(self):
        if not self.urls:
            messagebox.showwarning("Warning", "No URLs to process!")
            return
        Thread(target=self.process_urls, daemon=True).start()
        
    def check_audio_devices(self):
        devices = sd.query_devices()
        print("Available audio devices:")
        for i, device in enumerate(devices):
            print(f"{i}: {device['name']}, Input Channels: {device['max_input_channels']}, Output Channels: {device['max_output_channels']}")
        vb_audio = [d for d in devices if "CABLE" in d['name'].upper()]
        if vb_audio:
            print("VB-Audio Cable detected:", vb_audio[0]['name'])
            return vb_audio[0]['name'], True
        else:
            print("WARNING: VB-Audio Cable not found. Falling back to default microphone.")
            mic = [d for d in devices if d['max_input_channels'] > 0 and "Intel" in d['name']]
            if mic:
                print("Using fallback microphone:", mic[0]['name'])
                return mic[0]['name'], False
            raise Exception("No suitable input device found. Install VB-Audio Cable or ensure a microphone is available.")

    def test_audio_routing(self, device_name, is_vb_audio):
        self.status_var.set(f"Testing audio routing with {device_name}...")
        engine = pyttsx3.init()
        engine.setProperty('rate', 250)
        engine.say("Testing audio routing")
        fs = 44100
        with sd.InputStream(device=device_name, samplerate=fs, channels=1) as stream:
            recording = sd.rec(int(3 * fs), samplerate=fs, channels=1, device=device_name)
            engine.runAndWait()
            sd.wait()
        max_amplitude = np.max(np.abs(recording))
        print(f"Test recording max amplitude: {max_amplitude:.4f}")
        if max_amplitude < 0.01:
            raise Exception(f"Audio routing test failed with {device_name}. No audio detected. Check device settings.")
        self.status_var.set("Audio routing test passed.")

    def process_urls(self):
        # This method remains unchanged from the previous version
        options = Options()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--use-fake-ui-for-media-stream")
        options.add_argument("--disable-notifications")
        driver = webdriver.Chrome(options=options)
        
        try:
            audio_device, is_vb_audio = self.check_audio_devices()
            if not is_vb_audio:
                self.status_var.set("WARNING: Using physical microphone. Audio may not route correctly without VB-Audio Cable.")
            self.test_audio_routing(audio_device, is_vb_audio)
            
            engine = pyttsx3.init()
            engine.setProperty('rate', 250)
            engine.setProperty('volume', 1.5)
            
            self.status_var.set("Logging in...")
            driver.get("https://lms2.ai.saveetha.in/login/index.php")
            driver.find_element(By.ID, "username").send_keys(self.username.get())
            driver.find_element(By.ID, "password").send_keys(self.password.get())
            login_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "loginbtn"))
            )
            login_button.click()
            try:
                WebDriverWait(driver, 10).until(EC.url_contains("saveetha.in"))
                self.status_var.set("Login successful")
            except TimeoutException:
                raise Exception("Login failed. Check credentials or network.")
            
            processed_count = 0
            total_urls = len(self.urls)

            while self.urls:
                url = self.urls[0] 
                listbox_index = processed_count 
                
                self.status_var.set(f"Processing URL {processed_count + 1}/{total_urls}: {url}")
                self.url_listbox.selection_clear(0, tk.END)
                # Find the current index of the URL being processed in the listbox
                try:
                    current_listbox_items = list(self.url_listbox.get(0, tk.END))
                    actual_index = current_listbox_items.index(url)
                    self.url_listbox.selection_set(actual_index)
                except ValueError:
                    # This case handles if the item was somehow removed during processing
                    print(f"Warning: URL '{url}' not found in listbox for highlighting.")

                driver.get(url)
                print(f"Navigated to {url}")
                
                retries = 5
                for attempt in range(retries):
                    try:
                        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "mod_readaloud_button_startnoshadow")))
                        break
                    except TimeoutException:
                        if attempt < retries - 1:
                            self.status_var.set(f"Retrying URL {url} due to page load issue...")
                            time.sleep(5)
                            driver.refresh()
                        else:
                            raise Exception(f"Failed to load {url} after retries")
                
                read_button = WebDriverWait(driver, 30).until(
                    EC.element_to_be_clickable((By.ID, "mod_readaloud_button_startnoshadow"))
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", read_button)
                try:
                    read_button.click()
                    print("Clicked 'Read' button with Selenium")
                except:
                    driver.execute_script("arguments[0].click();", read_button)
                    print("Clicked 'Read' button with JavaScript")
                
                def switch_to_iframe_with_button(selector):
                    iframes = driver.find_elements(By.TAG_NAME, "iframe")
                    if not iframes:
                        return False
                    for i, iframe in enumerate(iframes):
                        try:
                            driver.switch_to.frame(iframe)
                            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                            return True
                        except TimeoutException:
                            driver.switch_to.default_content()
                    return False
                
                record_success = False
                for attempt in range(3):
                    try:
                        if switch_to_iframe_with_button("button.poodll_start-recording_readaloud[aria-label='Record']"):
                            print("Found record button in iframe")
                        else:
                            driver.switch_to.default_content()
                            print("Searching for record button in main content")
                        
                        record_button = WebDriverWait(driver, 30).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.poodll_start-recording_readaloud[aria-label='Record']"))
                        )
                        driver.execute_script("arguments[0].scrollIntoView(true);", record_button)
                        driver.execute_script("arguments[0].click();", record_button)
                        print("Clicked 'Record' button with JavaScript")
                        time.sleep(1)
                        record_success = True
                        break
                    except Exception as e:
                        print(f"Record attempt {attempt + 1} failed: {e}")
                        driver.switch_to.default_content()
                        time.sleep(2)
                
                if not record_success:
                    raise Exception(f"Failed to click 'Record' button for {url}")
                
                try:
                    WebDriverWait(driver, 3).until(EC.alert_is_present())
                    alert = Alert(driver)
                    alert.accept()
                    print("Accepted JavaScript microphone alert")
                except (TimeoutException, NoAlertPresentException):
                    print("No JavaScript alert found, continuing...")
                
                driver.switch_to.default_content()
                passage_elements = driver.find_elements(By.CLASS_NAME, "mod_readaloud_grading_passageword")
                passage_text = " ".join([elem.text for elem in passage_elements])
                print("Extracted passage:", passage_text)
                self.status_var.set(f"Speaking text for {url}...")
                start_time = time.time()
                engine.say(passage_text)
                engine.runAndWait()
                elapsed_time = time.time() - start_time
                print(f"Finished speaking in {elapsed_time:.2f} seconds")
                
                stop_success = False
                for attempt in range(3):
                    try:
                        stop_selector = "button.poodll_mediarecorder_button_readaloud.poodll_stop-recording_readaloud[aria-label='Stop']"
                        if switch_to_iframe_with_button(stop_selector):
                            print("Found stop button in iframe")
                        else:
                            driver.switch_to.default_content()
                            print("Searching for stop button in main content")
                        
                        stop_button = WebDriverWait(driver, 30).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, stop_selector))
                        )
                        driver.execute_script("arguments[0].scrollIntoView(true);", stop_button)
                        driver.execute_script("arguments[0].removeAttribute('disabled')", stop_button)
                        driver.execute_script("arguments[0].click();", stop_button)
                        print("Clicked 'Stop' button with JavaScript")
                        stop_success = True
                        break
                    except Exception as e:
                        print(f"Stop button attempt {attempt + 1} failed: {e}")
                        driver.switch_to.default_content()
                        time.sleep(2)
                
                if not stop_success:
                    raise Exception(f"Failed to click 'Stop' button for {url}")
                
                self.status_var.set(f"Waiting for audio upload for {url}...")
                try:
                    time.sleep(10)
                    driver.switch_to.default_content()
                    WebDriverWait(driver, 30).until(
                        EC.element_to_be_clickable((By.ID, "mod_readaloud_button_backtotop"))
                    )
                    self.status_var.set(f"Audio upload completed for {url}")
                except TimeoutException as e:
                    self.status_var.set(f"Failed to confirm audio upload for {url}: {e}")
                    raise
                
                # Logic for removing or highlighting the URL after completion
                try:
                    # Find the index of the completed URL in the current listbox state
                    current_listbox_items = list(self.url_listbox.get(0, tk.END))
                    completed_index_in_listbox = current_listbox_items.index(url)
                
                    if self.remove_completed_var.get():
                        self.url_listbox.delete(completed_index_in_listbox)
                    else:
                        self.url_listbox.itemconfig(completed_index_in_listbox, {'bg': 'light green'})
                except ValueError:
                     print(f"Warning: Completed URL '{url}' was already removed from the listbox.")


                self.urls.pop(0)
                processed_count += 1
            
            self.status_var.set("All URLs processed successfully!")
            messagebox.showinfo("Success", "All URLs processed successfully!")
            
        except Exception as e:
            self.status_var.set(f"Error: {e}")
            messagebox.showerror("Error", f"An error occurred: {e}")
            
        finally:
            time.sleep(2)
            driver.quit()
            self.status_var.set("Browser closed. Ready to start again.")

if __name__ == "__main__":
    root = tk.Tk()
    app = ReadAloudApp(root)
    root.mainloop()