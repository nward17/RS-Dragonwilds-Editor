import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import json
import uuid
import os
import sys
import webbrowser
from collections import OrderedDict
from PIL import Image, ImageTk
import time

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 2
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, background="#ffffe0", relief="solid", borderwidth=1, font=("Georgia", 9))
        label.pack()

    def hide_tip(self, event=None):
        tw = self.tipwindow
        if tw:
            tw.destroy()
            self.tipwindow = None

def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

ASSETS_DIR = resource_path("assets")
UI_DIR = os.path.join(ASSETS_DIR, "UI")
DATA_DIR = resource_path("data")

SLOT_SIZE = 64
ITEM_ICON_SIZE = 32
SELECTED_ICON_SIZE = int(ITEM_ICON_SIZE * 1.2)

ICON_MAP, POWER_MAP, ITEM_NAME_MAP = {}, {}, {}
POWER_BADGES = {}
ICON_CACHE = {}
PLACEHOLDER_ICON = None
PLACEHOLDER_ICON_SELECTED = None

selected_slot_index = None
selected_item_name = None
current_file_path = None
current_save_data = None

def generate_guid():
    return uuid.uuid4().hex[:22]

def load_item_list():
    global ICON_MAP, POWER_MAP, ITEM_NAME_MAP
    items, display_map, lookup, categorized_items = [], {}, {}, {}
    path = os.path.join(DATA_DIR, "ItemID.txt")
    if not os.path.exists(path):
        messagebox.showerror("Missing File", f"ItemID.txt not found in {DATA_DIR}.")
        return items, display_map, lookup, categorized_items

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        messagebox.showerror("Parse Error", f"Cannot read ItemID.txt: {e}")
        return items, display_map, lookup, categorized_items

    for entry in data:
        pid = entry.get("PersistenceID")
        icon = entry.get("IconFile")
        name = entry.get("SourceString", "").strip()
        if pid and icon:
            ICON_MAP[pid] = icon
        if pid and name:
            ITEM_NAME_MAP[pid] = name

    for entry in data:
        name = entry.get("SourceString", "").strip()
        if not name:
            continue
        category = entry.get("Category", "Miscellaneous")
        original_category = category
        category = category.lower()
        if category not in categorized_items:
            categorized_items[category] = []
        categorized_items[category].append((name, original_category))
        items.append(name)
        display_map[name] = name
        lookup[name] = entry
        pid = entry.get("PersistenceID")
        pwr = entry.get("PowerLevel")
        if pid and pwr is not None:
            POWER_MAP[pid] = pwr

    return items, display_map, lookup, categorized_items

def get_icon_image(item_id: str, size: int = SLOT_SIZE) -> ImageTk.PhotoImage | None:
    if not item_id:
        return None

    cache_key = (item_id, size)
    if cache_key in ICON_CACHE:
        return ICON_CACHE[cache_key]

    icon_name = ICON_MAP.get(item_id)
    if not icon_name:
        return None

    try:
        p = os.path.join(UI_DIR, icon_name)
        if not os.path.exists(p):
            return None
        img = Image.open(p).convert("RGBA").resize((size, size), Image.LANCZOS)
        tk_img = ImageTk.PhotoImage(img)
        ICON_CACHE[cache_key] = tk_img
        return tk_img
    except Exception as e:
        print(f"Failed to load icon {icon_name}: {e}")
        return None

class SaveEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("RuneScape Dragonwilds Save Editor")
        self.root.geometry("1100x700")
        self.root.configure(bg="#1c1b18")
        self.root.minsize(900, 600)
        
        self.selected_slot_index = None
        self.selected_loadout_index = None
        self.selected_item_name = None
        self.current_file_path = None
        self.current_save_data = None
        self.slot_labels = {}
        self.loadout_labels = []
        self.inventory_icons = {}
        self.current_tab = "main"
        
        self.item_list, self.display_lookup, self.item_lookup, self.categorized_items = load_item_list()
        
        self._init_placeholder_icons()
        self._init_power_badges()
        self._setup_styles()
        self._create_layout()
        
    def _init_placeholder_icons(self):
        global PLACEHOLDER_ICON, PLACEHOLDER_ICON_SELECTED
        placeholder_path = os.path.join(UI_DIR, "ICON PLACEHOLDER.png")
        try:
            placeholder_img = Image.open(placeholder_path).convert("RGBA").resize(
                (ITEM_ICON_SIZE, ITEM_ICON_SIZE), Image.LANCZOS
            )
            PLACEHOLDER_ICON = ImageTk.PhotoImage(placeholder_img)
            placeholder_img_selected = placeholder_img.resize((SELECTED_ICON_SIZE, SELECTED_ICON_SIZE), Image.LANCZOS)
            PLACEHOLDER_ICON_SELECTED = ImageTk.PhotoImage(placeholder_img_selected)
        except:
            placeholder_img = Image.new("RGBA", (ITEM_ICON_SIZE, ITEM_ICON_SIZE), (255, 255, 255, 0))
            PLACEHOLDER_ICON = ImageTk.PhotoImage(placeholder_img)
            PLACEHOLDER_ICON_SELECTED = ImageTk.PhotoImage(placeholder_img.resize((SELECTED_ICON_SIZE, SELECTED_ICON_SIZE), Image.LANCZOS))
    
    def _init_power_badges(self):
        global POWER_BADGES
        if not POWER_BADGES:
            for lvl in range(1, 6):
                try:
                    POWER_BADGES[lvl] = ImageTk.PhotoImage(
                        Image.open(os.path.join(ASSETS_DIR, f"PowerLevel{lvl}.png")).resize((20, 20))
                    )
                except:
                    pass
    
    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TLabel", background="#1c1b18", foreground="gold", font=("Georgia", 10, "bold"))
        style.configure("TEntry", fieldbackground="#302f2c", foreground="white")
        style.configure("TButton", background="#2c2b27", foreground="gold", font=("Georgia", 10, "bold"))
        style.configure("TFrame", background="#1c1b18")
    
    def _create_layout(self):
        main_container = tk.Frame(self.root, bg="#1c1b18")
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        top_bar = tk.Frame(main_container, bg="#1c1b18")
        top_bar.pack(fill="x", pady=(0, 10))
        
        ttk.Label(top_bar, text="Save File:").pack(side="left")
        self.entry_file = ttk.Entry(top_bar, width=60)
        self.entry_file.pack(side="left", padx=5)
        ttk.Button(top_bar, text="Browse", command=self._load_json).pack(side="left", padx=5)
        
        content_frame = tk.Frame(main_container, bg="#1c1b18")
        content_frame.pack(fill="both", expand=True)
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=0)
        content_frame.rowconfigure(0, weight=1)
        
        left_panel = tk.Frame(content_frame, bg="#1c1b18")
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left_panel.rowconfigure(1, weight=1)
        left_panel.columnconfigure(0, weight=1)
        
        search_frame = tk.Frame(left_panel, bg="#1c1b18")
        search_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        
        ttk.Label(search_frame, text="Search:").pack(side="left")
        self.search_entry = ttk.Entry(search_frame, width=25)
        self.search_entry.pack(side="left", padx=5)
        clear_btn = tk.Label(search_frame, text="✖", fg="red", bg="#1c1b18", font=("Arial", 10), cursor="hand2")
        clear_btn.pack(side="left")
        clear_btn.bind("<Button-1>", lambda e: self._clear_search())
        
        ttk.Label(search_frame, text="Tier:").pack(side="left", padx=(15, 0))
        self.tier_filter = ttk.Combobox(search_frame, width=8, state="readonly", 
                                        values=["All", "1", "2", "3", "4", "5"])
        self.tier_filter.set("All")
        self.tier_filter.pack(side="left", padx=5)
        self.tier_filter.bind("<<ComboboxSelected>>", lambda e: self._filter_items())
        
        self.item_box_frame = tk.Frame(left_panel, bg="#2c2b27", bd=2, relief="sunken")
        self.item_box_frame.grid(row=1, column=0, sticky="nsew")
        self._create_item_box()
        
        controls_frame = tk.Frame(left_panel, bg="#1c1b18")
        controls_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        
        ttk.Label(controls_frame, text="Quantity:").grid(row=0, column=0, sticky="e", padx=(0, 5))
        self.entry_count = ttk.Entry(controls_frame, width=8)
        self.entry_count.insert(0, "1")
        self.entry_count.grid(row=0, column=1, sticky="w")
        self._bind_scroll_increment(self.entry_count)
        
        self.label_maxstack = ttk.Label(controls_frame, text="", foreground="gray")
        self.label_maxstack.grid(row=0, column=2, sticky="w", padx=(10, 0))
        
        btn_frame = tk.Frame(controls_frame, bg="#1c1b18")
        btn_frame.grid(row=0, column=3, sticky="e", padx=(20, 0))
        
        ttk.Button(btn_frame, text="Add Item", command=self._add_item).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Clear Slot", command=self._clear_slot).pack(side="left", padx=5)
        
        right_panel = tk.Frame(content_frame, bg="#2c2b27", bd=2, relief="ridge", width=380)
        right_panel.grid(row=0, column=1, sticky="ns")
        right_panel.grid_propagate(False)
        
        self._create_inventory_panel(right_panel)
    
    def _create_inventory_panel(self, parent):
        parent.configure(width=380, height=580)
        
        inv_label = tk.Label(parent, text="Inventory", bg="#2c2b27", fg="gold", font=("Georgia", 12, "bold"))
        inv_label.pack(pady=(10, 5))
        
        action_bar = tk.Frame(parent, bg="#333")
        action_bar.pack(pady=5)
        
        for i in range(8):
            frame = tk.Frame(action_bar, bg="#444", width=SLOT_SIZE+8, height=SLOT_SIZE+8,
                           highlightthickness=2, highlightbackground="#222")
            frame.grid(row=0, column=i, padx=2, pady=2)
            frame.grid_propagate(False)
            
            lbl = tk.Label(frame, text="", bg="#444")
            lbl.place(relx=0.5, rely=0.5, anchor="center", width=SLOT_SIZE, height=SLOT_SIZE)
            lbl.slot_index = i
            lbl.bind("<Button-1>", lambda e, idx=i: self._select_slot(idx))
            lbl.bind("<Button-3>", lambda e, idx=i: self._show_slot_context_menu(e, idx))
            self.slot_labels[i] = lbl
        
        tab_frame = tk.Frame(parent, bg="#1c1b18")
        tab_frame.pack(pady=5)
        
        try:
            self.tab_icons = {
                "main": ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Icon_Items_Normal.png")).resize((80, 40))),
                "rune": ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Icon_Runes_Normal.png")).resize((80, 40))),
                "quest": ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Icon_Quests_Normal.png")).resize((80, 40)))
            }
            self.tab_icons_selected = {
                "main": ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Icon_Items_Highlight.png")).resize((80, 40))),
                "rune": ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Icon_Runes_Highlight.png")).resize((80, 40))),
                "quest": ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Icon_Quests_Highlight.png")).resize((80, 40)))
            }
        except Exception as e:
            print(f"Tab icon loading failed: {e}")
            self.tab_icons = {}
            self.tab_icons_selected = {}
        
        self.tab_buttons = {}
        tab_tooltips = {
            "main": "Main Inventory (Slots 8-31)\nGeneral items, weapons, armor, food, etc.",
            "rune": "Rune Inventory (Slots 32-55)\nRunes only",
            "quest": "Quest Inventory (Slots 56-79)\nKey items and quest items only"
        }
        for t in ("main", "rune", "quest"):
            img = self.tab_icons_selected.get(t) if t == self.current_tab else self.tab_icons.get(t)
            btn = tk.Label(tab_frame, image=img, bg="#1c1b18", cursor="hand2")
            btn.pack(side="left", padx=5)
            btn.bind("<Button-1>", lambda e, tab=t: self._switch_tab(tab))
            ToolTip(btn, tab_tooltips[t])
            self.tab_buttons[t] = btn
        
        self.grid_container = tk.Frame(parent, bg="#222")
        self.grid_container.pack(pady=5)
        
        self.tab_frames = {}
        tab_start = {"main": 8, "rune": 32, "quest": 56}
        
        for name, start in tab_start.items():
            f = tk.Frame(self.grid_container, bg="#222")
            f.grid(row=0, column=0, sticky="nsew")
            self.tab_frames[name] = f
            
            for r in range(3):
                for c in range(8):
                    idx = start + r * 8 + c
                    frame = tk.Frame(f, bg="#444", width=SLOT_SIZE+8, height=SLOT_SIZE+8,
                                   highlightthickness=2, highlightbackground="#222")
                    frame.grid(row=r, column=c, padx=2, pady=2)
                    frame.grid_propagate(False)
                    
                    lbl = tk.Label(frame, text="", bg="#444")
                    lbl.place(relx=0.5, rely=0.5, anchor="center", width=SLOT_SIZE, height=SLOT_SIZE)
                    lbl.slot_index = idx
                    lbl.bind("<Button-1>", lambda e, i=idx: self._select_slot(i))
                    lbl.bind("<Button-3>", lambda e, i=idx: self._show_slot_context_menu(e, i))
                    self.slot_labels[idx] = lbl
            f.lower()
        
        self.tab_frames[self.current_tab].lift()
        
        loadout_label = tk.Label(parent, text="Equipment", bg="#2c2b27", fg="gold", font=("Georgia", 10, "bold"))
        loadout_label.pack(pady=(15, 5))
        
        loadout_frame = tk.Frame(parent, bg="#222")
        loadout_frame.pack(pady=5)
        
        try:
            loadout_icons = [
                ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Inventory_EquipmentHelmet.png")).resize((40, 40))),
                ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Inventory_EquipmentBody.png")).resize((40, 40))),
                ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Inventory_EquipmentLegs.png")).resize((40, 40))),
                ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Inventory_EquipmentCape.png")).resize((40, 40))),
                ImageTk.PhotoImage(Image.open(os.path.join(ASSETS_DIR, "T_Inventory_EquipmentTrinket.png")).resize((30, 30)))
            ]
            self._loadout_placeholder_icons = loadout_icons
        except:
            loadout_icons = [None] * 5
            self._loadout_placeholder_icons = []
        
        for i, icon in enumerate(loadout_icons):
            frame = tk.Frame(loadout_frame, bg="#444", width=58, height=58,
                           highlightthickness=2, highlightbackground="#222")
            frame.grid(row=0, column=i, padx=5, pady=5)
            frame.grid_propagate(False)
            
            lbl = tk.Label(frame, image=icon, bg="#444")
            lbl.place(relx=0.5, rely=0.5, anchor="center", width=50, height=50)
            lbl.loadout_index = i
            lbl.bind("<Button-1>", lambda e, idx=i: self._select_loadout_slot(idx))
            lbl.bind("<Button-3>", lambda e, idx=i: self._show_loadout_context_menu(e, idx))
            self.loadout_labels.append(lbl)
            if icon:
                lbl.image = icon
    
    def _create_item_box(self):
        canvas = tk.Canvas(self.item_box_frame, bg="#1c1b18", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.item_box_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg="#1c1b18")
        
        self.scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        def on_mousewheel(event):
            canvas.yview_scroll(-1 * (event.delta // 120), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        self.canvas = canvas
        self.category_frames = {}
        self.category_visible = {}
        self.item_labels = {}
        self.selected_item_label = None
        
        self._populate_item_box()
        
        self.search_entry.bind("<KeyRelease>", lambda e: self._filter_items())
    
    def _populate_item_box(self, filter_text="", tier_filter="All"):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        self.category_frames = {}
        self.item_labels = {}
        
        row = 0
        items_per_row = 10
        
        for category in sorted(self.categorized_items.keys()):
            # Skip empty/unnamed category
            if not category or category.strip() == '':
                continue
            
            items = self.categorized_items[category]
            
            # Filter by search text
            if filter_text:
                items = [(name, orig) for name, orig in items if filter_text.lower() in name.lower()]
            
            # Filter by tier/power level
            if tier_filter != "All":
                tier_value = int(tier_filter)
                filtered_items = []
                for name, orig in items:
                    item_data = self.item_lookup.get(name, {})
                    item_tier = item_data.get("PowerLevel")
                    if item_tier == tier_value:
                        filtered_items.append((name, orig))
                items = filtered_items
            
            if not items:
                continue
            
            if category not in self.category_visible:
                self.category_visible[category] = True
            
            display_name = items[0][1] if items else category.capitalize()
            
            cat_header = tk.Frame(self.scrollable_frame, bg="#1c1b18")
            cat_header.grid(row=row, column=0, sticky="w", pady=(5, 2))
            
            arrow = "▼" if self.category_visible[category] else "►"
            toggle_btn = tk.Label(
                cat_header, text=f"{arrow} {display_name}", bg="#1c1b18", fg="gold",
                font=("Georgia", 10, "bold"), cursor="hand2"
            )
            toggle_btn.pack(side="left")
            toggle_btn.bind("<Button-1>", lambda e, c=category: self._toggle_category(c))
            
            row += 1
            
            items_frame = tk.Frame(self.scrollable_frame, bg="#1c1b18")
            items_frame.grid(row=row, column=0, sticky="w", pady=2)
            self.category_frames[category] = {"header": cat_header, "frame": items_frame, "toggle": toggle_btn, "display_name": display_name}
            
            if self.category_visible[category]:
                for idx, (item_name, orig_cat) in enumerate(items):
                    item_id = self.item_lookup.get(item_name, {}).get("PersistenceID")
                    icon = get_icon_image(item_id, ITEM_ICON_SIZE) if item_id else PLACEHOLDER_ICON
                    
                    item_frame = tk.Frame(items_frame, bg="#1c1b18", width=ITEM_ICON_SIZE+4, height=ITEM_ICON_SIZE+4)
                    item_frame.grid(row=idx // items_per_row, column=idx % items_per_row, padx=2, pady=2)
                    item_frame.grid_propagate(False)
                    
                    lbl = tk.Label(item_frame, image=icon, bg="#1c1b18", cursor="hand2")
                    lbl.place(relx=0.5, rely=0.5, anchor="center")
                    lbl.image = icon
                    lbl.item_name = item_name
                    
                    lbl.bind("<Button-1>", lambda e, name=item_name, l=lbl: self._select_item(name, l))
                    lbl.bind("<Double-Button-1>", lambda e, name=item_name: webbrowser.open(f"https://dragonwilds.runescape.wiki/w/{name.replace(' ', '_')}"))
                    lbl.bind("<Button-3>", lambda e, name=item_name, l=lbl: self._select_and_show_context_menu(e, name, l))
                    ToolTip(lbl, item_name)
                    
                    self.item_labels[item_name] = lbl
            
            row += 1
    
    def _toggle_category(self, category):
        self.category_visible[category] = not self.category_visible[category]
        self._populate_item_box(self.search_entry.get(), self.tier_filter.get())
    
    def _filter_items(self):
        self._populate_item_box(self.search_entry.get(), self.tier_filter.get())
    
    def _clear_search(self):
        self.search_entry.delete(0, tk.END)
        self.tier_filter.set("All")
        self._populate_item_box()
    
    def _select_item(self, item_name, label):
        if self.selected_item_label and self.selected_item_label.winfo_exists():
            try:
                self.selected_item_label.configure(highlightthickness=0, bd=0)
            except:
                pass
        
        label.configure(highlightthickness=2, highlightbackground="gold", bd=0)
        self.selected_item_label = label
        self.selected_item_name = item_name
        
        item_data = self.item_lookup.get(item_name, {})
        max_stack = item_data.get("MaxStackSize", 1)
        self.label_maxstack.config(text=f"(Max: {max_stack})")
        
        current_count = self.entry_count.get()
        try:
            if int(current_count) > max_stack:
                self.entry_count.delete(0, tk.END)
                self.entry_count.insert(0, str(max_stack))
        except:
            pass
    
    def _select_slot(self, slot_index):
        # Deselect all inventory slots - change border color only, not thickness
        for idx, lbl in self.slot_labels.items():
            frame = lbl.master
            if frame:
                frame.configure(highlightbackground="#222", highlightthickness=2)
        
        # Deselect all loadout slots
        for lbl in self.loadout_labels:
            frame = lbl.master
            if frame:
                frame.configure(highlightbackground="#222", highlightthickness=2)
        
        self.selected_loadout_index = None
        
        lbl = self.slot_labels.get(slot_index)
        if lbl:
            frame = lbl.master
            if frame:
                frame.configure(highlightbackground="#00ff00", highlightthickness=3)
            self.selected_slot_index = slot_index
    
    def _select_loadout_slot(self, loadout_index):
        # Deselect all inventory slots
        for idx, lbl in self.slot_labels.items():
            frame = lbl.master
            if frame:
                frame.configure(highlightbackground="#222", highlightthickness=2)
        
        # Deselect all loadout slots
        for lbl in self.loadout_labels:
            frame = lbl.master
            if frame:
                frame.configure(highlightbackground="#222", highlightthickness=2)
        
        self.selected_slot_index = None
        
        if loadout_index < len(self.loadout_labels):
            lbl = self.loadout_labels[loadout_index]
            frame = lbl.master
            if frame:
                frame.configure(highlightbackground="#00ff00", highlightthickness=3)
            self.selected_loadout_index = loadout_index
    
    def _switch_tab(self, tab_name):
        if tab_name == self.current_tab:
            return
        
        for t, btn in self.tab_buttons.items():
            img = self.tab_icons_selected.get(t) if t == tab_name else self.tab_icons.get(t)
            if img:
                btn.configure(image=img)
        
        self.tab_frames[self.current_tab].lower()
        self.tab_frames[tab_name].lift()
        self.current_tab = tab_name
    
    def _select_and_show_context_menu(self, event, item_name, label):
        self._select_item(item_name, label)
        self._show_item_context_menu(event, item_name)
    
    def _show_item_context_menu(self, event, item_name):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Open in Wiki", command=lambda: webbrowser.open(f"https://dragonwilds.runescape.wiki/w/{item_name.replace(' ', '_')}"))
        menu.tk_popup(event.x_root, event.y_root)
    
    def _show_slot_context_menu(self, event, slot_index):
        menu = tk.Menu(self.root, tearoff=0)
        
        if self.current_save_data:
            inv = self.current_save_data.get("Inventory", {})
            slot_data = inv.get(str(slot_index), {})
            item_id = slot_data.get("ItemData")
            item_name = ITEM_NAME_MAP.get(item_id)
            
            if item_name:
                menu.add_command(label=f"Open '{item_name}' in Wiki", 
                    command=lambda: webbrowser.open(f"https://dragonwilds.runescape.wiki/w/{item_name.replace(' ', '_')}"))
                menu.add_separator()
        
        menu.add_command(label="Clear Slot", command=lambda: self._clear_specific_slot(slot_index))
        menu.tk_popup(event.x_root, event.y_root)
    
    def _show_loadout_context_menu(self, event, loadout_index):
        menu = tk.Menu(self.root, tearoff=0)
        
        if self.current_save_data:
            loadout = self.current_save_data.get("Loadout", {})
            slot_data = loadout.get(str(loadout_index), {})
            item_id = slot_data.get("ItemData")
            item_name = ITEM_NAME_MAP.get(item_id)
            
            if item_name:
                menu.add_command(label=f"Open '{item_name}' in Wiki",
                    command=lambda: webbrowser.open(f"https://dragonwilds.runescape.wiki/w/{item_name.replace(' ', '_')}"))
                menu.add_separator()
            
            menu.add_command(label="Clear Slot", command=lambda: self._clear_loadout_slot(loadout_index))
        
        menu.tk_popup(event.x_root, event.y_root)
    
    def _get_valid_slot_range(self, item_category):
        """Returns valid slot ranges based on item category"""
        category_lower = item_category.lower() if item_category else ""
        
        # Runes go to rune slots (32-55)
        if "rune" in category_lower:
            return (32, 55), "Rune"
        
        # Quest items go to quest slots (56-79)
        # (Add quest categories here if needed)
        
        # Everything else goes to main inventory (0-31) or action bar (0-7)
        return (0, 31), "Main/Action Bar"
    
    def _get_valid_loadout_slots(self, item_category):
        """Returns valid loadout slot indices based on item category"""
        category_lower = item_category.lower() if item_category else ""
        
        # Loadout slots: 0=Helmet, 1=Body, 2=Legs, 3=Cape, 4=Trinket
        slot_map = {
            "helmet": [0],
            "body": [1],
            "legs": [2],
            "cape": [3],
            "trinket": [4],
            "amulet": [4],
        }
        
        for key, slots in slot_map.items():
            if key in category_lower:
                return slots
        
        return None  # Item cannot go in loadout
    
    def _add_item(self):
        if not self.current_file_path:
            messagebox.showerror("Error", "Please load a save file first.")
            return
        
        if self.selected_slot_index is None and self.selected_loadout_index is None:
            messagebox.showerror("Error", "Please select an inventory or equipment slot.")
            return
        
        if not self.selected_item_name:
            messagebox.showerror("Error", "Please select an item to add.")
            return
        
        item_data = self.item_lookup.get(self.selected_item_name)
        if not item_data:
            messagebox.showerror("Error", "Invalid item selection.")
            return
        
        item_category = item_data.get("Category", "")
        
        # Handle loadout/equipment slot
        if self.selected_loadout_index is not None:
            valid_slots = self._get_valid_loadout_slots(item_category)
            if valid_slots is None or self.selected_loadout_index not in valid_slots:
                slot_names = ["Helmet", "Body", "Legs", "Cape", "Trinket"]
                selected_name = slot_names[self.selected_loadout_index] if self.selected_loadout_index < len(slot_names) else "Unknown"
                messagebox.showerror("Error", f"'{self.selected_item_name}' cannot be equipped in the {selected_name} slot.")
                return
            
            loadout = self.current_save_data.setdefault("Loadout", {})
            item_entry = {
                "GUID": generate_guid(),
                "ItemData": item_data["PersistenceID"]
            }
            if item_data.get("BaseDurability"):
                item_entry["Durability"] = item_data["BaseDurability"]
            
            loadout[str(self.selected_loadout_index)] = item_entry
            self._save_file()
            self._refresh_inventory()
            return
        
        # Handle inventory slot
        slot_index = self.selected_slot_index
        
        # Validate slot range based on item category
        valid_range, range_name = self._get_valid_slot_range(item_category)
        
        # Check if rune is being placed in non-rune slot
        if "rune" in item_category.lower() and not (32 <= slot_index <= 55):
            messagebox.showerror("Error", f"Runes can only be placed in Rune inventory slots (32-55).")
            return
        
        # Check if non-rune is being placed in rune slot
        if "rune" not in item_category.lower() and (32 <= slot_index <= 55):
            messagebox.showerror("Error", f"Only runes can be placed in Rune inventory slots.")
            return
        
        # Check if key/quest item is being placed in non-quest slot
        if "keyitem" in item_category.lower() and not (56 <= slot_index <= 79):
            messagebox.showerror("Error", f"Key/Quest items can only be placed in Quest inventory slots (56-79).")
            return
        
        # Check if non-quest item is being placed in quest slot
        if "keyitem" not in item_category.lower() and (56 <= slot_index <= 79):
            messagebox.showerror("Error", f"Only Key/Quest items can be placed in Quest inventory slots.")
            return
        
        try:
            count = int(self.entry_count.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid quantity.")
            return
        
        max_stack = item_data.get("MaxStackSize", 1)
        if count > max_stack:
            count = max_stack
            self.entry_count.delete(0, tk.END)
            self.entry_count.insert(0, str(count))
        
        if count < 1:
            count = 1
        
        inventory = self.current_save_data.setdefault("Inventory", {})
        
        item_entry = {
            "GUID": generate_guid(),
            "ItemData": item_data["PersistenceID"]
        }
        if count > 1:
            item_entry["Count"] = count
        if item_data.get("BaseDurability"):
            item_entry["Durability"] = item_data["BaseDurability"]
        if item_data.get("VitalShield") is not None:
            item_entry["VitalShield"] = item_data["VitalShield"]
        
        inventory[str(self.selected_slot_index)] = item_entry
        
        max_idx = max([int(k) for k in inventory.keys() if k.isdigit()], default=0)
        inventory["MaxSlotIndex"] = max(inventory.get("MaxSlotIndex", 0), max_idx)
        
        self._save_file()
        self._refresh_inventory()
    
    def _clear_slot(self):
        if self.selected_slot_index is None and self.selected_loadout_index is None:
            messagebox.showerror("Error", "Please select an inventory or equipment slot to clear.")
            return
        
        if self.selected_loadout_index is not None:
            self._clear_loadout_slot(self.selected_loadout_index)
        else:
            self._clear_specific_slot(self.selected_slot_index)
    
    def _clear_specific_slot(self, slot_index):
        if not self.current_file_path or not self.current_save_data:
            messagebox.showerror("Error", "Please load a save file first.")
            return
        
        inventory = self.current_save_data.get("Inventory", {})
        slot_key = str(slot_index)
        
        if slot_key in inventory:
            del inventory[slot_key]
            self._save_file()
            self._refresh_inventory()
    
    def _clear_loadout_slot(self, loadout_index):
        if not self.current_file_path or not self.current_save_data:
            messagebox.showerror("Error", "Please load a save file first.")
            return
        
        loadout = self.current_save_data.get("Loadout", {})
        slot_key = str(loadout_index)
        
        if slot_key in loadout:
            del loadout[slot_key]
            self._save_file()
            self._refresh_inventory()
    
    def _save_file(self):
        if not self.current_file_path or not self.current_save_data:
            return
        
        backup_path = self.current_file_path.replace(".json", "_backup.json")
        if not os.path.exists(backup_path):
            try:
                with open(self.current_file_path, 'r', encoding='utf-8') as f:
                    original = json.load(f)
                with open(backup_path, 'w', encoding='utf-8') as f:
                    json.dump(original, f, indent=4)
            except:
                pass
        
        try:
            with open(self.current_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.current_save_data, f, indent=4)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")
    
    def _load_json(self):
        default = os.path.expandvars(r"%LOCALAPPDATA%\\RSDragonwilds\\Saved\\SaveCharacters")
        initdir = default if os.path.exists(default) else os.getcwd()
        fp = filedialog.askopenfilename(initialdir=initdir, title="Select Save File", filetypes=[("JSON", "*.json")])
        
        if not fp:
            return
        
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                self.current_save_data = json.load(f)
            self.current_file_path = fp
            self.entry_file.delete(0, tk.END)
            self.entry_file.insert(0, fp)
            self._refresh_inventory()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load save file: {e}")
    
    def _refresh_inventory(self):
        if not self.current_save_data:
            return
        
        for idx, lbl in self.slot_labels.items():
            lbl.configure(image="", text="", bg="#444")
            lbl.image = None
            self._set_count_badge(lbl, None)
            self._set_power_badge(lbl, None)
        
        for i, lbl in enumerate(self.loadout_labels):
            if i < len(self._loadout_placeholder_icons):
                lbl.configure(image=self._loadout_placeholder_icons[i])
                lbl.image = self._loadout_placeholder_icons[i]
            self._set_count_badge(lbl, None)
            self._set_power_badge(lbl, None)
        
        inventory = self.current_save_data.get("Inventory", {})
        
        for slot_str, entry in inventory.items():
            if not slot_str.isdigit():
                continue
            
            slot_idx = int(slot_str)
            item_id = entry.get("ItemData")
            
            if slot_idx not in self.slot_labels:
                continue
            
            lbl = self.slot_labels[slot_idx]
            icon = get_icon_image(item_id, SLOT_SIZE - 8)
            
            if icon:
                lbl.configure(image=icon, text="")
                lbl.image = icon
                self._set_count_badge(lbl, entry.get("Count"))
                self._set_power_badge(lbl, item_id)
                
                item_name = ITEM_NAME_MAP.get(item_id, "Unknown")
                ToolTip(lbl, item_name)
        
        loadout = self.current_save_data.get("Loadout", {})
        for slot_str, entry in loadout.items():
            if not slot_str.isdigit():
                continue
            
            slot_idx = int(slot_str)
            if slot_idx >= len(self.loadout_labels):
                continue
            
            item_id = entry.get("ItemData")
            if not item_id and "PlayerInventoryItemIndex" in entry:
                ref = str(entry["PlayerInventoryItemIndex"])
                item_id = inventory.get(ref, {}).get("ItemData")
            
            lbl = self.loadout_labels[slot_idx]
            icon = get_icon_image(item_id, 46)
            
            if icon:
                lbl.configure(image=icon)
                lbl.image = icon
                self._set_count_badge(lbl, entry.get("Count"))
                self._set_power_badge(lbl, item_id)
                
                item_name = ITEM_NAME_MAP.get(item_id, "Unknown")
                ToolTip(lbl, item_name)
        
        if self.selected_slot_index is not None:
            self._select_slot(self.selected_slot_index)
    
    def _set_count_badge(self, parent_lbl, count):
        badge = getattr(parent_lbl, "_count_badge", None)
        if badge is None:
            badge = tk.Label(parent_lbl, text="", fg="white", bg="#444", font=("Consolas", 9, "bold"))
            badge.place(relx=1.0, rely=1.0, anchor="se")
            parent_lbl._count_badge = badge
        
        if count is None or count <= 1:
            badge.place_forget()
        else:
            badge.config(text=str(count))
            badge.place(relx=1.0, rely=1.0, anchor="se")
    
    def _set_power_badge(self, parent_lbl, item_id):
        badge = getattr(parent_lbl, "_power_badge", None)
        if badge is None:
            badge = tk.Label(parent_lbl, image="", bd=0, bg=parent_lbl["bg"])
            badge.place(relx=0, rely=0, anchor="nw")
            parent_lbl._power_badge = badge
        
        lvl = POWER_MAP.get(item_id)
        if lvl in POWER_BADGES:
            badge.config(image=POWER_BADGES[lvl])
            badge.image = POWER_BADGES[lvl]
            badge.place(relx=0, rely=0, anchor="nw")
        else:
            badge.place_forget()
    
    def _bind_scroll_increment(self, entry_widget):
        def on_scroll(event):
            try:
                val = int(entry_widget.get())
                if event.delta > 0:
                    val += 1
                else:
                    val = max(1, val - 1)
                
                if self.selected_item_name:
                    item_data = self.item_lookup.get(self.selected_item_name, {})
                    max_stack = item_data.get("MaxStackSize", 99)
                    val = min(val, max_stack)
                
                entry_widget.delete(0, tk.END)
                entry_widget.insert(0, str(val))
            except ValueError:
                pass
        entry_widget.bind("<MouseWheel>", on_scroll)

if __name__ == "__main__":
    root = tk.Tk()
    app = SaveEditor(root)
    root.mainloop()
