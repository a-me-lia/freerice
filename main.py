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

import argparse
import signal
import sys
import threading
from threading import Thread, Event
from collections import deque
from time import sleep, time
import random




import threading

from proxies import fetch_proxies
from monitor import MonitorBot, rate_limit, all_restart
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


import psutil as psutil

class BotManager:
    def __init__(self):
        self.instances = []
        self.running_event = Event()
        self.stats = {'correct': 0, 'random': 0, 'total': 0}
        self.stats_lock = threading.Lock()
        self.start_time = time()
        self.last_5_min_stats = deque()
        self.instance_lock = threading.Lock()
        
        # Stats printing thread
        self.stats_thread = None
        self.print_stats_event = Event()
        
        # Auto-scaling settings
        self.last_scale_time = time()
        self.scale_interval = 10  # seconds between scaling checks
        self.memory_threshold = 1.0  # GB
        self.chrome_memory_usage = 0.3  # GB per instance
        self.scaling_thread = None
        self.scaling_event = Event()

    def get_available_memory(self):
        """Get available memory in GB"""
        return psutil.virtual_memory().available / (1024 * 1024 * 1024)

    def calculate_target_instances(self):
        """Calculate target number of instances based on available memory"""
        available_memory = self.get_available_memory()
        target = int((available_memory - self.memory_threshold) / self.chrome_memory_usage)
        return max(1, min(target, 100))  # Keep between 1 and 100 instances

    def scale_instances(self):
        """Add or remove instances based on available memory"""
        while self.scaling_event.is_set():
            current_time = time()
            if current_time - self.last_scale_time >= self.scale_interval:
                available_memory = self.get_available_memory()
                current_instances = len(self.instances)
                
                with self.instance_lock:
                    if available_memory < self.memory_threshold and current_instances > 1:
                        # Remove one instance
                        instance = self.instances.pop()
                        instance.running_event.clear()
                        instance.join()
                        print(f"\n[Scaling] Removed instance (memory: {available_memory:.2f}GB)")
                    elif available_memory > self.memory_threshold + 0.5:  # Add buffer to prevent oscillation
                        target_instances = self.calculate_target_instances()
                        if current_instances < target_instances:
                            # Add one instance
                            new_instance = FreericeBot(
                                current_instances + 1, 
                                self.stats, 
                                self.running_event, 
                                'none'
                            )
                            new_instance.start()
                            self.instances.append(new_instance)
                            print(f"\n[Scaling] Added instance (memory: {available_memory:.2f}GB)")
                
                self.last_scale_time = current_time
            sleep(1)

    def print_stats_loop(self):
        """Continuously print stats until stopped"""
        while self.print_stats_event.is_set():
            self.print_stats()
            sleep(1)

    def print_stats(self):
        """Print current statistics"""
        current_time = time()
        elapsed_time = current_time - self.start_time
        available_memory = self.get_available_memory()
        
        # Calculate QPS
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

        # Calculate QPS per worker
        num_workers = len(self.instances)
        qps_per_worker = overall_qps / num_workers if num_workers > 0 else 0

        # Clear line and print stats
        print(f"\r[Stats] Memory: {available_memory:.2f}GB | "
              f"Instances: {num_workers} | "
              f"Correct: {self.stats['correct']} | "
              f"Random: {self.stats['random']} | "
              f"Total: {self.stats['total']} | "
              f"QPS: {overall_qps:.2f} | "
              f"5min QPS: {last_5_min_qps:.2f} | "
              f"QPS/Worker: {qps_per_worker:.2f}")

    def start_bot(self, initial_instances):
        """Start the bot with initial number of instances"""
        print(f"Starting with {initial_instances} instances...")

        self.monitor_bot = MonitorBot(USE_VPN)
        self.monitor_bot.start()
            
        self.running_event.set()
        self.print_stats_event.set()
        self.scaling_event.set()

        # Start stats printing thread
        self.stats_thread = Thread(target=self.print_stats_loop)
        self.stats_thread.start()

        # Start scaling thread
        self.scaling_thread = Thread(target=self.scale_instances)
        self.scaling_thread.start()

        # Handle proxies if enabled
        proxies = ['none', 'none']
        if PROXIED:
            proxies = fetch_proxies()
            random.shuffle(proxies)
            print("Proxies:", proxies)

        # Start VPN if enabled
        if USE_VPN:
            switch_vpn_server(1)

        # Create and start initial instances
        for i in range(initial_instances):
            new_instance = FreericeBot(
                i + 1, 
                self.stats, 
                self.running_event, 
                proxies[i % len(proxies) - 1] if PROXIED else 'none'
            )
            print(f"\r[Info] Starting instance {i+1}...")
            sleep(8)
            new_instance.start()
            self.instances.append(new_instance)

        self.last_5_min_stats.clear()
        self.start_time = time()

    def scale_instances(self):
        """Add or remove instances based on available memory"""
        while self.scaling_event.is_set():
            current_time = time()
            if current_time - self.last_scale_time >= self.scale_interval:
                available_memory = self.get_available_memory()
                current_instances = len(self.instances)
                
                with self.instance_lock:
                    if available_memory < self.memory_threshold and current_instances > 1:
                        # Remove one instance
                        instance = self.instances.pop()
                        instance.running_event.clear()
                        instance.join()
                        print(f"\n[Scaling] Removed instance (memory: {available_memory:.2f}GB)")
                    elif available_memory > self.memory_threshold + 0.5:
                        target_instances = self.calculate_target_instances()
                        if current_instances < target_instances:
                            # Add one instance with proper proxy if enabled
                            proxy = 'none'
                            if PROXIED:
                                proxies = fetch_proxies()
                                proxy = proxies[current_instances % len(proxies) - 1]
                            
                            new_instance = FreericeBot(
                                current_instances + 1, 
                                self.stats, 
                                self.running_event,
                                proxy
                            )
                            new_instance.start()
                            self.instances.append(new_instance)
                            print(f"\n[Scaling] Added instance (memory: {available_memory:.2f}GB)")
                
                self.last_scale_time = current_time
            sleep(1)

def main():
    parser = argparse.ArgumentParser(description='Freerice Bot Manager')
    parser.add_argument('-i', '--instances', type=int, default=1,
                      help='Initial number of instances (default: 1)')
    parser.add_argument('-c', '--continuous', action='store_true',
                      help='Run continuously with automatic restarts')
    parser.add_argument('-u', '--username', type=str, default='mikoyae',
                      help='Freerice username (default: mikoyae)')
    parser.add_argument('-p', '--password', type=str, default='GingerAil541!',
                      help='Freerice password')
    parser.add_argument('--vpn', action='store_true',
                      help='Enable VPN usage')
    parser.add_argument('--proxy', action='store_true',
                      help='Enable proxy usage')

    args = parser.parse_args()

    # Set global constants
    global FREERICE_USERNAME, FREERICE_PASSWORD, MONITOR_FREQUENCY, USE_VPN, PROXIED
    FREERICE_USERNAME = args.username
    FREERICE_PASSWORD = args.password
    USE_VPN = 1 if args.vpn else 0
    PROXIED = 1 if args.proxy else 0

    manager = BotManager()
    
    try:
        if args.continuous:
            manager.run_continuous(args.instances)
        else:
            manager.start_bot(args.instances)
            # Wait for interrupt
            while True:
                sleep(1)
    except KeyboardInterrupt:
        manager.stop_bot()

if __name__ == "__main__":
    stats_lock = Event()
    main()

