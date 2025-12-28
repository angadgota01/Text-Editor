import tkinter as tk
from tkinter import ttk, filedialog, font, colorchooser, messagebox
from ctypes import *
import platform, os


class BackendManager:
    def __init__(self):
        self.lib = None
        self.load_library()

    def load_library(self):
        system = platform.system()
        if system == "Windows":
            lib_name = "libds.dll"  
        elif system == "Darwin": 
            lib_name = "libds.dylib"
        else:
            lib_name = "libds.so"

        paths = [
            os.path.join(os.path.dirname(__file__), "c_ds", lib_name),
            os.path.join(os.path.dirname(__file__), lib_name),
            os.path.join(os.getcwd(), "c_ds", lib_name)
        ]

        lib_path = next((p for p in paths if os.path.exists(p)), None)

        if not lib_path:
            messagebox.showerror("System Error", "Critical: C Library not found.\nPlease compile 'editor_core.c' into 'c_ds/libds.dll' (or .so).")
            exit(1)

        try:
            self.lib = CDLL(lib_path)
            self.lib.init()
       
            self.lib.push_undo_state.argtypes = [c_char_p]
            self.lib.perform_undo.argtypes = [c_char_p]
            self.lib.perform_undo.restype = c_char_p 
            self.lib.perform_redo.argtypes = [c_char_p]
            self.lib.perform_redo.restype = c_char_p
            self.lib.save_file.argtypes = [c_char_p, c_char_p]
            self.lib.free_mem.argtypes = [c_void_p]
        except Exception as e:
            messagebox.showerror("Linker Error", f"Failed to load C functions: {e}")
            exit(1)

backend = BackendManager()


class AdvancedText(tk.Frame):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        
        
        self.linenumbers = tk.Text(self, width=5, padx=5, takefocus=0, border=0,
                                   background='#f5f5f5', foreground='#999', state='disabled', font=("Consolas", 11))
        
        self.text = tk.Text(self, wrap=tk.WORD, undo=False, font=("Arial", 12), padx=10, pady=5)
        
        self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.sync_scroll)
        self.text.configure(yscrollcommand=self.scrollbar.set)
        
     
        self.linenumbers.pack(side=tk.LEFT, fill=tk.Y)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

      
        self.text.tag_configure("bold", font=("Arial", 12, "bold"))
        self.text.tag_configure("italic", font=("Arial", 12, "italic"))
        self.text.tag_configure("underline", underline=True)

        self.text.bind('<KeyRelease>', self.on_change)
        self.text.bind('<Button-1>', self.on_click)
        self.text.bind('<MouseWheel>', self.sync_wheel)

        self.save_timer = None

    def sync_scroll(self, *args):
        self.text.yview(*args)
        self.linenumbers.yview(*args)

    def sync_wheel(self, event):
        self.text.yview_scroll(int(-1*(event.delta/120)), "units")
        self.linenumbers.yview_scroll(int(-1*(event.delta/120)), "units")
        return "break"

    def update_line_numbers(self):
        lines = self.text.get('1.0', tk.END).count('\n')
        if lines == 0: lines = 1
        line_str = '\n'.join(str(i) for i in range(1, lines + 1))
        
        self.linenumbers.config(state='normal')
        self.linenumbers.delete('1.0', tk.END)
        self.linenumbers.insert('1.0', line_str)
        self.linenumbers.config(state='disabled')
        self.linenumbers.yview_moveto(self.text.yview()[0])

    def on_click(self, event):
        self.update_line_numbers()

    def on_change(self, event=None):
        self.update_line_numbers()
        
        if self.save_timer:
            self.after_cancel(self.save_timer)
        self.save_timer = self.after(500, self.push_state_to_c)

    def push_state_to_c(self):
       
        content = self.text.get("1.0", tk.END).encode('utf-8')
        backend.lib.push_undo_state(content)


class ResearchEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TextEditor")
        self.geometry("1200x800")
        
       
        self.file_map = {} 

        
        self.create_menus()

       
        self.create_toolbar()

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

       
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = tk.Label(self, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W, padx=10)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

     
        self.bind("<Control-n>", lambda e: self.file_new())
        self.bind("<Control-o>", lambda e: self.file_open())
        self.bind("<Control-s>", lambda e: self.file_save())
        self.bind("<Control-z>", self.edit_undo)
        self.bind("<Control-y>", self.edit_redo)
        self.bind("<Control-b>", lambda e: self.format_text("bold"))
        self.bind("<Control-i>", lambda e: self.format_text("italic"))
        self.bind("<Control-u>", lambda e: self.format_text("underline"))

        
        self.file_new()

    
    def create_menus(self):
        menubar = tk.Menu(self)
        
        
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New Project", accelerator="Ctrl+N", command=self.file_new)
        file_menu.add_command(label="Open File...", accelerator="Ctrl+O", command=self.file_open)
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.file_save)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu)

     
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Undo", accelerator="Ctrl+Z", command=self.edit_undo)
        edit_menu.add_command(label="Redo", accelerator="Ctrl+Y", command=self.edit_redo)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        self.config(menu=menubar)

    def create_toolbar(self):
        toolbar = tk.Frame(self, bd=1, relief=tk.RAISED, bg="#e1e1e1", height=40)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        self.font_var = tk.StringVar(value="Arial")
        font_box = ttk.Combobox(toolbar, textvariable=self.font_var, values=["Arial", "Courier New", "Consolas", "Times New Roman"], width=15, state="readonly")
        font_box.pack(side=tk.LEFT, padx=(10, 2), pady=5)
        font_box.bind("<<ComboboxSelected>>", self.apply_font)

       
        self.size_var = tk.StringVar(value="12")
        size_box = ttk.Combobox(toolbar, textvariable=self.size_var, values=[8, 10, 11, 12, 14, 18, 24, 36, 48], width=3)
        size_box.pack(side=tk.LEFT, padx=2, pady=5)
        size_box.bind("<<ComboboxSelected>>", self.apply_font)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5)

        
        def make_btn(text, cmd, font_style):
            btn = tk.Button(toolbar, text=text, command=cmd, font=font_style, width=3, relief=tk.FLAT, bg="#e1e1e1")
            btn.pack(side=tk.LEFT, padx=2, pady=5)
            return btn

        make_btn("B", lambda: self.format_text("bold"), ("Times", 11, "bold"))
        make_btn("I", lambda: self.format_text("italic"), ("Times", 11, "italic"))
        make_btn("U", lambda: self.format_text("underline"), ("Times", 11, "underline"))

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5)

       
        tk.Button(toolbar, text="Text Color", command=self.format_color, bg="#d9d9d9", relief=tk.FLAT).pack(side=tk.LEFT, padx=5, pady=5)

   
    def get_active_editor(self):
        try:
            tab_id = self.notebook.select()
            return self.notebook.nametowidget(tab_id).text
        except:
            return None

    def file_new(self):
        editor_frame = AdvancedText(self.notebook)
        self.notebook.add(editor_frame, text="Untitled")
        self.notebook.select(editor_frame)
        self.file_map[editor_frame] = None
        self.status_var.set("New document created.")

    def file_open(self):
        filepath = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if filepath:
            self.file_new()
            editor = self.get_active_editor()
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                editor.insert("1.0", content)
              
                backend.lib.push_undo_state(content.encode('utf-8'))
            
          
            current_tab = self.notebook.nametowidget(self.notebook.select())
            self.file_map[current_tab] = filepath
            self.notebook.tab(current_tab, text=os.path.basename(filepath))
            self.status_var.set(f"Opened: {filepath}")

    def file_save(self):
        current_tab = self.notebook.nametowidget(self.notebook.select())
        editor = current_tab.text
        filepath = self.file_map.get(current_tab)

        if not filepath:
            filepath = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
            if not filepath: return
            self.file_map[current_tab] = filepath
            self.notebook.tab(current_tab, text=os.path.basename(filepath))

        content = editor.get("1.0", tk.END).encode('utf-8')
       
        backend.lib.save_file(filepath.encode('utf-8'), content)
        self.status_var.set(f"Saved to {filepath}")

    def edit_undo(self, event=None):
        editor = self.get_active_editor()
        if not editor: return

        current_text = editor.get("1.0", tk.END).encode('utf-8')
        
       
        result_ptr = backend.lib.perform_undo(current_text)
        
        if result_ptr:
            try:
               
                prev_text = cast(result_ptr, c_char_p).value.decode('utf-8')
                
                
                editor.delete("1.0", tk.END)
                editor.insert("1.0", prev_text.rstrip('\n')) 
                
               
                backend.lib.free_mem(result_ptr)
                self.status_var.set("Undo successful.")
            except Exception as e:
                print(f"Undo Error: {e}")
        else:
            self.status_var.set("Nothing to undo.")
        return "break"

    def edit_redo(self, event=None):
        editor = self.get_active_editor()
        if not editor: return

        current_text = editor.get("1.0", tk.END).encode('utf-8')
        result_ptr = backend.lib.perform_redo(current_text)

        if result_ptr:
            try:
                next_text = cast(result_ptr, c_char_p).value.decode('utf-8')
                editor.delete("1.0", tk.END)
                editor.insert("1.0", next_text.rstrip('\n'))
                backend.lib.free_mem(result_ptr)
                self.status_var.set("Redo successful.")
            except Exception as e:
                print(f"Redo Error: {e}")
        else:
            self.status_var.set("Nothing to redo.")
        return "break"

    def format_text(self, tag_name):
        editor = self.get_active_editor()
        if not editor: return "break"
        
        try:
            
            if editor.tag_ranges("sel"):
                current_tags = editor.tag_names("sel.first")
                if tag_name in current_tags:
                    editor.tag_remove(tag_name, "sel.first", "sel.last")
                else:
                    editor.tag_add(tag_name, "sel.first", "sel.last")
        except tk.TclError:
            pass 
        return "break"

    def format_color(self):
        editor = self.get_active_editor()
        if not editor: return
        
        color = colorchooser.askcolor(title="Choose Text Color")[1]
        if color:
            tag_name = f"fg_{color}"
            editor.tag_configure(tag_name, foreground=color)
            try:
                editor.tag_add(tag_name, "sel.first", "sel.last")
            except tk.TclError: pass

    def apply_font(self, event=None):
        editor = self.get_active_editor()
        if not editor: return
        
        f_name = self.font_var.get()
        f_size = self.size_var.get()
        
       
        editor.configure(font=(f_name, int(f_size)))
        
        editor.tag_configure("bold", font=(f_name, int(f_size), "bold"))
        editor.tag_configure("italic", font=(f_name, int(f_size), "italic"))


if __name__ == "__main__":
    app = ResearchEditor()
    app.mainloop()