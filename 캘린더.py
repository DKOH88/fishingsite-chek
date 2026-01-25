import tkinter as tk
from tkinter import messagebox, ttk, simpledialog, scrolledtext
import os
import subprocess
from bs4 import BeautifulSoup
import calendar
import re

class MemoDialog(simpledialog.Dialog):
    def __init__(self, parent, title, initial_text=""):
        self.initial_text = initial_text
        self.result_text = None
        super().__init__(parent, title)

    def body(self, master):
        self.text_area = scrolledtext.ScrolledText(master, width=80, height=30, font=("Arial", 10))
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.text_area.insert("1.0", self.initial_text)
        
        # [Request] Shift+Enter to insert newline
        def insert_newline(event):
            self.text_area.insert(tk.INSERT, "\n")
            return "break"
            
        self.text_area.bind("<Shift-Return>", insert_newline)
        return self.text_area

    def apply(self):
        self.result_text = self.text_area.get("1.0", tk.END).strip()

# Points to the unified capture script
CAPTURE_SCRIPT = r"C:\gemini\fishing_bot\낚시 달력 캡쳐.py"
DEFAULT_FILE_NAME = "Default"
DEFAULT_PATH = r"C:\gemini\fishing_bot\캘린더\기본"
SAVE_PATH = r"C:\gemini\fishing_bot\캘린더\저장"

class CalendarEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("낚시 캘린더 에디터 (커스텀 저장)")
        
        # Window Geometry & Centering
        w, h = 1200, 1100
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = int((ws/2) - (w/2))
        y = int((hs/2) - (h/2))
        self.geometry(f'{w}x{h}+{x}+{y}')
        
        self.data_map = {} 
        self.current_year = 2026
        self.current_month_view = 1 # Default Single View to Jan

        
        # Determine initial path
        # Try to load latest saved file first
        latest_file = None
        if os.path.exists(SAVE_PATH):
            files = [os.path.join(SAVE_PATH, f) for f in os.listdir(SAVE_PATH) if f.endswith(".html")]
            if files:
                latest_file = max(files, key=os.path.getmtime)
        
        if latest_file:
             self.current_file_path = latest_file
        else:
             self.current_file_path = os.path.join(DEFAULT_PATH, f"{DEFAULT_FILE_NAME}.html")
        
        if not os.path.exists(self.current_file_path):
             # Try fallback to Default if latest was somehow missing (unlikely) or strict Default fallback needed
             self.current_file_path = os.path.join(DEFAULT_PATH, f"{DEFAULT_FILE_NAME}.html")
             if not os.path.exists(self.current_file_path):
                  fallback = os.path.join(os.path.dirname(CAPTURE_SCRIPT), f"{DEFAULT_FILE_NAME}.html")
                  if os.path.exists(fallback):
                      self.current_file_path = fallback
        
        if os.path.exists(self.current_file_path):
            with open(self.current_file_path, "r", encoding="utf-8") as f:
                self.soup = BeautifulSoup(f, "html.parser")
        else:
             messagebox.showerror("Error", f"Default file not found: {self.current_file_path}")
             self.destroy()
             return

    def push_to_github(self, file_path):
        try:
            # Check if git is available and repo is configured
            subprocess.run(["git", "--version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Get directory of the file (should be inside repo)
            file_dir = os.path.dirname(file_path)
            
            # Simple git add, commit, push
            # We run this in the file's directory
            # 1. Add
            subprocess.run(["git", "add", os.path.basename(file_path)], cwd=file_dir, check=True)
            
            # 2. Commit (Allow empty if no changes, or catch error)
            commit_msg = f"Auto-update: {os.path.basename(file_path)}"
            subprocess.run(["git", "commit", "-m", commit_msg], cwd=file_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # 3. Push
            # This might fail if no upstream configured or no creds.
            # We'll try and see.
            result = subprocess.run(["git", "push"], cwd=file_dir, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("GitHub push successful")
            else:
                print(f"GitHub push failed: {result.stderr}")
                # Optional: messagebox.showwarning("GitHub Push Failed", f"자동 푸시 실패:\n{result.stderr}")

        except Exception as e:
            print(f"Git automation error: {e}")
            # Silently fail or log to console as requested "auto" often implies background
            
        # Detect year
        title_h1 = self.soup.find("h1")
        if title_h1:
            match = re.search(r"20\d\d", title_h1.text)
            if match: self.current_year = int(match.group(0))

        self.create_widgets()

        # Check if we need to migrate/regenerate to full 12 months
        months_divs = self.soup.find_all("div", class_="month-card")
        if len(months_divs) < 12:
            print("Detected incomplete calendar. Regenerating for 12 months...")
            self.regenerate_calendar_structure(self.current_year)
            self.load_calendar_grid()

    def create_widgets(self):
        # --- Top Action Frame ---
        self.action_frame = tk.Frame(self, pady=10, bg="#f0f0f0")
        self.action_frame.pack(fill=tk.X)
        
        # Year Selection
        tk.Label(self.action_frame, text="연도:", bg="#f0f0f0", font=("Arial", 11)).pack(side=tk.LEFT, padx=(10, 2))
        self.year_var = tk.IntVar(value=self.current_year)
        self.cmb_year = ttk.Combobox(self.action_frame, textvariable=self.year_var, values=list(range(2026, 2051)), width=5, state="readonly")
        self.cmb_year.pack(side=tk.LEFT, padx=2)
        self.cmb_year.bind("<<ComboboxSelected>>", self.on_year_change)
        
        # Month Selection Buttons (2 Rows)
        frame_months = tk.Frame(self.action_frame, bg="#f0f0f0")
        frame_months.pack(side=tk.LEFT, padx=5)
        
        frame_m_row1 = tk.Frame(frame_months, bg="#f0f0f0")
        frame_m_row1.pack(side=tk.TOP, fill=tk.X)
        frame_m_row2 = tk.Frame(frame_months, bg="#f0f0f0")
        frame_m_row2.pack(side=tk.TOP, fill=tk.X)
        
        self.btn_months = {}
        # 1~6월
        for m in range(1, 7):
            btn = tk.Button(frame_m_row1, text=f"{m}월", width=7, height=1, font=("Arial", 9, "bold"),
                            command=lambda month=m: self.switch_month_view(month))
            btn.pack(side=tk.LEFT, padx=2, pady=2)
            self.btn_months[m] = btn
            
        # 7~12월
        for m in range(7, 13):
            btn = tk.Button(frame_m_row2, text=f"{m}월", width=7, height=1, font=("Arial", 9, "bold"),
                            command=lambda month=m: self.switch_month_view(month))
            btn.pack(side=tk.LEFT, padx=2, pady=2)
            self.btn_months[m] = btn
            
        self.update_month_buttons(self.current_month_view)
        
        # File Name Input
        tk.Label(self.action_frame, text=" | 파일명:", bg="#f0f0f0", font=("Arial", 11)).pack(side=tk.LEFT, padx=(10, 2))
        self.entry_filename = tk.Entry(self.action_frame, width=15, font=("Arial", 10))
        # Initial Requirement: "2026 다이어리"
        self.entry_filename.delete(0, tk.END) 
        self.entry_filename.insert(0, "2026 다이어리")
        self.entry_filename.pack(side=tk.LEFT, padx=2)
        
        # Title Input (New)
        tk.Label(self.action_frame, text=" | 제목:", bg="#f0f0f0", font=("Arial", 11)).pack(side=tk.LEFT, padx=(10, 2))
        self.entry_title = tk.Entry(self.action_frame, width=25, font=("Arial", 10))
        
        current_title = ""
        h1 = self.soup.find("h1")
        if h1: current_title = h1.text.strip()
        self.entry_title.insert(0, current_title)
        self.entry_title.pack(side=tk.LEFT, padx=2)
        
        # Buttons
        self.btn_save = tk.Button(self.action_frame, text="💾 저장", command=self.save_html, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), padx=10)
        self.btn_save.pack(side=tk.LEFT, padx=15)
        
        # [CHANGE] Left Capture -> Initialize
        self.btn_init = tk.Button(self.action_frame, text="🔄 초기화", command=self.initialize_default, bg="#FF9800", fg="white", font=("Arial", 10, "bold"), padx=10)
        self.btn_init.pack(side=tk.LEFT, padx=5)

        self.btn_capture = tk.Button(self.action_frame, text="📷 캡처", command=self.run_capture, bg="#2196F3", fg="white", font=("Arial", 10, "bold"), padx=10)
        self.btn_capture.pack(side=tk.LEFT, padx=5)

        # --- Main Area (No Scrollbar) ---
        self.scrollable_frame = tk.Frame(self, bg="#e0e0e0")
        self.scrollable_frame.pack(side="left", fill="both", expand=True)

        self.load_calendar_grid()

    def get_target_paths(self):
        filename = self.entry_filename.get().strip()
        if not filename:
            filename = "fishing_calendar_edited" # Default save name if empty? Or utilize entered name
        
        # Determine directory
        # If user entered absolute path, use it. Else use SAVE_PATH
        # Wait, filename input is just a name typically.
        
        target_dir = SAVE_PATH
        if not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)
            
        html_path = os.path.join(target_dir, f"{filename}.html")
        png_path = os.path.join(target_dir, f"{filename}.png")
        return html_path, png_path

    def on_year_change(self, event):
        new_year = self.year_var.get()
        if messagebox.askyesno("연도 변경", f"{new_year}년으로 변경하시겠습니까?\n기존 데이터(물때, 일정 등)는 초기화됩니다."):
            self.regenerate_calendar_structure(new_year)
            self.load_calendar_grid()

    def initialize_default(self):
        if not messagebox.askyesno("초기화 확인", "기본(Default.html) 상태로 초기화하시겠습니까?\n현재 작업 중인 내용은 저장하지 않으면 사라집니다."):
            return
            
        default_path = os.path.join(DEFAULT_PATH, f"{DEFAULT_FILE_NAME}.html")
        if not os.path.exists(default_path):
             # Try fallback
             default_path = os.path.join(os.path.dirname(CAPTURE_SCRIPT), f"{DEFAULT_FILE_NAME}.html")
        
        if os.path.exists(default_path):
             with open(default_path, "r", encoding="utf-8") as f:
                self.soup = BeautifulSoup(f, "html.parser")
             
             # Reset UI State
             self.current_file_path = default_path # Wait, should we keep it as default path? Or treat as new?
             # User requirement: "Load Default.html". Usually implies resetting state.
             
             # Detect year from loaded default
             title_h1 = self.soup.find("h1")
             if title_h1:
                match = re.search(r"20\d\d", title_h1.text)
                if match: self.current_year = int(match.group(0))
             
             self.year_var.set(self.current_year)
             
             # Re-populate title entry
             self.entry_title.delete(0, tk.END)
             if title_h1: self.entry_title.insert(0, title_h1.text.strip())
             
             # Reset filename entry to default? User asked for "2026 다이어리" default logic.
             # Let's keep existing filename or reset? User didn't specify. I'll keep current filename or reset to "2026 다이어리".
             # "파일명 입력란은 '2026 다이어리' 기본입력 되어 있게 해줘" -> likely applies to init state too.
             self.entry_filename.delete(0, tk.END)
             self.entry_filename.insert(0, "2026 다이어리")

             self.load_calendar_grid()
             messagebox.showinfo("초기화 완료", "기본 설정으로 초기화되었습니다.")
        else:
             messagebox.showerror("Error", "Default.html not found.")

    def regenerate_calendar_structure(self, year):
        self.current_year = year
        
        # Update Title
        new_title = f"{year}년 낚시 캘린더"
        self.entry_title.delete(0, tk.END)
        self.entry_title.insert(0, new_title)
        
        title_h1 = self.soup.find("h1")
        if not title_h1:
            title_h1 = self.soup.new_tag("h1")
            if self.soup.body: self.soup.body.insert(0, title_h1)
        title_h1.string = new_title
            
        # Remove existing month cards to rebuild 1-12
        existing_months = self.soup.find_all("div", class_="month-card")
        for m in existing_months:
            m.decompose()
            
        # Create container if not exists (optional, but good for structure)
        # We append to body directly as per previous structure assumption
        
        target_months = list(range(0, 14))
        
        for month_idx in target_months:
            # Determine Year and Month
            if month_idx == 0:
                real_year = year - 1
                real_month = 12
            elif month_idx == 13:
                real_year = year + 1
                real_month = 1
            else:
                real_year = year
                real_month = month_idx

            month_div = self.soup.new_tag("div", attrs={"class": "month-card"})
            
            # Wrapper for Month Header
            header_div = self.soup.new_tag("div", attrs={"class": "month-header"})
            
            # H2
            h2 = self.soup.new_tag("h2")
            if month_idx == 0 or month_idx == 13:
                 h2.string = f"{real_year}년 {real_month}월"
            else:
                 h2.string = f"{real_month}월"
            header_div.append(h2)
            
            # English Name (Restored logic)
            eng_months = ["", "January", "February", "March", "April", "May", "June", 
                         "July", "August", "September", "October", "November", "December"]
            span_eng = self.soup.new_tag("span")
            span_eng.string = eng_months[real_month]
            header_div.append(span_eng)
            
            month_div.append(header_div)
            
            # Grid Header (Days)
            grid_header = self.soup.new_tag("div", attrs={"class": "calendar-grid-header"})
            day_names = ["일", "월", "화", "수", "목", "금", "토"]
            for idx, d_name in enumerate(day_names):
                classes = ["day-name"]
                if idx == 0: classes.append("sun")
                elif idx == 6: classes.append("sat")
                
                d_div = self.soup.new_tag("div", attrs={"class": " ".join(classes)})
                d_div.string = d_name
                grid_header.append(d_div)
                
            month_div.append(grid_header)
            
            # Grid Body
            grid_body = self.soup.new_tag("div", attrs={"class": "calendar-grid-body"})
            
            first_weekday, num_days = calendar.monthrange(real_year, real_month)
            # calendar.weekday: 0=Mon, 6=Sun. 
            # calendar.monthrange returns (first_weekday, num_days) where first_weekday is 0=Mon.
            # Our grid starts with Sunday (0).
            # Convert python weekday (0=Mon...6=Sun) to our grid index:
            # Grid: Sun(0), Mon(1), ..., Sat(6).
            # Python: Mon(0)...Sun(6).
            # So, Grid Index = (Python + 1) % 7.
            
            empty_count = (first_weekday + 1) % 7
            
            for _ in range(empty_count):
                grid_body.append(self.soup.new_tag("div", attrs={"class": "calendar-cell empty-cell"}))
                
            for day in range(1, num_days + 1):
                # Calculate weekday for color class
                # python: 0=Mon, 5=Sat, 6=Sun
                wday = calendar.weekday(real_year, real_month, day)
                classes = ["calendar-cell"]
                if wday == 5: classes.append("is-sat")
                if wday == 6: classes.append("is-sun")
                
                cell_div = self.soup.new_tag("div", attrs={"class": " ".join(classes)})
                
                date_num_div = self.soup.new_tag("div", attrs={"class": "date-number"})
                date_num_div.string = str(day)
                cell_div.append(date_num_div)
                
                tide_div = self.soup.new_tag("div", attrs={"class": "tide-info"})
                # [FIX] Clear data for previous/next year edge months
                if month_idx == 0 or month_idx == 13:
                    tide_div.string = ""
                else:
                    tide_div.string = "물때입력" # Default placeholder
                
                cell_div.append(tide_div)
                
                grid_body.append(cell_div)
            
            # [FIX] Pad grid to minimum 42 cells (6 rows) for consistent height
            # May 2026 requires 6 rows. To match height, all months must be 6 rows.
            current_total = empty_count + num_days
            target_total = max(42, current_total)
            remainder = target_total - current_total
            
            for _ in range(remainder):
                 grid_body.append(self.soup.new_tag("div", attrs={"class": "calendar-cell empty-cell"}))

            month_div.append(grid_body)

            
            # [FIX] Append to container, not body directly
            container = self.soup.find("div", id="calContainer")
            if not container:
                container = self.soup.find("div", class_="calendar-months-wrapper")
            
            if container:
                container.append(month_div)
            else:
                # Fallback: create container
                container = self.soup.new_tag("div", attrs={"class": "calendar-months-wrapper", "id": "calContainer"})
                self.soup.body.append(container)
                container.append(month_div)

    def switch_month_view(self, month):
        self.save_to_soup_only()
        self.current_month_view = month
        self.update_month_buttons(month)
        self.load_calendar_grid()

    def update_month_buttons(self, active_month):
        for m, btn in self.btn_months.items():
            if m == active_month:
                btn.configure(bg="#4CAF50", fg="white", relief="sunken")
            else:
                btn.configure(bg="SystemButtonFace", fg="black", relief="raised")

    def load_calendar_grid(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.data_map = {}
        
        # Reset grid config
        self.scrollable_frame.grid_columnconfigure(0, weight=1)
        self.scrollable_frame.grid_columnconfigure(1, weight=0)
        self.scrollable_frame.grid_columnconfigure(2, weight=0)
        
        selected_month = self.current_month_view
        
        months = self.soup.find_all("div", class_="month-card")
        
        for i, month in enumerate(months):
            # [FIX] Skip previous/next year duplicate months in Editor view
            # Index 0 is previous year Dec, Index 13 is next year Jan.
            if i == 0 or i == 13:
                continue

            header = month.find("h2")
            if not header: continue
            try:
                # Extract month number from "X월"
                month_num = int(header.text.strip().replace("월", ""))
            except:
                month_num = i + 1

            if selected_month and month_num != selected_month:
                continue
                
            header_div = month.find("h2")
            if not header_div: continue
            header_text = header_div.text.strip()
            
            frame_month = tk.Frame(self.scrollable_frame, bg="white", bd=2, relief="groove", padx=5, pady=5)
            frame_month.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Header with Clear Buttons
            frame_header = tk.Frame(frame_month, bg="white")
            frame_header.pack(fill=tk.X, pady=(0, 10))
            tk.Label(frame_header, text=f"{header_text}", font=("Arial", 16, "bold"), bg="white").pack(side=tk.LEFT)
            
            # Clear Buttons Frame
            f_clear = tk.Frame(frame_header, bg="white")
            f_clear.pack(side=tk.LEFT, padx=20)
            
            btn_clear_data = tk.Button(f_clear, text="모두 지우기", bg="#ffcccc", font=("Arial", 8),
                                       command=lambda m=month: self.clear_month_data(m))
            btn_clear_data.pack(side=tk.LEFT, padx=2)
            
            btn_clear_memo = tk.Button(f_clear, text="메모 초기화", bg="#ffcccc", font=("Arial", 8),
                                       command=lambda m=month: self.clear_month_memos(m))
            btn_clear_memo.pack(side=tk.LEFT, padx=2)
            
            frame_grid = tk.Frame(frame_month, bg="#ccc")
            frame_grid.pack(fill=tk.BOTH, expand=True)
            
            days = ["일", "월", "화", "수", "목", "금", "토"]
            for i, day in enumerate(days):
                color = "black"
                if i == 0: color = "red"
                if i == 6: color = "blue"
                lbl = tk.Label(frame_grid, text=day, font=("Arial", 10, "bold"), fg=color, bg="#f9f9f9", pady=5)
                lbl.grid(row=0, column=i, sticky="nsew", padx=1, pady=1)

            for i in range(7): frame_grid.grid_columnconfigure(i, weight=1)

            cells = month.find_all("div", class_="calendar-cell")
            current_row = 1
            current_col = 0
            
            for cell in cells:
                is_empty = "empty-cell" in cell.get("class", [])
                
                frame_cell = tk.Frame(frame_grid, bg="white", bd=1, relief="solid") 
                frame_cell.grid(row=current_row, column=current_col, sticky="nsew", padx=1, pady=1)
                
                if not is_empty:
                    self.create_cell_content(frame_cell, cell)
                else:
                    frame_cell.configure(bg="#f9f9f9")

                current_col += 1
                if current_col > 6:
                    current_col = 0
                    current_row += 1

            for r in range(1, current_row + 2):
                frame_grid.grid_rowconfigure(r, weight=1, minsize=110)

    def clear_month_data(self, month_elem):
        if not messagebox.askyesno("초기화 확인", "물때 정보와 예약정보를 초기화하시겠습니까?"):
            return
            
        # Iterate all tracked widgets
        for widget, data in self.data_map.items():
            # Check if this widget relates to the target month
            # We can check using soup element lineage
            target_elem = None
            if "elem" in data: target_elem = data["elem"]
            elif "cell" in data: target_elem = data["cell"]
            elif "event_div" in data: target_elem = data["event_div"] or data["cell"] # event_div might be None
            
            if target_elem:
                # Check if descendant
                # ancestors check
                is_descendant = False
                parent = target_elem
                while parent:
                    if parent == month_elem:
                        is_descendant = True
                        break
                    parent = parent.parent
                
                if is_descendant:
                    dtype = data["type"]
                    if dtype == "tide":
                        widget.delete("1.0", tk.END)
                        if "elem" in data: data["elem"].clear()
                    # event_boat_new logic removed
        
        # Save updates to soup logic is implicitly handled if we manipulate widgets AND their backing elems?
        # Actually save_html reads from widgets. So clearing widgets is enough for save.
        # But we also cleared some soup elems directly? 
        # save_to_soup_only effectively rewrites soup from widgets. 
        # So as long as widgets are cleared, save will reflect it.
        # Exception: event_div needs to be handled carefully in save loop if it was deleted.
        # My save logic checks `if event_div:`. If I decomposed it, I should update data_map? 
        # Actually save logic: `event_div = data["event_div"]`. If decomposed, it's still an object but not in tree?
        # `if not event_div:` creates new one. 
        # We should probably let save logic handle "Empty widget -> clear soup".
        # Yes, save logic: `if not new_boat ... if event_div: event_div.decompose()`. 
        # So just clearing widgets is sufficient! 
        pass

    def clear_month_memos(self, month_elem):
        if not messagebox.askyesno("메모 초기화", "메모를 초기화 하시겠습니까?"):
            return
            
        for widget, data in self.data_map.items():
            if data["type"] == "memo_data":
                cell = data["cell"]
                # lineage check
                parent = cell
                is_this_month = False
                while parent:
                    if parent == month_elem:
                        is_this_month = True
                        break
                    parent = parent.parent
                
                if is_this_month:
                    widget.memo_text = ""
                    widget.configure(bg="#eee")
                    if 'data-memo' in cell.attrs: del cell['data-memo']
                    if 'title' in cell.attrs: del cell['title']



    def create_cell_content(self, parent, cell):
        date_div = cell.find("div", class_="date-number")
        if not date_div: return
        
        date_num_text = ""
        holiday_label_text = ""
        
        for content in date_div.contents:
            if isinstance(content, str):
                t = content.strip()
                if t: date_num_text = t
            elif content.name == "span" and "holiday-label" in content.get("class", []):
                holiday_label_text = content.text.strip()
        
        f_date = tk.Frame(parent, bg="white")
        f_date.pack(fill=tk.X, padx=5, pady=2)
        
        tk.Label(f_date, text=date_num_text, font=("Arial", 12, "bold"), bg="white").pack(side=tk.LEFT)
        
        is_holiday = "is-holiday" in cell.get("class", [])
        var_holiday = tk.BooleanVar(value=is_holiday)
        
        chk_holiday = tk.Checkbutton(f_date, text="휴일", variable=var_holiday, bg="white", fg="red", selectcolor="white")
        chk_holiday.pack(side=tk.RIGHT)
        
        # Memo Button
        memo_val = cell.get('data-memo', '')
        btn_memo = tk.Button(f_date, text="메모", font=("Arial", 8), bg="#eee")
        if memo_val and memo_val.strip():
             btn_memo.configure(bg="#ffeb3b")
        btn_memo.pack(side=tk.RIGHT, padx=5)
        
        btn_memo.memo_text = memo_val 
        btn_memo.configure(command=lambda b=btn_memo: self.open_memo_dialog(b))
        
        f_holiday_name = tk.Frame(parent, bg="white")
        f_holiday_name.pack(fill=tk.X, padx=5, pady=0)
        entry_holiday_name = tk.Entry(f_holiday_name, font=("Arial", 8), width=10, fg="red", justify="center")
        entry_holiday_name.insert(0, holiday_label_text)
        entry_holiday_name.pack(fill=tk.X)
        
        self.data_map[chk_holiday] = {
            "type": "holiday_settings",
            "cell": cell,
            "date_div": date_div,
            "date_num": date_num_text,
            "var_holiday": var_holiday,
            "entry_name": entry_holiday_name,
            "soup": self.soup
        }
        
        self.data_map[btn_memo] = {
            "type": "memo_data",
            "cell": cell
        }
        
        tide_div = cell.find("div", class_="tide-info")
        if tide_div:
            text_content = ""
            for child in tide_div.children:
                if child.name == "br":
                    text_content += "\n"
                elif isinstance(child, str):
                    text_content += child.strip()
            
            txt_tide = tk.Text(parent, height=2, width=15, font=("Arial", 9), bd=1, relief="solid")
            txt_tide.insert("1.0", text_content)
            txt_tide.pack(fill=tk.X, padx=5, pady=2)
            self.data_map[txt_tide] = {"type": "tide", "elem": tide_div, "soup": self.soup}

        # Event input frame removed as per request
        # frame_event was here


    def open_memo_dialog(self, btn_widget):
        current_text = getattr(btn_widget, 'memo_text', '')
        
        # Check if active (has text) and prompt for deactivation
        if current_text and current_text.strip():
            if messagebox.askyesno("메모 관리", "이미 작성된 메모가 있습니다.\n삭제(비활성화) 하시겠습니까?\n\n[예] = 삭제 및 비활성화\n[아니오] = 내용 수정"):
                btn_widget.memo_text = ""
                btn_widget.configure(bg="#eee")
                return

        if not current_text.strip():
            current_text = "" # Default empty as requested
            
        dialog = MemoDialog(self, "메모 입력", current_text)
        if dialog.result_text is not None:
            new_text = dialog.result_text
            btn_widget.memo_text = new_text
            
            if new_text.strip():
                btn_widget.configure(bg="#ffeb3b")
            else:
                btn_widget.configure(bg="#eee")

    def ensure_javascript(self):
        # Inject JS/CSS for custom modal and cursor
        if not self.soup.find("style", id="memo-style"):
            style_tag = self.soup.new_tag("style", id="memo-style")
            style_tag.string = """
            .memo-cell { cursor: pointer; }
            /* Custom Modal Styles */
            #memoModal {
                display: none; 
                position: fixed; 
                z-index: 1000; 
                left: 0;
                top: 0;
                width: 100%; 
                height: 100%; 
                overflow: auto; 
                background-color: rgba(0,0,0,0.4); 
            }
            #memoModalContent {
                background-color: #fefefe;
                margin: 15% auto; /* 15% from the top and centered */
                padding: 20px;
                border: 1px solid #888;
                width: 50%; /* Could be more responsive */
                min-height: 400px; /* Increased height base + 200 roughly */
                border-radius: 10px;
                box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
                position: relative;
                white-space: pre-wrap; /* Preserve line breaks */
                font-family: Arial, sans-serif;
                font-size: 14px;
            }
            #memoTitle {
                text-align: center;
                font-size: 18px; /* +2 size roughly */
                font-weight: bold;
                margin-bottom: 15px;
                padding-bottom: 10px;
                border-bottom: 1px solid #eee;
            }
            .close-btn {
                color: #aaa;
                float: right;
                font-size: 28px;
                font-weight: bold;
                cursor: pointer;
                position: absolute; /* simple positioning */
                right: 15px;
                top: 5px;
            }
            .close-btn:hover,
            .close-btn:focus {
                color: black;
                text-decoration: none;
                cursor: pointer;
            }
            """
            if self.soup.head: self.soup.head.append(style_tag)

        if not self.soup.find("div", id="memoModal"):
            # Create Modal HTML Structure with Title
            modal_html = """
            <div id="memoModal">
              <div id="memoModalContent">
                <span class="close-btn">&times;</span>
                <div id="memoTitle"></div>
                <div id="memoText"></div>
              </div>
            </div>
            """
            modal_tag = BeautifulSoup(modal_html, 'html.parser')
            if self.soup.body: self.soup.body.append(modal_tag)

        if not self.soup.find("script", id="memo-script"):
            script_content = """
            document.addEventListener('DOMContentLoaded', function() {
                const modal = document.getElementById("memoModal");
                const span = document.getElementsByClassName("close-btn")[0];
                const memoTextDiv = document.getElementById("memoText");
                const memoTitleDiv = document.getElementById("memoTitle");

                span.onclick = function() {
                    modal.style.display = "none";
                }

                window.onclick = function(event) {
                    if (event.target == modal) {
                        modal.style.display = "none";
                    }
                }

                const monthMap = {"September": "9월", "October": "10월", "November": "11월"};

                const cells = document.querySelectorAll('.calendar-cell');
                cells.forEach(cell => {
                    const memo = cell.getAttribute('data-memo');
                    if (memo && memo.trim() !== "") {
                        cell.classList.add('memo-cell'); // Add cursor pointer class
                        cell.addEventListener('click', function() {
                            // Extract Date Info
                            let dayNum = "0";
                            try {
                                const dayText = this.querySelector('.date-number').innerText;
                                dayNum = parseInt(dayText); 
                            } catch(e) {}
                            
                            let monthName = "";
                            try {
                                const h2 = this.closest('.month-card').querySelector('h2');
                                monthName = h2.innerText.trim();
                            } catch(e) {}
                            
                            const kMonth = monthMap[monthName] || monthName;
                            
                            // Set Title & Content
                            memoTitleDiv.innerText = `${kMonth} ${dayNum}일 출조후기`;
                            memoTextDiv.textContent = memo;
                            
                            modal.style.display = "block";
                            
                            // Center Vertically roughly if needed, but CSS handles margin auto
                        });
                    }
                });
            });
            """
            script_tag = self.soup.new_tag("script", id="memo-script")
            script_tag.string = script_content
            self.soup.body.append(script_tag)

        # -------------------------------------------------------------------------
        # [NEW] Inject Carousel/Slider Logic for HTML
        # -------------------------------------------------------------------------
        # -------------------------------------------------------------------------
        # [NEW] Inject Carousel/Slider Logic for HTML
        # -------------------------------------------------------------------------
        # -------------------------------------------------------------------------
        # [MODIFIED] Minimal Injection - Respect Template Structure
        # -------------------------------------------------------------------------
        
        # Only inject script if completely missing (for legacy files)
        # We assume Default.html has correct CSS/Structure.
        c_script = self.soup.find("script", id="carousel-script")
        if not c_script:
            # Fallback for old files: Simple toggle script
            c_script = self.soup.new_tag("script", id="carousel-script")
            c_script.string = """
            let currentCenterMonth = 2; 
            function updateView() {
                const container = document.getElementById('calContainer'); 
                // Try to find container, if not use body? 
                // If template is old, this might fail, but user wants Default.html logic.
                if(!container) return;
                
                const months = container.getElementsByClassName('month-card');
                for(let m of months) m.style.display = 'none';
                
                const centerIdx = currentCenterMonth - 1;
                const indices = [centerIdx - 1, centerIdx, centerIdx + 1];
                
                indices.forEach(idx => {
                    if (idx >= 0 && idx < months.length) {
                        months[idx].style.display = 'flex'; 
                        // Note: Default.html uses flex for cards? Check CSS.
                        // YES, .month-card { display: flex; flex-direction: column; }
                    }
                });
            }
            function moveMonth(delta) {
                const temp = currentCenterMonth + delta;
                if (temp >= 1 && temp <= 12) {
                    currentCenterMonth = temp;
                    updateView();
                }
            }
            document.addEventListener('DOMContentLoaded', updateView);
            """
            self.soup.body.append(c_script)

    def save_to_soup_only(self):
        # Update Title
        new_title = self.entry_title.get()
        title_h1 = self.soup.find("h1")
        if title_h1:
            title_h1.string = new_title
            
        self.ensure_javascript()

        for widget, data in self.data_map.items():
            dtype = data["type"]
            
            if dtype == "text":
                data["elem"].string = widget.get().strip()
            elif dtype == "tide":
                new_text = widget.get("1.0", tk.END).strip()
                lines = new_text.split('\n')
                data["elem"].clear()
                for i, line in enumerate(lines):
                    if line:
                        data["elem"].append(line)
                        if i < len(lines) - 1:
                            data["elem"].append(self.soup.new_tag("br"))
            
            elif dtype == "memo_data":
                cell = data["cell"]
                memo_text = getattr(widget, 'memo_text', '')
                if memo_text.strip():
                    cell['data-memo'] = memo_text
                    cell['title'] = "클릭하여 메모 확인" 
                    # Class handling handled by JS injection logic implicitly 
                    # but let's be safe and let JS add class
                else:
                    if 'data-memo' in cell.attrs: del cell['data-memo']
                    if 'title' in cell.attrs: del cell['title']

            elif dtype == "holiday_settings":
                is_h = data["var_holiday"].get()
                cell = data["cell"]
                classes = cell.get("class", [])
                if is_h:
                    if "is-holiday" not in classes: classes.append("is-holiday")
                else:
                    if "is-holiday" in classes: classes.remove("is-holiday")
                cell["class"] = classes
                
                date_div = data["date_div"]
                date_num = data["date_num"]
                h_name = data["entry_name"].get().strip()
                
                date_div.clear()
                date_div.append(date_num + " ")
                if h_name:
                    span = self.soup.new_tag("span", attrs={"class": "holiday-label"})
                    span.string = h_name
                    date_div.append(span)
            # event_boat_new saving logic removed

    def save_html(self):
        try:
            self.save_to_soup_only()
            html_path, png_path = self.get_target_paths() # Get png_path here
            
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(str(self.soup))
            
            # Capture PNG
            self.run_capture_headless(html_path, png_path)
            
            # [NEW] Auto Push to GitHub
            self.push_to_github(html_path)
            
            messagebox.showinfo("저장 완료", f"파일이 저장되었습니다:\n{html_path}\n(이미지도 함께 저장됨)")
        except Exception as e:
            messagebox.showerror("에러", f"저장 실패: {e}")

    def run_capture(self):
        try:
            self.save_to_soup_only()
            html_path, png_path = self.get_target_paths()
            
            # Save HTML first to ensure we capture latest state
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(str(self.soup))
            
            # Run capture with arguments
            p = subprocess.Popen(
                ["python", CAPTURE_SCRIPT, "--input", html_path, "--output", png_path], 
                cwd=os.path.dirname(CAPTURE_SCRIPT),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = p.communicate()
            
            if p.returncode == 0:
                messagebox.showinfo("캡처 완료", f"이미지 생성 완료!\n{png_path}")
            else:
                messagebox.showerror("캡처 실패", f"오류 발생:\n{stderr.decode('utf-8', errors='ignore')}")
                
        except Exception as e:
            messagebox.showerror("에러", f"캡처 실행 불가: {e}")

if __name__ == "__main__":
    app = CalendarEditor()
    app.mainloop()
