import os
import random
import time
from collections import deque
from difflib import SequenceMatcher
from threading import Thread, Event
from time import sleep

import tkinter as tk
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from colors import bcolors



import threading

from proxies import fetch_proxies
from monitor import MonitorBot, rate_limit, all_restart
from config import *
from vpn import switch_vpn_server

rate_limit_flag = threading.Event()
NACS_SPINLOCK = threading.Event()

class FreericeBot(Thread):
    def __init__(self, instance_id, stats, running_event, proxy):
        super().__init__()
        self.instance_id = instance_id
        self.stats = stats
        self.running_event = running_event
        self.driver = None
        self.proxy = proxy


    def setup_driver(self):
        """Sets up the Chrome WebDriver with necessary options for headless operation."""
        chrome_options = Options()

        if PROXIED:
            chrome_options.add_argument(f"--proxy-server=http://{self.proxy}")
        
        # Headless configuration
        chrome_options.add_argument("--headless=new")  # new headless mode for newer Chrome versions
        chrome_options.add_argument("--window-size=1920,1080")  # Required for headless
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Performance options
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--ignore-certificate-error")
        chrome_options.add_argument("--ignore-ssl-errors")
        # Anti-bot detection
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Additional performance settings
        prefs = {
            'profile.default_content_setting_values': {
            },
            'disk-cache-size': 4096
        }
        chrome_options.add_experimental_option('prefs', prefs)

        # Create service with specific options if needed
        service = Service()
        
        # Create and return the driver
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.set_window_size(1920, 1080)
        self.driver.delete_all_cookies()
        
        # Additional settings after driver creation
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # Disable webdriver mode
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")


    def similarity_ratio(self, a, b):
        """Calculates the similarity ratio between two strings."""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def login(self, username, password):
        login = False
        while not login:
            while(1):
                if rate_limit.is_set(): print(bcolors.WARNING + f"[Instance {self.instance_id}] Starting held due to rate Limited." + bcolors.ENDC)
                while rate_limit.is_set():
                    continue
                """Logs into the FreeRice website."""
                self.driver.get("https://play.freerice.com/categories/multiplication-table?level=2")
                try:
                    login_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Login')]"))
                    )
                    login_button.click()
                    sleep(1)

                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "input#login-username"))
                    )
                    self.driver.find_element(By.CSS_SELECTOR, "input#login-username").send_keys(username)
                    self.driver.find_element(By.CSS_SELECTOR, "input#login-password").send_keys(password)
                    self.driver.find_element(By.CSS_SELECTOR, "button").click()
                    sleep(1)

                    WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'game')]")
                    )).click()
                    sleep(1)
                    login = True

                except Exception as e:
                    self.driver.get("https://play.freerice.com/categories/multiplication-table?level=2")
                    break



    def is_answer_correct(self, answer_element):
        return True  # Placeholder for actual answer verification logic
    def run(self):
        while(1):
            """Main bot loop."""
            try:
                self.setup_driver()

                self.login(FREERICE_USERNAME, FREERICE_PASSWORD)

                # Wait for game to load
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "card-title"))
                )

                sleep(0.5)

                while self.running_event.is_set() and not all_restart.is_set():
                    try:
                        username_element = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, f"//a[text()='{FREERICE_USERNAME}']")
                        )
                    )
                    except Exception:
                        print(bcolors.WARNING + f"[Instance {self.instance_id}] Username element not found. Re-logging in..." + bcolors.ENDC)
                        self.login(FREERICE_USERNAME, FREERICE_PASSWORD)
                    try:
                        # Get the question
                        question_element = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.CLASS_NAME, "card-title"))
                        )
                        question = question_element.text.strip()

                        # Safely parse and calculate answer
                        try:
                            # Extract numbers from the question (e.g., "6 x 7" -> [6, 7])
                            numbers = [int(num.strip()) for num in question.split('x')]
                            if len(numbers) == 2:
                                answer = numbers[0] * numbers[1]
                            else:
                                raise ValueError("Invalid question format")
                        except (ValueError, IndexError) as e:
                            print(bcolors.FAIL + f"[Instance {self.instance_id}] Error parsing question '{question}': {e}" + bcolors.ENDC)
                            break
                        if rate_limit.is_set():
                            print(bcolors.WARNING + f"[Instance {self.instance_id}] Halted from monitor signal" + bcolors.ENDC)
                        while rate_limit.is_set():
                            time.sleep(1)
                            if not rate_limit.is_set():
                                print(bcolors.OKBLUE + f"[Instance {self.instance_id}] Restarted after rate limit cleared" + bcolors.ENDC)
                                continue

                        # Find and click correct answer button
                        buttons = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_all_elements_located((By.CLASS_NAME, "card-button"))
                        )
                        while NACS_SPINLOCK.is_set():
                            continue
                        # NACS_SPINLOCK.set()
                        answer_clicked = False
                        for button in buttons:
                            if button.text.strip() == str(answer):
                                ActionChains(self.driver).move_to_element(button).click().perform()
                                answer_clicked = True
                                self.stats['correct'] += 1
                                break
                                
                        if not answer_clicked:
                            random.choice(buttons).click()
                            self.stats['random'] += 1

                        NACS_SPINLOCK.clear()

                        self.stats['total'] += 1
                        print(f"[Instance {self.instance_id}] Stats: "
                            f"Total: {self.stats['total']}, "
                            f"Correct: {self.stats['correct']}, "
                            f"Random: {self.stats['random']}, "
                            f"Accuracy: {(self.stats['correct']/self.stats['total'])*100:.2f}%")
                        

                        try:
                            next_button = WebDriverWait(self.driver, 10).until(
                                EC.element_to_be_clickable((By.XPATH, "//button[text()='Next']"))
                            )
                            next_button.click()
                        except:
                            pass

                    except Exception as e:
                        if 'stale element reference' in str(e).lower():
                            print(bcolors.FAIL + f"[Instance {self.instance_id}] Stale element error encountered. Retrying..." + bcolors.ENDC)
                            continue
                        else:
                            print(bcolors.FAIL + f"[Instance {self.instance_id}] Error on question" + bcolors.ENDC)
                            self.restart_worker()
                            continue
            except Exception as e:
                if self.driver:
                    self.driver.quit()
            finally:
                if self.driver:
                    self.driver.quit()
            if self.driver:
                self.driver.quit()
            sleep(10)



class UIManager:
    def __init__(self, root):
        self.root = root
        self.instances = []
        self.running_event = Event()
        self.stats = {'correct': 0, 'random': 0, 'total': 0}
        self.stats_lock = stats_lock

        self.start_time = time.time()
        self.last_5_min_stats = deque()
        self.setup_ui()

    def setup_ui(self):
        self.root.title("Freerice Bot Manager")
        self.root.geometry("500x400")

        self.status_label = tk.Label(self.root, text="Bot Status: Stopped", font=("Arial", 12))
        self.status_label.pack(pady=10)

        self.stats_label = tk.Label(self.root, text="Correct: 0 | Random: 0 | Total: 0", font=("Arial", 12))
        self.stats_label.pack(pady=10)

        self.qps_label = tk.Label(self.root, text="Overall QPS: 0 | Last 5 Min QPS: 0", font=("Arial", 12))
        self.qps_label.pack(pady=10)

        self.worker_qps_label = tk.Label(self.root, text="QPS per Worker: 0", font=("Arial", 12))
        self.worker_qps_label.pack(pady=10)
        self.start_button = tk.Button(self.root, text="Start Bot", command=self.runn)
        self.start_button.pack(pady=5)
        self.start_button = tk.Button(self.root, text="Start Bot", command=self.start_bot)
        self.start_button.pack(pady=5)

        self.stop_button = tk.Button(self.root, text="Stop Bot", command=self.stop_bot, state=tk.DISABLED)
        self.stop_button.pack(pady=5)

        self.instance_label = tk.Label(self.root, text="Instances: 1")
        self.instance_label.pack(pady=5)

        self.instance_slider = tk.Scale(self.root, from_=1, to=MAX_NUM_INSTANCES, orient="horizontal", command=self.update_instances)
        self.instance_slider.pack()

    def update_instances(self, value):
        self.instance_label.config(text=f"Instances: {value}")

    def runn(self):
        while(1):
            self.start_bot()
            sleep(60 * 30)
            self.stop_bot()
            sleep(10)
        

    def start_bot(self):
        self.status_label.config(text="Bot Status: Running")
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.running_event.set()

        rate_limit.set()

        if PROXIED:
            proxies = fetch_proxies()
            random.shuffle(proxies)
            print(proxies)
        else:
            proxies = ['none', 'none']
        monitor_bot = MonitorBot()
        monitor_bot.start()

        num_instances = int(self.instance_slider.get())
        self.instances = [
            FreericeBot(i + 1, self.stats, self.running_event, proxies[i % len(proxies) - 1]) for i in range(num_instances)
        ]
        switch_vpn_server(1)
        i = 0
        for instance in self.instances:
            if rate_limit.is_set(): 
                print(bcolors.WARNING + f"[Initialization {i+1}] Starting held due to rate Limited." + bcolors.ENDC)
            while rate_limit.is_set():
                continue
            print(bcolors.OKGREEN + f"[Initialization {i+1}] Starting instance" + bcolors.ENDC)
            sleep(8)
            instance.start()
            i = i+1

        self.last_5_min_stats.clear()
        self.start_time = time.time()
        self.update_stats()

    def stop_bot(self):
        self.running_event.clear()
        for instance in self.instances:
            instance.join()

        self.instances = []
        self.status_label.config(text="Bot Status: Stopped")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

        print("VPN disconnected.")

    def update_stats(self):
        current_time = time.time()

        # Update overall QPS
        elapsed_time = current_time - self.start_time
        overall_qps = self.stats['total'] / elapsed_time if elapsed_time > 0 else 0

        # Update last 5 minutes QPS
        self.last_5_min_stats.append((current_time, self.stats['total']))
        while self.last_5_min_stats and self.last_5_min_stats[0][0] < current_time - 300:
            self.last_5_min_stats.popleft()

        if len(self.last_5_min_stats) > 1:
            first_time, first_total = self.last_5_min_stats[0]
            last_time, last_total = self.last_5_min_stats[-1]
            last_5_min_qps = (last_total - first_total) / (last_time - first_time)
        else:
            last_5_min_qps = 0

        # Update QPS per worker
        num_workers = len(self.instances)
        qps_per_worker = overall_qps / num_workers if num_workers > 0 else 0

        # Update UI
        self.stats_label.config(
            text=f"Correct: {self.stats['correct']} | Random: {self.stats['random']} | Total: {self.stats['total']}"
        )
        self.qps_label.config(
            text=f"Overall QPS: {overall_qps:.4f} | Last 5 Min QPS: {last_5_min_qps:.4f}"
        )
        self.worker_qps_label.config(text=f"QPS per Worker: {qps_per_worker:.4f}")

        if self.running_event.is_set():
            self.root.after(1000, self.update_stats)

if __name__ == "__main__":
    stats_lock = Event()
    root = tk.Tk()
    app = UIManager(root)
    root.mainloop()