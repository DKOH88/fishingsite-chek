import sys
import json
import time
import argparse
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from base_bot import BaseFishingBot

class GajuaBot(BaseFishingBot):
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
        # Base: 2025-12-17 -> 1274109
        base_date_str = "20251217"
        base_id = 1274109
        
        try:
            d_target = datetime.strptime(target_date_str, "%Y%m%d")
            d_base = datetime.strptime(base_date_str, "%Y%m%d")
            delta_days = (d_target - d_base).days
            target_id = base_id + delta_days
            
            url = f"https://ocpro.sunsang24.com/mypage/reservation_ready/{target_id}"
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

                # Check for success indicator (This part needs user feedback on selector)
                # Assuming standard SunSang24 structure, look for 'person' count or 'submit' button
                # For now, we wait for BODY to load and URL check
                if "reservation_ready" in self.driver.current_url:
                    # We are on the page. Assuming it's open if we can interact.
                    # NEED INFO: What does the page look like?
                    # Temporarily, we stop here and ask user for HTML/Screenshot.
                    self.log("✅ Page loaded! (Need further logic implementation)")
                    page_opened = True
                    break
                    
            except Exception as e:
                self.log(f"⚠️ Connection Error: {e}")
                time.sleep(retry_interval)
                
        if not page_opened:
            self.log("❌ Failed to open page.")
            return

        # 4. Reservation Logic (Placeholder)
        self.log("🚧 Reservation Logic is not implemented yet.")
        self.log("ℹ️ Please provide a screenshot or HTML source of this page to implement the form filling.")
        
        # Keep alive
        while True:
            time.sleep(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to config JSON")
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    bot = GajuaBot(config)
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()
