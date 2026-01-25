from selenium import webdriver
from selenium.webdriver.common.by import By
import time

URL = "http://xn--v42bv0rcoar53c6lb.kr/_core/module/reservation_boat_v5.2_seat1/popu2.step1.php?date=20260302&PA_N_UID=5030"

def inspect_site():
    print(f"🔍 Inspecting: {URL}")
    options = webdriver.ChromeOptions()
    options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(options=options)
    
    try:
        driver.get(URL)
        print("✅ Page loaded. Analyzing inputs...")
        time.sleep(2)
        
        inputs = driver.find_elements(By.TAG_NAME, "input")
        print(f"\n--- [INPUTS FOUND: {len(inputs)}] ---")
        for i, el in enumerate(inputs):
            try:
                eid = el.get_attribute("id")
                ename = el.get_attribute("name")
                etype = el.get_attribute("type")
                eph = el.get_attribute("placeholder")
                print(f"#{i} | ID: {eid} | NAME: {ename} | TYPE: {etype} | PH: {eph}")
            except: pass

        buttons = driver.find_elements(By.TAG_NAME, "a")
        print(f"\n--- [LINKS/BUTTONS FOUND: {len(buttons)}] ---")
        for i, el in enumerate(buttons):
            try:
                text = el.text.strip()
                href = el.get_attribute("href")
                onclick = el.get_attribute("onclick")
                if text or onclick:
                    print(f"#{i} | TEXT: {text} | ONCLICK: {onclick} | HREF: {href}")
            except: pass
            
        print("\n✅ Inspection Complete. Check the console output.")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    inspect_site()
