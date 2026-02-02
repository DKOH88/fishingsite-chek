import requests
import time
import statistics
import os
import socket
import subprocess
import platform
import urllib3
from urllib.parse import urlparse

# 🚀 Disable SSL Warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 🚀 Monkey Patch: FORCE IPv4 ONLY (Keeping this as a good practice for speed)
old_getaddrinfo = socket.getaddrinfo
def new_getaddrinfo(*args, **kwargs):
    responses = old_getaddrinfo(*args, **kwargs)
    return [response for response in responses if response[0] == socket.AF_INET]
socket.getaddrinfo = new_getaddrinfo

# 🚀 Force Disable Proxy
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''
os.environ['NO_PROXY'] = '*'

TARGETS = [
    "http://www.thefishing.co.kr",  # 더피싱
    "https://www.sunsang24.com",    # 선상24
    "https://camping.gtdc.or.kr/DZ_reservation/reserCamping_v3.php?xch=reservation&xid=camping_reservation",
    "http://www.sungryungho.com/_core/module/reservation_boat_v5.2_seat1/popu2.step1.php?date=20261006&PA_N_UID=830"
]

def get_ip_address(url):
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        return socket.gethostbyname(hostname)
    except Exception:
        return "Unknown"

def measure_rtt(url, count=10):
    ip = get_ip_address(url)
    print(f"\n📡 Testing RTT for {url}")
    print(f"   ➡️  Resolved IP (IPv4): {ip}")
    print(f"   🔓 SSL Verification: DISABLED (Fastest Mode)")
    
    rtts = []
    ttfbs = []
    
    session = requests.Session()
    session.trust_env = False
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })
    
    try:
        # verify=False added here
        session.get(url, stream=True, timeout=5, verify=False)
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    print(f"   Running {count} requests...")
    
    for i in range(count):
        start = time.perf_counter()
        try:
            # verify=False added here
            resp = session.get(url, stream=True, timeout=5, verify=False)
            ttfb = (time.perf_counter() - start) * 1000 
            content = resp.content 
            duration = (time.perf_counter() - start) * 1000 
            
            rtts.append(duration)
            ttfbs.append(ttfb)
            status = f"✅ {resp.status_code}"
        except Exception as e:
            duration = 0
            ttfb = 0
            status = f"❌ {e}"
        
        print(f"   [{i+1}/{count}] TTFB: {ttfb:.2f}ms | Total: {duration:.2f}ms ({status})")
        time.sleep(0.5)

    if rtts:
        avg = statistics.mean(rtts)
        avg_ttfb = statistics.mean(ttfbs)
        min_v = min(rtts)
        max_v = max(rtts)
        
        print(f"📊 Result for {url}:")
        print(f"   Avg Total: {avg:.2f} ms")
        print(f"   Avg TTFB:  {avg_ttfb:.2f} ms")
        print(f"   Min Total: {min_v:.2f} ms")
        print(f"   Max Total: {max_v:.2f} ms")

if __name__ == "__main__":
    hostname = socket.gethostname()
    print(f"🚀 Network RTT Tester (No-Verify Mode) - {hostname}")
    print("==========================================================")
    
    for target in TARGETS:
        measure_rtt(target)
    
    input("\nPress Enter to exit...")
