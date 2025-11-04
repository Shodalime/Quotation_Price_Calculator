# import section
import sys,os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import pandas as pd, os, requests, io, json

import sqlite3
from libsql_client import create_client_sync

DB_URL = "https://daplpricing-shodalime.aws-ap-south-1.turso.io"
AUTH_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3NjA2MDA4NzYsImlkIjoiYjhjZWRjOWYtM2IwNC00NTMwLTk5OTUtODBiMTY1MzZkYTYxIiwicmlkIjoiNWY4YzNkYzMtYmE0OS00MjMyLWExMDAtNjVmMTRkNGE5MmNhIn0.mGS_d0TLVCy24p7E2DUGbK2sehtFaAvk54NCcV6tjBwdRBScppOU3fYtTezAisy5jlsTjX7Z5vooCHhlnEfiDw"

def get_db_connection():
    """
    Returns a tuple (conn,cur) - tries to connect to Turso first, and
    falls back to local SQLite if not available.
    """
    try:
        remote_client = create_client_sync(url=DB_URL, auth_token=AUTH_TOKEN)
        class TursoCursor:
            def __init__(self,client): 
                self.client = client
            def execute(self,query,params=()):
                self._last = self.client.execute(query,params or [])
                return self._last
            def fetchall(self):
                return [tuple(row) for row in self._last.rows] if hasattr(self,"_last") else []
            def fetchone(self):
                return tuple(self._last.rows[0]) if hasattr(self,"_last") and self._last.rows else None
            
        class TursoConnection:
            def __init__(self,client): self.client = client
            def cursor(self): return TursoCursor(self.client)
            def commit(self): pass
            def close(self):
                try:
                    self.client.close()
                except Exception:
                    pass

        conn = TursoConnection(remote_client)
        cur = conn.cursor()
        print("✅ Connected to Turso Cloud Database")
        return conn,cur
    except Exception as e:
        print("⚠️ Using local SQLite database due to:",e)
        conn = sqlite3.connect("pricing.db")
        cur = conn.cursor()
        return conn,cur

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS  # PyInstaller unpacked
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class PricingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DAPL PRICING CALCULATOR")
        self.root.geometry("600x550")

        self.entries, self.outputs = {}, {}
        self.fx_rate_label_var = tk.StringVar()
        self.material_size_var = tk.StringVar()
        self.bg_color = "#FFFACD"
        self.db_conn, self.db_cur = get_db_connection()
        self.root.configure(bg=self.bg_color)

        self.currency_used = None
        self.material_size_export = None

        self.create_widgets()

    def create_widgets(self):
        labels = ["Customer Width (MM)", "Customer Length (MM)", "Grit", "Grade", "Quantity"]
        for i, label in enumerate(labels):
            tk.Label(self.root, text=label, bg=self.bg_color, font=("Arial", 12)).grid(row=i+1, column=0, pady=5, sticky='e')
            e = tk.Entry(self.root, font=("Arial", 12))
            e.grid(row=i+1, column=1, padx=10, pady=5)
            self.entries[label] = e

        # Proper alignment: Material Size appears just below Quantity (row 6)
        tk.Label(self.root, textvariable=self.material_size_var, bg=self.bg_color,
         font=("Arial", 11, "italic"), fg="black").grid(row=6, column=1, sticky="w")

        output_labels = ["No. of Belts", "Offer Price", "Discount (%)", "Discounted Price"]
        for idx, name in enumerate(output_labels):
            tk.Label(self.root, text=name, bg=self.bg_color, font=("Arial", 12)).grid(row=9 + idx, column=0, pady=5, sticky='e')
            var = tk.StringVar()
            tk.Entry(self.root, textvariable=var, font=("Arial", 12), state='readonly').grid(row=9 + idx, column=1, padx=5)
            self.outputs[name] = var

        tk.Label(self.root, textvariable=self.fx_rate_label_var, bg=self.bg_color,
                 font=("Arial", 11, "italic"), fg="black").grid(row=13, column=0, columnspan=3, pady=5)

        button_frame = tk.Frame(self.root, bg=self.bg_color)
        button_frame.grid(row=14, column=0, columnspan=4, pady=20)

        tk.Button(button_frame, text="Calculate", command=self.calculate_pricing,
                  bg="green", fg="white", font=("Arial", 12)).pack(side="left", padx=10)

        tk.Button(button_frame, text="Save", command=self.save_to_excel,
                  bg="blue", fg="white", font=("Arial", 12)).pack(side="left", padx=10)

        tk.Button(button_frame, text="Reset", command=self.reset_fields,
                  bg="red", fg="white", font=("Arial", 12)).pack(side="left", padx=10)

        tk.Button(button_frame, text="Edit Materials", command=self.change_file,
                  bg="orange", fg="black", font=("Arial", 11)).pack(side="left", padx=10)
        
        all_inputs = list(self.entries.values())

        buttons = []
        for child in self.root.winfo_children():
            if isinstance(child,tk.Frame):
                for b in child.winfo_children():
                    if isinstance(b,tk.Button):
                        buttons.append(b)

        focus_widgets = all_inputs + buttons
        self.add_focus_bindings(focus_widgets,enter_action=self.calculate_pricing)

        all_inputs[0].focus_set()
        
    def add_focus_bindings(self,widgets,enter_action=None):
        """
        Adds Tab, Shift+Tab, and Enter key navigation to a list of widgets.
        Optionally binds Enter to a specific action.
        """
        def focus_next(event):
            event.widget.tk_focusNext().focus_set()
            return "break"
        def focus_prev(event):
            event.widget.tk_focusPrev().focus_set()
            return "break"
        
        for w in widgets:
            w.bind("<Tab>",focus_next)
            w.bind("<Shift-Tab>",focus_prev)
            if enter_action:
                w.bind("<Return>", lambda event:enter_action())

    def add_escape_binding(self,window):
        """Bind Esc key to close the given window."""
        window.bind("<Escape>",lambda event:window.destroy())

    def reset_fields(self):
        for entry in self.entries.values():
            entry.delete(0, tk.END)
        for var in self.outputs.values():
            var.set("")
        self.fx_rate_label_var.set("")
        self.material_size_var.set("")
        self.currency_used = None
        self.material_size_export = None

    def get_fx_rate(self, currency):
        try:
            url_map = {
                "USD": "https://www.exchange-rates.org/converter/usd-inr",
                "CNY": "https://www.exchange-rates.org/converter/cny-inr",
                "EUR": "https://www.exchange-rates.org/converter/eur-inr"
            }
            url = url_map.get(currency.upper())
            if not url:
                raise ValueError(f"Unsupported currency: {currency}")
            html = requests.get(url).text
            tables = pd.read_html(io.StringIO(html))
            rate_text = str(tables[0].iloc[0, 1])
            rate_cleaned = ''.join(c for c in rate_text if c.isdigit() or c == '.')
            return float(rate_cleaned)
        except Exception:
            raise ValueError(f"Failed to fetch conversion rate: {currency}")

    def compute_offer_price(self,w_num, l_num, price, fx, qty, mult, cw, cl):
        belts_w = w_num / cw
        belts_l = l_num / cl
        belt_count = int(belts_w) * int(belts_l)
        if belt_count <= 0:
            messagebox.showerror("Error", "No belts – check dimensions.")
            return 0, 0, 0, 0
        offer = price * (w_num / 1000) * (l_num / 1000) * (fx + (0.03 * fx)) * mult / belt_count

        if qty >= belt_count:
            discount_pct = 20
        elif qty >= 0.5 * belt_count:
            discount_pct = 15
        else:
            discount_pct = 10

        discounted_price = offer * (1 - discount_pct / 100)
        return belt_count, offer, discount_pct, discounted_price        


    def calculate_pricing(self):
        try:
            cw = float(self.entries["Customer Width (MM)"].get())
            cl = float(self.entries["Customer Length (MM)"].get())
            grit_input = self.entries["Grit"].get().strip().upper()
            grade = self.entries["Grade"].get().strip().upper()
            qty = int(self.entries["Quantity"].get())

            if not os.path.exists("pricing.db") and "turso" not in str(type(self.db_conn)).lower():
                messagebox.showerror("Missing Database", "No Turso or SQLite database found.")
                return

            if (grit_input != "NW" and (int(grit_input) < 0 or qty < 0)):
                messagebox.showerror("Input Error", "Grit and Quantity must be positive integers.")
                return

            mult = 2.5
            if cw < 21 or cl < 400:
                mult = 5.0
            elif cw < 21 or 400 < cl < 700:
                mult = 4.0

            conn, cur = self.db_conn, self.db_cur

            if grit_input == "NW":
                cur.execute("""
                    SELECT grade, grit, size, price, currency FROM [China Machinery]
                    WHERE UPPER(TRIM(grade)) = ?
                    UNION ALL
                    SELECT grade, grit, size, price, currency FROM [Jiangsu]
                    WHERE UPPER(TRIM(grade)) = ?
                    UNION ALL
                    SELECT grade, grit, size, price, currency FROM [Kingdeer]
                    WHERE UPPER(TRIM(grade)) = ?
                    UNION ALL
                    SELECT grade, grit, size, price, currency FROM [Bibielle]
                    WHERE UPPER(TRIM(grade)) = ?
                    UNION ALL
                    SELECT grade, grit, size, price, currency FROM [FE10]
                    WHERE UPPER(TRIM(grade)) = ?
                """, (grade, grade, grade, grade, grade))
                rows = cur.fetchall()
                grit_input = "NW"
            else:
                grit_input = int(grit_input)
                cur.execute("""
                    SELECT grade, grit, size, price, currency FROM [China Machinery]
                    WHERE UPPER(TRIM(grade)) = ?
                    UNION ALL
                    SELECT grade, grit, size, price, currency FROM [Jiangsu]
                    WHERE UPPER(TRIM(grade)) = ?
                    UNION ALL
                    SELECT grade, grit, size, price, currency FROM [Kingdeer]
                    WHERE UPPER(TRIM(grade)) = ?
                    UNION ALL
                    SELECT grade, grit, size, price, currency FROM [Bibielle]
                    WHERE UPPER(TRIM(grade)) = ?
                    UNION ALL
                    SELECT grade, grit, size, price, currency FROM [FE10]
                    WHERE UPPER(TRIM(grade)) = ?
                """, (grade, grade, grade, grade, grade))
                rows = cur.fetchall()
            if not rows:
                messagebox.showerror("No Match", f"No matching material for Grade {grade}.")
                return

            matched_rows = []
            for grade_val, grit_val, size, price, currency in rows:
                grit_str = str(grit_val).strip()
                if grit_input == "NW":
                    matched_rows.append((grade_val, grit_str, size, price, currency))
                elif '-' in grit_str:
                    try:
                        g1, g2 = map(int, grit_str.split('-'))
                        if g1 <= grit_input <= g2:
                            matched_rows.append((grade_val, grit_str, size, price, currency))
                    except:
                        continue
                else:
                    try:
                        if int(grit_str) == grit_input:
                            matched_rows.append((grade_val, grit_str, size, price, currency))
                    except:
                        continue

            if not matched_rows:
                messagebox.showerror("No Match", f"No matching material for Grade {grade} and Grit {grit_input}.")
                return

            # If only one match, check if size is ambiguous and ask for length
            if len(matched_rows) == 1:
                grade_val, grit_val, size, price, currency = matched_rows[0]
                size_std = str(size).upper().replace('*', 'X').strip()
                parts = size_std.split('X')

                w_num = self.convert_to_mm(parts[0])

                if len(parts) < 2 or not parts[1].strip():
                    # Ask user for roll length
                    length_input = simpledialog.askfloat("Missing Length", "Input the length of the roll for the database in (MM)")
                    if not length_input:
                        messagebox.showwarning("Length Required", "Length input is required to proceed.")
                        return
                    l_num = length_input
                else:
                    l_num = self.convert_to_mm(parts[1])

                fx = self.get_fx_rate(currency)

                belt_count, offer, discount_pct, discounted_price = self.compute_offer_price(w_num, l_num, price, fx, qty, mult, cw, cl)

                size_str = f"{float(w_num / 1000)} m x {float(l_num / 1000)} m"
                self.material_size_var.set(f"Material Size: {size_str}")
                self.material_size_export = size_str
                self.fx_rate_label_var.set(f"Currency: {currency} | FX: {fx}")
                self.currency_used = currency

                self.outputs["No. of Belts"].set(belt_count)
                self.outputs["Offer Price"].set(round(offer, 2))
                self.outputs["Discount (%)"].set(f"{discount_pct}%")
                self.outputs["Discounted Price"].set(round(discounted_price, 2))
                return

            # If multiple matches, find one with closest matching width ≥ cw
            found = False
            for grade_val, grit_val, size, price, currency in matched_rows:
                size_std = str(size).upper().replace('*', 'X').strip()
                parts = size_std.split('X')
                if len(parts) < 2:
                    continue

                w_num = self.convert_to_mm(parts[0])
                l_num = self.convert_to_mm(parts[1])

                if w_num < cw:
                    continue

                fx = self.get_fx_rate(currency)

                belt_count, offer, discount_pct, discounted_price = self.compute_offer_price(w_num, l_num, price, fx, qty, mult, cw, cl)

                size_str = f"{float(w_num / 1000)} m x {float(l_num / 1000)} m"
                self.material_size_var.set(f"Material Size: {size_str}")
                self.material_size_export = size_str
                self.fx_rate_label_var.set(f"Currency: {currency} | FX: {fx}")
                self.currency_used = currency

                self.outputs["No. of Belts"].set(belt_count)
                self.outputs["Offer Price"].set(round(offer, 2))
                self.outputs["Discount (%)"].set(f"{discount_pct}%")
                self.outputs["Discounted Price"].set(round(discounted_price, 2))
                found = True
                break

            if not found:
                messagebox.showerror("Width Too Large", f"No available width ≥ {cw} mm for Grade {grade} and Grit {grit_input}.")

        except Exception as e:
            self.fx_rate_label_var.set("")
            messagebox.showerror("Error", str(e))

    def convert_to_mm(self, s):
        s = s.strip().upper()
        if 'MM' in s:
            return float(s.replace('MM', '').strip())
        elif 'M' in s:
            return float(s.replace('M', '').strip()) * 1000
        else:
            val = float(s)
            return val * 1000 if val < 10 else val

    def save_to_excel(self):
        try:
            if not all(self.outputs[key].get() for key in self.outputs):
                messagebox.showerror("Warning", "Please calculate the pricing before saving.")
                return

            input_data = {k: self.entries[k].get() for k in self.entries}
            output_data = {k: self.outputs[k].get() for k in self.outputs}

            currency = self.currency_used or "N/A"
            fx_line = self.fx_rate_label_var.get()
            fx_rate = ""
            if fx_line and "FX:" in fx_line:
                fx_rate = fx_line.split("FX:")[1].strip()

            material_size = self.material_size_export or ""

            ordered_keys = list(input_data.keys()) + list(output_data.keys()) + ["Material Size", "Currency Used", "FX Rate Used"]
            row_values = list(input_data.values()) + list(output_data.values()) + [material_size, currency, fx_rate]

            df_new = pd.DataFrame([dict(zip(ordered_keys, row_values))])

            # Check if user already selected a path before
            if not hasattr(self, "saved_excel_path") or not self.saved_excel_path:
                # First-time save
                self.saved_excel_path = filedialog.asksaveasfilename(
                    defaultextension=".xlsx",
                    filetypes=[("Excel files", "*.xlsx")],
                    title="Save As",
                    initialfile="quotation_output.xlsx"
                )
                if not self.saved_excel_path:
                    return  # Cancelled
            else:
                # Ask if user wants to overwrite or choose new
                choice = messagebox.askyesno("Save Option",
                                            f"Do you want to save to the same file?\n\n{self.saved_excel_path}")
                if not choice:
                    new_path = filedialog.asksaveasfilename(
                        defaultextension=".xlsx",
                        filetypes=[("Excel files", "*.xlsx")],
                        title="Save As",
                        initialfile="quotation_output.xlsx"
                    )
                    if not new_path:
                        return  # Cancelled
                    self.saved_excel_path = new_path

            # Write to file
            if os.path.exists(self.saved_excel_path):
                try:
                    df_existing = pd.read_excel(self.saved_excel_path)
                    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                except Exception:
                    df_combined = df_new
            else:
                df_combined = df_new

            df_combined.to_excel(self.saved_excel_path, index=False)
            messagebox.showinfo("Saved", f"Data saved to:\n{self.saved_excel_path}")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def change_file(self):
        username = simpledialog.askstring("Login Required", "Enter Username:")
        if username != "admin":
            messagebox.showerror("Access Denied", "Incorrect Username.")
            return
        password = simpledialog.askstring("Login Required", "Enter Password:", show='*')
        if password != "1234":
            messagebox.showerror("Access Denied", "Incorrect Password.")
            return

        editor = tk.Toplevel(self.root)
        self.apply_icon(editor)
        editor.title("Edit Materials")
        editor.geometry("1250x650")
        editor.configure(bg="#FFFACD")

        self.add_escape_binding(editor)

        # --- LEFT PANEL: SEARCH SECTION ---
        search_frame = tk.Frame(editor, bg="#FFFACD", bd=2, relief="groove")
        search_frame.pack(side="left", fill="y", padx=10, pady=10)
        search_frame.pack_propagate(False)
        search_frame.config(width=230)

        tk.Label(search_frame, text="Search Materials", font=("Arial", 12, "bold"), bg="#FFFACD").pack(pady=5)
        tk.Label(search_frame, text="Grade:", bg="#FFFACD").pack()
        grade_entry = tk.Entry(search_frame)
        grade_entry.pack(pady=5)
        tk.Label(search_frame, text="Grit (e.g., 60 or 60-120):", bg="#FFFACD").pack()
        grit_entry = tk.Entry(search_frame)
        grit_entry.pack(pady=5)

        grade_entry.bind("<Return>",lambda event: perform_search())
        grit_entry.bind("<Return>", lambda event: perform_search())

        tk.Button(search_frame, text="Search", bg="blue", fg="white", font=("Arial", 11),command=lambda: perform_search()).pack(pady=10)
        grade_entry.focus_set()

        # --- RIGHT PANEL: RESULTS TABLE ---
        right_frame = tk.Frame(editor, bg="#FFFACD")
        right_frame.pack(side="right", expand=True, fill="both", padx=10, pady=10)

        columns = ["Table", "Grade", "Grit", "Size", "Price", "Currency"]

        tree_container = tk.Frame(right_frame,bg="#FFFACD")
        tree_container.pack(fill="both",expand=True)

        tree = ttk.Treeview(tree_container, columns=columns, show="headings")
        for col in columns:
            tree.heading(col, text=col, command=lambda c=col: sort_treeview(tree, c, False))
            tree.column(col, width=120, anchor="center")
        tree.grid(row=0,column=0,sticky="nsew")

        filter_frame = tk.Frame(tree_container,bg="#FFFACD")
        filter_frame.grid(row=1,column=0,sticky="ew",pady=(0,3))
        
        tree_container.grid_rowconfigure(0,weight=1)
        tree_container.grid_columnconfigure(0,weight=1)

        filter_vars = {col:tk.StringVar() for col in columns}

        # Auto-filter as you type
        def on_filter_change(event):
            task_id = getattr(editor,"_filter_after_id",None)
            if task_id:
                try:
                    editor.after_cancel(task_id)
                except Exception:
                    pass
            editor._filter_after_id = editor.after(300,apply_filter)

        filter_entries = {}
        for i, col in enumerate(columns):
            entry = tk.Entry(filter_frame,textvariable=filter_vars[col],font=("Arial",10))
            entry.grid(row=0,column=i,padx=1,pady=(2,3),sticky="ew")
            entry.bind("<KeyRelease>", on_filter_change)
            filter_frame.grid_columnconfigure(i,weight=1)
            filter_entries[col]=entry

        tk.Frame(tree_container,height=1,bg="gray").grid(row=2,column=0,sticky="ew",pady=(2,0))
        
        search_results = []

        def sync_filter_widths(event=None):
            total_cols = len(columns)
            for i, col in enumerate(columns):
                width = tree.column(col,option="width")
                filter_entries[col].config(width=max(int(width/8),8))

        tree.bind("<Configure>",sync_filter_widths)

        def apply_filter():
            nonlocal search_results
            """Filter the current search results by values entered in filter boxes."""
            filters = {col:filter_vars[col].get().strip().upper() for col in columns}

            for i in tree.get_children():
                tree.delete(i)

            for row in search_results:
                rowid, table, grade, grit, size, price, currency = row
                row_dict = {
                    "Table": table,
                    "Grade": grade,
                    "Grit": str(grit).upper(),
                    "Size": str(size).upper(),
                    "Price": str(price).upper(),
                    "Currency": str(currency).upper()
                }

                match = all(
                    not filters[col] or filters[col] in row_dict[col]
                    for col in columns
                )

                if match:
                    tree.insert("","end",values=(table,grade,grit,size,price,currency), iid=f"{table}:{rowid}")

            #print(row_dict)

        def sort_treeview(tree, col, reverse):
            items = [(tree.set(k, col), k) for k in tree.get_children('')]
            try:
                items.sort(key=lambda t: float(t[0]), reverse=reverse)
            except ValueError:
                items.sort(reverse=reverse)
            for index, (val, k) in enumerate(items):
                tree.move(k, '', index)
            tree.heading(col, command=lambda: sort_treeview(tree, col, not reverse))

        # --- BUTTONS BELOW SEARCH ---
        button_frame = tk.Frame(search_frame, bg="#FFFACD")
        button_frame.pack(pady=20)

        tk.Button(button_frame, text="Edit Selected", bg="orange", fg="black", font=("Arial", 11),
                command=lambda: edit_selected()).pack(fill="x", pady=5)
        tk.Button(button_frame, text="Delete Selected", bg="red", fg="white", font=("Arial", 11),
                command=lambda: delete_selected()).pack(fill="x", pady=5)
        tk.Button(button_frame, text="Add New", bg="green", fg="white", font=("Arial", 11),
                command=lambda: add_new()).pack(fill="x", pady=5)
        
        focus_widgets = [grade_entry,grit_entry]

        for widget in search_frame.winfo_children():
            if isinstance(widget,tk.Button):
                focus_widgets.append(widget)
        for widget in button_frame.winfo_children():
            if isinstance(widget,tk.Button):
                focus_widgets.append(widget)

        self.add_focus_bindings(focus_widgets,enter_action=lambda: perform_search())

        grade_entry.focus_set()

        # --- SEARCH LOGIC ---
        def perform_search():
            nonlocal search_results
            grit_val = grit_entry.get().strip().upper()
            grade_val = grade_entry.get().strip().upper()
            if not grit_val and not grade_val:
                messagebox.showerror("Error", "Please enter at least a Grade or Grit to search.")
                return

            conn, cur = self.db_conn, self.db_cur

            tables = ["China Machinery", "Jiangsu", "Kingdeer", "FE10", "Bibielle"]
            query_results = []

            # --- Grit parsing logic ---
            grit_min, grit_max = None, None
            is_nonnumeric_grit = False

            if grit_val:
                if grit_val in ["NW", "NON-WOVEN"]:
                    is_nonnumeric_grit = True
                elif '-' in grit_val:
                    parts = grit_val.split('-')
                    if len(parts) == 2 and all(p.strip().isdigit() for p in parts):
                        grit_min, grit_max = map(int, parts)
                    else:
                        messagebox.showerror("Error", "Invalid grit range format.")
                        return
                else:
                    try:
                        grit_min = grit_max = int(grit_val)
                    except:
                        # Non-numeric grit entered (like A/O)
                        is_nonnumeric_grit = True

            for table in tables:
                cur.execute(f"SELECT rowid, '{table}', grade, grit, size, price, currency FROM [{table}]")
                for row in cur.fetchall():
                    rowid, tbl, grade_db, grit_db, size, price, currency = row
                    grit_str = str(grit_db).strip().upper()

                    # --- Grade filtering ---
                    if grade_val and grade_val not in grade_db.upper():
                        continue

                    # --- Grit filtering ---
                    if not grit_val:
                        query_results.append(row)
                        continue

                    if is_nonnumeric_grit:
                        # Match NW, NON-WOVEN, or exact non-numeric grit
                        if grit_val == grit_str:
                            query_results.append(row)
                        continue

                    try:
                        if '-' in grit_str:
                            g1, g2 = map(int, grit_str.split('-'))
                            if grit_min and grit_max and g1 <= grit_max and g2 >= grit_min:
                                query_results.append(row)
                        else:
                            g = int(grit_str)
                            if grit_min <= g <= grit_max:
                                query_results.append(row)
                    except:
                        # skip non-numeric grits when searching numeric grit
                        continue

            # --- Populate results ---
            for i in tree.get_children():
                tree.delete(i)

            for row in query_results:
                db_rowid = row[0]
                table, grade, grit, size, price, currency = row[1:]
                tree.insert("", "end", values=(table, grade, grit, size, price, currency), iid=f"{table}:{db_rowid}")

            #print("Rows fetched:", len(query_results))
            #print(query_results[:5])

            search_results = query_results.copy()

        # --- EDIT FUNCTION ---
        def edit_selected():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Select Entry", "Please select a row to edit.")
                return
            item_id = selected[0]
            table, rowid = item_id.split(':',1)
            values = tree.item(item_id, "values")

            edit_win = tk.Toplevel(editor)
            edit_win.title("Edit Record")
            edit_win.geometry("400x400")
            edit_win.configure(bg="#FFFACD")

            self.add_escape_binding(edit_win)

            labels = ["Grade", "Grit", "Size", "Price", "Currency"]
            var_list = [tk.StringVar(value=v) for v in values[1:]]
            entries = {}

            for i, lbl in enumerate(labels):
                tk.Label(edit_win, text=lbl, bg="#FFFACD").pack()
                e = tk.Entry(edit_win, textvariable=var_list[i])
                e.pack(pady=5)
                entries[lbl] = e

            def save_changes():
                try:
                    conn, cur = self.db_conn, self.db_cur

                    cur.execute(f"""
                        UPDATE [{table}] SET grade=?, grit=?, size=?, price=?, currency=?
                        WHERE rowid=?
                    """, (var_list[0].get().strip().upper(),
                        var_list[1].get().strip(),
                        var_list[2].get().strip(),
                        float(var_list[3].get()),
                        var_list[4].get().strip().upper(),
                        rowid))
                    conn.commit()
                    messagebox.showinfo("Updated", "Record updated successfully.")
                    perform_search()  # Refresh
                    edit_win.destroy()
                except Exception as e:
                    messagebox.showerror("Error", str(e))

            self.add_focus_bindings(entries.values(),enter_action=save_changes)

            tk.Button(edit_win, text="Save Changes", bg="green", fg="white",
                    command=save_changes).pack(pady=10)

        # --- DELETE FUNCTION ---
        def delete_selected():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Select Entry", "Please select a row to delete.")
                return
            if not messagebox.askyesno("Confirm", "Are you sure you want to delete the selected record?"):
                return

            conn, cur = self.db_conn, self.db_cur

            for item_id in selected:
                table, db_rowid = item_id.split(':',1)
                cur.execute(f"DELETE FROM [{table}] WHERE rowid=?", (db_rowid,))
                tree.delete(item_id)
            conn.commit()
            messagebox.showinfo("Deleted", "Selected record(s) deleted successfully.")

        # --- ADD FUNCTION ---
        def add_new():
            add_win = tk.Toplevel(editor)
            add_win.title("Add New Record")
            add_win.geometry("400x450")
            add_win.configure(bg="#FFFACD")

            self.add_escape_binding(add_win)

            tk.Label(add_win, text="Add New Entry", font=("Arial", 12, "bold"), bg="#FFFACD").pack(pady=5)

            tables = ["China Machinery", "Jiangsu", "Kingdeer", "FE10", "Bibielle"]
            table_var = tk.StringVar(value=tables[0])
            grade_var = tk.StringVar()
            grit_var = tk.StringVar()
            size_var = tk.StringVar()
            price_var = tk.StringVar()
            currency_var = tk.StringVar()

            fields = [
                ("Table", ttk.Combobox(add_win, textvariable=table_var, values=tables)),
                ("Grade", tk.Entry(add_win, textvariable=grade_var)),
                ("Grit", tk.Entry(add_win, textvariable=grit_var)),
                ("Size", tk.Entry(add_win, textvariable=size_var)),
                ("Price", tk.Entry(add_win, textvariable=price_var)),
                ("Currency", tk.Entry(add_win, textvariable=currency_var))
            ]

            input_widgets = [widget for _,widget in fields]

            def save_new():
                try:
                    conn, cur = self.db_conn, self.db_cur

                    cur.execute(f"""
                        INSERT INTO [{table_var.get()}] (grade, grit, size, price, currency)
                        VALUES (?, ?, ?, ?, ?)
                    """, (grade_var.get().strip().upper(),
                        grit_var.get().strip(),
                        size_var.get().strip(),
                        float(price_var.get()),
                        currency_var.get().strip().upper()))
                    conn.commit()
                    messagebox.showinfo("Added", "New record added successfully.")
                    perform_search()
                    add_win.destroy()
                except Exception as e:
                    messagebox.showerror("Error", str(e))

            self.add_focus_bindings(input_widgets,enter_action=save_new)

            for lbl, widget in fields:
                tk.Label(add_win, text=lbl, bg="#FFFACD").pack()
                widget.pack(pady=3)

            tk.Button(add_win, text="Add Entry", bg="orange", fg="black", font=("Arial", 11),
                    command=save_new).pack(pady=10)

    def apply_icon(self, window):
        icon_path = resource_path("Changed_picture.ico")
        try:
            window.iconbitmap(icon_path)
        except Exception:
            print(f"Icon not found: {icon_path}")


if __name__ == "__main__":
    root = tk.Tk()
    icon_path = resource_path("Changed_picture.ico")
    try:
        root.iconbitmap(icon_path)
    except Exception as e:
        print(f"Icon file not found:{icon_path}")
    app = PricingApp(root)

    def on_close():
        if hasattr(app,"db_conn") and app.db_conn:
            try:
                app.db_conn.close()
            except Exception:
                pass
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()