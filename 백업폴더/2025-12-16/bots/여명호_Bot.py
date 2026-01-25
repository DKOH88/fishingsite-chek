import sys
import json
import time
import argparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from base_bot import BaseFishingBot

class YeomyeongBot(BaseFishingBot):
    def run(self):
        self.setup_driver()
        wait = WebDriverWait(self.driver, 30)

        # 1. Parse Config
        target_date = self.config.get('target_date', '20260302')
        target_time = self.config.get('target_time', '09:00:00')
        test_mode = self.config.get('test_mode', False)
        self.simulation_mode = self.config.get('simulation_mode', False)
        
        user_name = self.config.get('user_name', '')
        user_depositor = self.config.get('user_depositor', '')
        user_phone = self.config.get('user_phone', '')
        user_pw = self.config.get('user_pw', '1234')
        
        user_pw = self.config.get('user_pw', '1234')
        
        # 2. Build URL (Prepare Early)
        base_url = "http://xn--v42bv0rcoar53c6lb.kr/_core/module/reservation_boat_v5.2_seat1/popu2.step1.php"
        url = f"{base_url}?date={target_date}&PA_N_UID=5030"
        
        # 2.5 Pre-load / Warm-up
        self.log(f"🌍 Pre-loading: {url}")
        try:
             self.driver.get(url)
             self.log("✅ Page pre-loaded. Waiting for target time...")
        except Exception as e:
             self.log(f"⚠️ Pre-load failed (will retry at target time): {e}")

        # 1.5 Scheduling
        if not test_mode:
            self.log(f"⏰ Scheduled for {target_time}...")
            self.wait_until_target_time(target_time)
        else:
            self.log("🚀 TEST MODE ACTIVE: Skipping wait, running immediately!")

        # 3. Start "Smart Refresh Loop" at target time
        self.log(f"🔥 Starting Attack Loop on: {url}")
        
        # Retry config
        max_retries = 1000 # Try for about 20~30 minutes
        retry_interval = 1 # seconds
        
        step1_success = False

        for attempt in range(max_retries):
            try:
                self.driver.get(url)
                
                # Check for Server Errors
                if "Bad Gateway" in self.driver.title or "502" in self.driver.page_source:
                    self.log(f"⚠️ Server Error (502). Refreshing... ({attempt+1}/{max_retries})")
                    time.sleep(0.5)
                    continue

                # Check if we are potentially on the right page
                # target: class="ps_selis" which holds the fishing names
                try:
                    # Quick check for presence
                    WebDriverWait(self.driver, 1).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "ps_selis"))
                    )
                except:
                    # Not found yet, maybe site not open or loading
                    self.log(f"⏳ Site not ready (Fishing types not found). Retrying... ({attempt+1}/{max_retries})")
                    time.sleep(retry_interval)
                    continue
                
                # If we get here, the elements are likely present. Try to select.
                self.log("🎣 Looking for fishing type selection...")
                
                target_keywords = []
                target_ship_cfg = self.config.get('target_ship', '').strip()
                if target_ship_cfg:
                    target_keywords.append(target_ship_cfg)
                target_keywords.extend(['갑오징어', '쭈꾸미', '문어'])
                
                found_click = False
                for keyword in target_keywords:
                    # Logic same as before
                    # ...
                    xpath_span = f"//span[contains(@class, 'ps_selis') and contains(text(), '{keyword}')]"
                    spans = self.driver.find_elements(By.XPATH, xpath_span)
                    
                    if not spans: continue
                        
                    for span in spans:
                        label = span.find_element(By.XPATH, "./..")
                        target_id = label.get_attribute("for")
                        if target_id:
                            radio_btn = self.driver.find_element(By.ID, target_id)
                            self.log(f"⚡ Found target: '{keyword}' (ID: {target_id}) -> Clicking!")
                            self.driver.execute_script("arguments[0].click();", radio_btn)
                            found_click = True
                            break
                    if found_click: break
                
                if found_click:
                    step1_success = True
                    break # Success!
                else:
                     self.log("⚠️ Fishing types found, but no matching keyword. Retrying logic won't help here unless content changes.")
                     # In this specific case, maybe we should stop or manual intervention. 
                     # For safety, let's break and let user handle it, assuming page loaded but target is full/not listed.
                     break 

            except Exception as e:
                self.log(f"⚠️ Connection Error: {e}. Retrying...")
                time.sleep(retry_interval)
        
        if not step1_success:
             self.log("❌ Failed to enter reservation step 1 after maximum retries.")
             # return or exit? For now just try to proceed or exit
             # return 


        # 4. Step 1.5: Select Person Count (BI_IN)
        # The select box might appear dynamically or be present but disabled.
        # We wait for it to be visible.
        self.log("👥 Waiting for Person Count (BI_IN) selection...")
        try:
            from selenium.webdriver.support.ui import Select
            
            # Wait for element
            select_el = wait.until(EC.element_to_be_clickable((By.ID, "BI_IN")))
            
            # Check current value to avoid redundant selection
            select_obj = Select(select_el)
            current_val = select_obj.first_selected_option.get_attribute("value")
            
            target_count = self.config.get('person_count', '1')
            
            if current_val != target_count:
                self.log(f"👥 Selecting {target_count} person(s)...")
                select_obj.select_by_value(target_count)
            else:
                self.log(f"👥 Already set to {target_count} person(s).")
                
        except Exception as e:
            self.log(f"⚠️ Error selecting person count: {e}")

        except Exception as e:
            self.log(f"⚠️ Error in Step 1: {e}")

        # 5. Step 2: Seat Selection & Info
        self.log("🪑 Waiting for Input Page (Step 2)...")
        try:
            # 5.1 Fill Name (BI_NAME)
            # It has no ID, only name="BI_NAME"
            name_input = wait.until(EC.element_to_be_clickable((By.NAME, "BI_NAME")))
            self.log(f"✍️ Filling Name: {user_name}")
            name_input.clear()
            name_input.send_keys(user_name)
            
            # 5.2 Fill Depositor (BI_BANK)
            # It has ID="BI_BANK"
            bank_input = self.driver.find_element(By.ID, "BI_BANK")
            depositor = user_depositor if user_depositor else user_name
            self.log(f"✍️ Filling Depositor: {depositor}")
            bank_input.clear()
            bank_input.send_keys(depositor)

            # 5.3 Fill Phone Number (BI_TEL1, BI_TEL2, BI_TEL3)
            # Parse phone number (e.g., 010-1234-5678 or 01012345678)
            p1, p2, p3 = "", "", ""
            if "-" in user_phone:
                parts = user_phone.split("-")
                if len(parts) == 3:
                    p1, p2, p3 = parts
            elif len(user_phone) == 11:
                p1, p2, p3 = user_phone[:3], user_phone[3:7], user_phone[7:]
            
            if p1 and p2 and p3:
                self.log(f"📞 Filling Phone: {p2}-{p3} (Skipping 010)")
                
                # t1 = self.driver.find_element(By.ID, "BI_TEL1")
                # t1.clear()
                # t1.send_keys(p1)
                
                t2 = self.driver.find_element(By.ID, "BI_TEL2")
                t2.clear()
                t2.send_keys(p2)
                
                t3 = self.driver.find_element(By.ID, "BI_TEL3")
                t3.clear()
                t3.send_keys(p3)
            else:
                self.log(f"⚠️ Phone number format warning: {user_phone}")

            # 5.4 Agree All
            # <input type="radio" name="all_agree" value="Y" ...>
            self.log("✅ Clicking 'Agree All'...")
            try:
                agree_btn = self.driver.find_element(By.XPATH, "//input[@name='all_agree' and @value='Y']")
                self.driver.execute_script("arguments[0].click();", agree_btn)
            except Exception as e:
                self.log(f"⚠️ 'Agree All' button not found or error: {e}")

            # 5.5 Submit Button
            # 5.5 Submit Button
            self.log("🚀 Clicking 'Submit Reservation' button...")
            try:
                submit_btn = self.driver.find_element(By.ID, "submit")
                self.driver.execute_script("arguments[0].click();", submit_btn)
                
                # Handle Confirmation Alert
                self.log("🔔 Waiting for confirmation alert...")
                alert = wait.until(EC.alert_is_present())
                alert_text = alert.text
                self.log(f"🔔 Alert found: {alert_text}")
                
                if not self.simulation_mode:
                    self.log("🚀 FINAL EXECUTION: Accepting alert...")
                    alert.accept()
                    self.log("✅ Reservation submitted! Check the browser.")
                else:
                    self.log("🛑 SIMULATION MODE: Submit clicked & Alert shown. Stopping here.")
                    
            except Exception as e:
                self.log(f"⚠️ Submit button/alert error: {e}")

        except Exception as e:
            self.log(f"ℹ️ Input Autofill skipped or failed: {e}")

        self.log("✅ Bot setup complete. Monitor the browser for further actions.")
        
        # Keep alive
        while True:
            time.sleep(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to config JSON")
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    bot = YeomyeongBot(config)
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()
