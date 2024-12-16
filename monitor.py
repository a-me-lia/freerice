import threading
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from threading import Thread


from vpn import switch_vpn_server

# Shared rate_limit flag
rate_limit = threading.Event()
all_restart = threading.Event()
from colors import bcolors

class MonitorBot(Thread):
    def __init__(self, vpn):
        super().__init__()
        self.driver = None
        self.running = True
        self.times = 0
        self.USE_VPN = vpn

    def setup_driver(self):
        """Set up the Selenium WebDriver."""
        chrome_options = Options()
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


    def run(self):
        """Main loop to monitor the webpage."""

        while(1):
            try:
                self.setup_driver()
                self.driver.get("https://play.freerice.com/categories/multiplication-table?level=2")
                print(bcolors.OKCYAN + "[Monitor] Monitor up" + bcolors.ENDC)
                time.sleep(8)

                while self.running:

                        
                    try:
                        # Check for the presence of the div with class name 'card-title'
                        try:
                            WebDriverWait(self.driver, 15).until(
                                EC.presence_of_element_located((By.CLASS_NAME, "card-title"))
                            )

                            # If found, unset the rate limit flag
                            if rate_limit.is_set():
                                print(bcolors.OKCYAN + "[Monitor] Active content detected. Unsetting rate limit flag." + bcolors.ENDC)
                                rate_limit.clear()
                                if self.times % 16 == 15:
                                    all_restart.set()
                                    time.sleep(60)
                                    all_restart.clear()
                                    
                        
                        except:
                            # If not found, set the rate limit flag
                            if not rate_limit.is_set():
                                print(bcolors.WARNING + "[Monitor] No active content detected. Setting rate limit flag." + bcolors.ENDC)
                                if self.USE_VPN:
                                    switch_vpn_server(self.times)
                                self.times = self.times + 1
                                rate_limit.set() 
                            else:
                                print(bcolors.WARNING + "[Monitor] Switching server" + bcolors.ENDC)
                                if self.USE_VPN:
                                    switch_vpn_server(self.times)

                                self.times = self.times + 1

                        time.sleep(8)
                        self.driver.refresh()

                    except Exception as e:
                        print(f"[Monitor] Error in monitor bot: {e}")

            except:
                if self.driver:
                    self.driver.quit()

    def stop(self):
        """Stop the monitoring bot."""
        self.running = False
        if self.driver:
            self.driver.quit()
