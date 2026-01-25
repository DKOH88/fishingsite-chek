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
        self.text_area = scrolledtext.ScrolledText(master, width=40, height=15, font=("Arial", 10))
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.text_area.insert("1.0", self.initial_text)
        return self.text_area

    def apply(self):
        self.result_text = self.text_area.get("1.0", tk.END).strip()

# Points to the unified capture script
CAPTURE_SCRIPT = r"C:\gemini\fishing_bot\낚시 달력 캡쳐.py"
DEFAULT_FILE_NAME = "fishing_calendar"
DEFAULT_PATH = r"C:\gemini\fishing_bot\낚시\기본 데이터"
SAVE_PATH = r"C:\gemini\fishing_bot\낚시\저장폴더"

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
        self.current_month_view = 9 # Default view
        
        # Determine initial path
        self.current_file_path = os.path.join(DEFAULT_PATH, f"{DEFAULT_FILE_NAME}.html")
        
        if not os.path.exists(self.current_file_path):
             # Try fallback to root if not found in \낚시
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
            
        # Detect year
        title_h1 = self.soup.find("h1")
        if title_h1:
            match = re.search(r"20\d\d", title_h1.text)
            if match: self.current_year = int(match.group(0))

        self.create_widgets()

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
        
        # Month Selection Buttons
        tk.Label(self.action_frame, text=" | 월:", bg="#f0f0f0", font=("Arial", 11)).pack(side=tk.LEFT, padx=(10, 2))
        
        self.btn_months = {}
        for m in [9, 10, 11]:
            btn = tk.Button(self.action_frame, text=f"{m}월", width=4, 
                            command=lambda month=m: self.switch_month_view(month))
            btn.pack(side=tk.LEFT, padx=1)
            self.btn_months[m] = btn
            
        self.update_month_buttons(self.current_month_view)
        
        # File Name Input
        tk.Label(self.action_frame, text=" | 파일명:", bg="#f0f0f0", font=("Arial", 11)).pack(side=tk.LEFT, padx=(10, 2))
        self.entry_filename = tk.Entry(self.action_frame, width=15, font=("Arial", 10))
        # Initial Requirement: Empty field
        self.entry_filename.delete(0, tk.END) 
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
        
        self.btn_capture = tk.Button(self.action_frame, text="📷 캡처", command=self.run_capture, bg="#2196F3", fg="white", font=("Arial", 10, "bold"), padx=10)
        self.btn_capture.pack(side=tk.LEFT, padx=5)

        # --- Main Scrollable Area ---
        self.canvas = tk.Canvas(self, bg="#e0e0e0")
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#e0e0e0")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        self.load_calendar_grid()

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

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

    def regenerate_calendar_structure(self, year):
        self.current_year = year
        
        # Update Title in Entry and Soup
        new_title = f"Fishing Expedition {year}"
        self.entry_title.delete(0, tk.END)
        self.entry_title.insert(0, new_title)
        
        title_h1 = self.soup.find("h1")
        if title_h1:
            title_h1.string = new_title
            
        months_divs = self.soup.find_all("div", class_="month-card")
        target_months = [9, 10, 11]
        
        if len(months_divs) < 3: return

        for i, month_num in enumerate(target_months):
            month_div = months_divs[i]
            grid_body = month_div.find("div", class_="calendar-grid-body")
            if not grid_body: continue
            
            grid_body.clear()
            
            first_weekday, num_days = calendar.monthrange(year, month_num)
            empty_count = (first_weekday + 1) % 7
            
            for _ in range(empty_count):
                grid_body.append(self.soup.new_tag("div", attrs={"class": "calendar-cell empty-cell"}))
                
            for day in range(1, num_days + 1):
                wday = calendar.weekday(year, month_num, day)
                classes = ["calendar-cell"]
                if wday == 5: classes.append("is-sat")
                if wday == 6: classes.append("is-sun")
                
                cell_div = self.soup.new_tag("div", attrs={"class": " ".join(classes)})
                
                date_num_div = self.soup.new_tag("div", attrs={"class": "date-number"})
                date_num_div.string = str(day)
                cell_div.append(date_num_div)
                
                tide_div = self.soup.new_tag("div", attrs={"class": "tide-info"})
                tide_div.string = "물때입력"
                cell_div.append(tide_div)
                
                grid_body.append(cell_div)

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
        
        months = self.soup.find_all("div", class_="month-card")
        
        for i, month in enumerate(months):
            month_num = 9 + i 
            if self.current_month_view and month_num != self.current_month_view:
                continue
                
            header_div = month.find("h2")
            if not header_div: continue
            header_text = header_div.text.strip()
            
            frame_month = tk.Frame(self.scrollable_frame, bg="white", bd=2, relief="groove", padx=10, pady=10)
            frame_month.pack(fill=tk.X, padx=20, pady=20)
            
            # Header with Clear Buttons
            frame_header = tk.Frame(frame_month, bg="white")
            frame_header.pack(fill=tk.X, pady=(0, 10))
            tk.Label(frame_header, text=f"{header_text} ({self.current_year})", font=("Arial", 16, "bold"), bg="white").pack(side=tk.LEFT)
            
            # Clear Buttons Frame
            f_clear = tk.Frame(frame_header, bg="white")
            f_clear.pack(side=tk.LEFT, padx=20)
            
            btn_clear_data = tk.Button(f_clear, text="모두 지우기", bg="#ffcccc", font=("Arial", 8),
                                       command=lambda m=month: self.clear_month_data(m))
            btn_clear_data.pack(side=tk.LEFT, padx=2)
            
            btn_clear_memo = tk.Button(f_clear, text="메모 초기화", bg="#ffcccc", font=("Arial", 8),
                                       command=lambda m=month: self.clear_month_memos(m))
            btn_clear_memo.pack(side=tk.LEFT, padx=2)

            port_label_div = month.find("div", class_="port-standard-label")
            if port_label_div:
                frame_port = tk.Frame(frame_header, bg="white")
                frame_port.pack(side=tk.RIGHT)
                tk.Label(frame_port, text="기준:", bg="white").pack(side=tk.LEFT)
                entry_port = tk.Entry(frame_port, width=15)
                entry_port.insert(0, port_label_div.text.strip())
                entry_port.pack(side=tk.LEFT)
                self.data_map[entry_port] = {"type": "text", "elem": port_label_div}
            
            frame_grid = tk.Frame(frame_month, bg="#ccc")
            frame_grid.pack(fill=tk.X)
            
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
                
                frame_cell = tk.Frame(frame_grid, bg="white", width=160, height=210) 
                frame_cell.grid_propagate(False)
                frame_cell.grid(row=current_row, column=current_col, sticky="nsew", padx=1, pady=1)
                
                if not is_empty:
                    self.create_cell_content(frame_cell, cell)
                else:
                    frame_cell.configure(bg="#f9f9f9")

                current_col += 1
                if current_col > 6:
                    current_col = 0
                    current_row += 1

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
                    elif dtype == "event_boat_new":
                        widget.delete(0, tk.END)
                        if "entry_port" in data: data["entry_port"].delete(0, tk.END)
                        if "event_div" in data and data["event_div"]: 
                            data["event_div"].decompose()
                            data["event_div"] = None # Clear ref
        
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

        event_div = cell.find("div", class_="boat-event")
        frame_event = tk.Frame(parent, bg="white")
        frame_event.pack(fill=tk.X, padx=5, pady=2, side=tk.BOTTOM)
        
        boat_val = ""
        port_val = ""
        if event_div:
            port_span = event_div.find("span", class_="port-loc")
            if port_span:
                port_val = port_span.text.strip()
                for c in event_div.contents:
                    if isinstance(c, str): boat_val += c.strip()
            else:
                boat_val = event_div.text.strip()

        lbl_b = tk.Label(frame_event, text="선박/일정:", font=("Arial", 9), bg="white")
        lbl_b.pack(anchor="w")
        entry_boat = tk.Entry(frame_event, font=("Arial", 9), bd=1, relief="solid")
        entry_boat.insert(0, boat_val)
        entry_boat.pack(fill=tk.X)
        
        lbl_p = tk.Label(frame_event, text="항구:", font=("Arial", 9), bg="white")
        lbl_p.pack(anchor="w")
        entry_port = tk.Entry(frame_event, font=("Arial", 9), bd=1, relief="solid")
        entry_port.insert(0, port_val)
        entry_port.pack(fill=tk.X)
        
        self.data_map[entry_boat] = {"type": "event_boat_new", "cell": cell, "event_div": event_div, "entry_port": entry_port}

    def open_memo_dialog(self, btn_widget):
        current_text = getattr(btn_widget, 'memo_text', '')
        
        # Check if active (has text) and prompt for deactivation
        if current_text and current_text.strip():
            if messagebox.askyesno("메모 관리", "이미 작성된 메모가 있습니다.\n삭제(비활성화) 하시겠습니까?\n\n[예] = 삭제 및 비활성화\n[아니오] = 내용 수정"):
                btn_widget.memo_text = ""
                btn_widget.configure(bg="#eee")
                return

        default_template = """■날씨:
■자리:
■조과
-쭈꾸미: 
-갑오징어: 
-기타: 
■출항시간: 
■입항시간: 
■선박정보: 
■기타"""

        if not current_text.strip():
            current_text = default_template
            
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
            if self.soup.body:
                self.soup.body.append(script_tag)

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
            elif dtype == "event_boat_new":
                new_boat = widget.get().strip()
                entry_port = data["entry_port"]
                new_port = entry_port.get().strip()
                cell = data["cell"]
                event_div = data["event_div"]
                
                if not new_boat and not new_port:
                    if event_div: event_div.decompose()
                    continue
                if not event_div:
                    event_div = self.soup.new_tag("div", attrs={"class": "boat-event"})
                    cell.append(event_div)
                event_div.clear()
                event_div.append(new_boat + " ")
                if new_port:
                    p = self.soup.new_tag("span", attrs={"class": "port-loc"})
                    p.string = new_port
                    event_div.append(p)

    def save_html(self):
        try:
            self.save_to_soup_only()
            html_path, _ = self.get_target_paths()
            
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(str(self.soup))
            
            messagebox.showinfo("완료", f"파일이 저장되었습니다.\n{html_path}")
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
