import sys
import json
import time
import argparse
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from base_bot import BaseFishingBot

class BigBossBot(BaseFishingBot):
    def run(self):
        self.setup_driver()
        wait = WebDriverWait(self.driver, 30)

        # 1. Parse Config
        target_date_str = self.config.get('target_date', '20260901')
        target_time = self.config.get('target_time', '09:00:00')
        test_mode = self.config.get('test_mode', False)
        self.simulation_mode = self.config.get('simulation_mode', False)
        
        user_name = self.config.get('user_name', '')
        user_depositor = self.config.get('user_depositor', '')
        user_phone = self.config.get('user_phone', '')
        
        # 2. Calculate URL (Date-based ID)
        # Base: 2025-12-17 -> 1344352 (BigBoss)
        base_date_str = "20251217"
        base_id = 1344352
        
        try:
            d_target = datetime.strptime(target_date_str, "%Y%m%d")
            d_base = datetime.strptime(base_date_str, "%Y%m%d")
            delta_days = (d_target - d_base).days
            target_id = base_id + delta_days
            
            url = f"https://bigboss24.sunsang24.com/mypage/reservation_ready/{target_id}"
            self.log(f"🎯 Target URL Calculated: {url} (ID: {target_id}, Delta: {delta_days})")
            
        except Exception as e:
            self.log(f"❌ Date URL Calculation Failed: {e}")
            return

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

        # 3. Start "Smart Refresh Loop"
        self.log(f"🔥 Starting Attack Loop on: {url}")
        
        max_retries = 1000
        retry_interval = 1 # seconds
        
        page_opened = False
        
        for attempt in range(max_retries):
            try:
                self.driver.get(url)
                
                # Check for Server Errors
                if "Bad Gateway" in self.driver.title or "502" in self.driver.page_source:
                    self.log(f"⚠️ Server Error (502). Refreshing... ({attempt+1}/{max_retries})")
                    time.sleep(0.5)
                    continue

                # Check for success indicator
                if "reservation_ready" in self.driver.current_url:
                    self.log("✅ Page loaded! Starting form filling...")
                    page_opened = True
                    break
                    
            except Exception as e:
                self.log(f"⚠️ Connection Error: {e}")
                time.sleep(retry_interval)
                
        if not page_opened:
            self.log("❌ Failed to open page.")
            return

        # 4. Form Filling
        try:
            # 4.1 Person Count (Click Plus Button N times)
            self.log("👥 Setting Person Count...")
            target_count = int(self.config.get('person_count', 1))
            
            # Find the Plus Button Image
            plus_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//img[contains(@src, 'btn_plus.gif')]")))
            
            for i in range(target_count):
                self.log(f"  ➕ Clicking plus button ({i+1}/{target_count})...")
                plus_btn.click()
                time.sleep(0.1)

            # 4.2 Fill Name (name="name")
            self.log(f"✍️ Filling Name: {user_name}")
            driver_name = self.driver.find_element(By.NAME, "name")
            driver_name.clear()
            driver_name.send_keys(user_name)

            # 4.3 Fill Depositor (name="deposit_name")
            depositor = user_depositor if user_depositor else user_name
            self.log(f"✍️ Filling Depositor: {depositor}")
            driver_deposit = self.driver.find_element(By.NAME, "deposit_name")
            driver_deposit.clear()
            driver_deposit.send_keys(depositor)

            # 4.4 Fill Phone (name="phone2", name="phone3")
            # Parse phone
            p1, p2, p3 = "", "", ""
            if "-" in user_phone:
                parts = user_phone.split("-")
                if len(parts) == 3: p1, p2, p3 = parts
            elif len(user_phone) == 11:
                p1, p2, p3 = user_phone[:3], user_phone[3:7], user_phone[7:]
            
            if p2 and p3:
                 self.log(f"📞 Filling Phone: {p2}-{p3}")
                 self.driver.find_element(By.NAME, "phone2").send_keys(p2)
                 self.driver.find_element(By.NAME, "phone3").send_keys(p3)
            else:
                 self.log(f"⚠️ Phone format error: {user_phone}")

            # 4.5 Agree All (name="all_check")
            self.log("✅ Clicking 'Agree All' checkbox...")
            try:
                agree_chk = self.driver.find_element(By.NAME, "all_check")
                if not agree_chk.is_selected():
                    agree_chk.click()
            except Exception as e:
                self.log(f"⚠️ Agree Checkbox error: {e}")

            # 4.6 Submit Button (id="btn_payment")
            self.log("🚀 Clicking 'Submit Reservation' button...")
            try:
                submit_btn = self.driver.find_element(By.ID, "btn_payment")
                self.driver.execute_script("arguments[0].click();", submit_btn) # JS click for safety
                
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
             self.log(f"⚠️ Error in Form Filling: {e}")
        
        # Keep alive
        while True:
            time.sleep(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to config JSON")
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    bot = BigBossBot(config)
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()
