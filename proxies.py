
import os
import random
import time
from collections import deque
from difflib import SequenceMatcher
from threading import Thread, Event
from time import sleep

import requests
import tkinter as tk
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

UNIQUE_PROXIES_MIN = 2

def validate_proxies(proxy_list):
    """
    Validates a list of proxies by first checking if they can fetch a test URL, 
    and then validating if they can load a specific page and don't show a connection issue.

    Args:
        proxy_list (list): List of proxies in the format ['ip:port', ...].

    Returns:
        list: A list of working proxies.
    """
    test_url = "https://httpbin.org/ip"  # A basic URL to verify if the proxy is working
    website_url = "https://play.freerice.com/categories/english-vocabulary?level=1"
    working_proxies = []

    print("Testing proxies...")

    for proxy in proxy_list:
        # First, validate the proxy by checking if it can fetch the test URL
        proxies = {
            "http": f"http://{proxy}",
            "https": f"http://{proxy}"
        }

        try:
            # Perform a basic connection test to httpbin
            response = requests.get(test_url, proxies=proxies, timeout=5)
            if response.status_code != 200:
                print(f"[FAILURE] Proxy failed basic test: {proxy} (Status Code: {response.status_code})")
                continue
            print(f"[SUCCESS] Proxy passed basic test: {proxy}")

        except requests.RequestException as e:
            print(f"[FAILURE] Proxy failed basic test: {proxy} (Error: {e})")
            continue

        # Now, validate the proxy on the target website using Selenium
        options = Options()
        options.add_argument(f'--proxy-server=http://{proxy}')
        options.add_argument("--headless")  # Run headless to avoid opening the browser window
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        try:
            # Initialize the WebDriver
            driver = webdriver.Chrome(options=options)
            driver.get(website_url)

            # Wait for the page to load and check for connection issue
            try:
                # Wait until the page content is loaded or a box with connection issue appears
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "card-title"))
                )
                # Check for any box-info element with the word "connection"
                infoboxes = driver.find_elements(By.CLASS_NAME, "box-info")
                connection_issue = False
                for box in infoboxes:
                    if "connection" in box.text.lower():
                        connection_issue = True
                        break

                if connection_issue:
                    print(f"[FAILURE] Proxy failed website validation: {proxy} (Connection issue detected)")
                else:
                    print(f"[SUCCESS] Proxy passed website validation: {proxy}")
                    working_proxies.append(proxy)

            except Exception as e:
                print(f"[FAILURE] Proxy failed website validation: {proxy} (Error loading page or connection issue detected)")

            driver.quit()

        except Exception as e:
            print(f"[FAILURE] Proxy failed website validation: {proxy} (Error: {e})")

        # If enough working proxies are found, return early
        if len(working_proxies) > UNIQUE_PROXIES_MIN:
            return working_proxies

    print(f"\nFinished testing. {len(working_proxies)} out of {len(proxy_list)} proxies are working.")
    return working_proxies

def fetch_proxies():
    print("Fetching proxies...")

    # Set up Chrome options
    chrome_options = webdriver.ChromeOptions()
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
    
    # Initialize the WebDriver
    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        # Navigate to the proxy site
        driver.get("https://sslproxies.org/")

        sleep(5)
        
        # Wait for the table to load
        print("Waiting for the proxy table to load...")
        table_xpath = "//table[@class='table table-striped table-bordered']"
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, table_xpath))
        )
        
        # Locate the table's scrollable element
        scrollable_div = driver.find_element(By.XPATH, "//div[@class='table-responsive fpl-list']")
        driver.execute_script("arguments[0].scrollIntoView(true);", scrollable_div)

        # Initialize lists for IPs, ports, and countries
        ips, ports, countries = [], [], []
        last_scroll_height = 0

        # Scroll incrementally to gather all data
        while True:
            # Extract visible IPs, ports, and countries
            visible_ips = [elem.text for elem in driver.find_elements(By.XPATH, f"{table_xpath}//tbody//tr/td[1]")]
            visible_ports = [elem.text for elem in driver.find_elements(By.XPATH, f"{table_xpath}//tbody//tr/td[2]")]
            visible_countries = [elem.text for elem in driver.find_elements(By.XPATH, f"{table_xpath}//tbody//tr/td[3]")]
            
            # Filter and add proxies from US
            for ip, port, country in zip(visible_ips, visible_ports, visible_countries):
                if ip and port and country == "US" and f"{ip}:{port}" not in ips:
                    ips.append(ip)
                    ports.append(port)
                    countries.append(country)

            # Stop when we've fetched at least 10 proxies
            if len(ips) > 10:
                break

            # Scroll down
            driver.execute_script("arguments[0].scrollBy(0, 100);", scrollable_div)
            sleep(0.5)  # Allow time for loading new data

            # Check if we've reached the bottom of the table
            new_scroll_height = driver.execute_script("return arguments[0].scrollTop;", scrollable_div)
            if new_scroll_height == last_scroll_height:
                break  # Exit loop if scrolling doesn't reveal new data
            last_scroll_height = new_scroll_height

        # Combine IPs and ports into proxy strings
        proxies = [f"{ip}:{port}" for ip, port in zip(ips, ports)]
        
        print(f"Fetched {len(proxies)} proxies.")
        return validate_proxies(proxies)

    finally:
        # Ensure the WebDriver quits properly
        driver.quit()