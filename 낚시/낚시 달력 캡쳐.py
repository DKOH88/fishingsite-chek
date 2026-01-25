import os
import time
import argparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def capture_element_screenshot(file_path, output_path):
    print(f"Opening file: {file_path}")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=2300,3000") # Wider to prevent wrapping
    chrome_options.add_argument("--hide-scrollbars")
    chrome_options.add_argument("--force-device-scale-factor=2") # Higher DPI for better quality

    driver = webdriver.Chrome(options=chrome_options)

    try:
        file_url = f"file:///{file_path.replace(os.sep, '/')}"
        driver.get(file_url)
        time.sleep(1) # Wait for render

        # Find the main container
        container = driver.find_element(By.CLASS_NAME, "container")
        print("Container element found.")

        # Take screenshot of the element only (crops whitespace)
        container.screenshot(output_path)
        print(f"Screenshot saved to: {output_path}")

    except Exception as e:
        print(f"Error extracting screenshot: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Capture calendar screenshot")
    parser.add_argument("--input", "-i", type=str, help="Input HTML file path")
    parser.add_argument("--output", "-o", type=str, help="Output PNG file path")
    
    args = parser.parse_args()
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    target_html = args.input if args.input else os.path.join(base_dir, "fishing_calendar.html")
    output_png = args.output if args.output else os.path.join(base_dir, "fishing_calendar.png")
    
    if os.path.exists(target_html):
        capture_element_screenshot(target_html, output_png)
    else:
        print(f"File not found: {target_html}")
