import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox, simpledialog
from ctypes import *
import platform
import os


# =============================================================================
#  BACKEND
# =============================================================================
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
            messagebox.showerror("Error", "Library not found!")
            exit(1)

        try:
            self.lib = CDLL(lib_path)
            self.lib.init()
        
            # Basic
            self.lib.push_undo_state.argtypes = [c_char_p]
            self.lib.perform_undo.argtypes = [c_char_p, c_char_p]
            self.lib.perform_undo.restype = c_int
            self.lib.perform_redo.argtypes = [c_char_p, c_char_p]
            self.lib.perform_redo.restype = c_int
            self.lib.save_file.argtypes = [c_char_p, c_char_p]
            self.lib.autocomplete.argtypes = [c_char_p, (c_char * 64) * 5]
            self.lib.autocomplete.restype = c_int
            
            # Statistics
            self.lib.count_words.argtypes = [c_char_p]
            self.lib.count_words.restype = c_int
            self.lib.count_lines.argtypes = [c_char_p]
            self.lib.count_lines.restype = c_int
            self.lib.count_characters.argtypes = [c_char_p]
            self.lib.count_characters.restype = c_int
            
            # Find
            self.lib.find_text.argtypes = [c_char_p, c_char_p]
            self.lib.find_text.restype = c_int
            self.lib.get_find_result.argtypes = [c_int, POINTER(c_int), POINTER(c_int), c_char_p]
            self.lib.get_find_result.restype = c_int
            
            # Navigation
            self.lib.get_line_position.argtypes = [c_char_p, c_int, POINTER(c_int)]
            self.lib.get_line_position.restype = c_int
            
            # Advanced
            self.lib.calculate_indent.argtypes = [c_char_p, c_int]
            self.lib.calculate_indent.restype = c_int
            
            self.lib.duplicate_line.argtypes = [c_char_p, c_int, c_int]
            self.lib.sort_lines.argtypes = [c_char_p, c_int]
            
            self.lib.analyze_word_frequency.argtypes = [c_char_p]
            self.lib.analyze_word_frequency.restype = c_int
            
            self.lib.get_word_frequency.argtypes = [c_int, c_char_p, POINTER(c_int)]
            self.lib.get_word_frequency.restype = c_int
            
            # New features
            self.lib.toggle_comment.argtypes = [c_char_p, c_int, c_int]
            self.lib.trim_trailing_whitespace.argtypes = [c_char_p, c_int]
            self.lib.convert_case.argtypes = [c_char_p, c_int, c_int, c_int]
            self.lib.move_line_up.argtypes = [c_char_p, c_int, c_int]
            self.lib.move_line_down.argtypes = [c_char_p, c_int, c_int]
            self.lib.remove_empty_lines.argtypes = [c_char_p, c_int]
            
            # Auto-correct
            self.lib.autocorrect.argtypes = [c_char_p, (c_char * 64) * 5]
            self.lib.autocorrect.restype = c_int
            self.lib.get_best_correction.argtypes = [c_char_p, c_char_p]
            self.lib.get_best_correction.restype = c_int
            self.lib.autocorrect_text.argtypes = [c_char_p, c_int]
            self.lib.autocorrect_text.restype = c_int

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load: {e}")
            exit(1)


backend = BackendManager()


# =============================================================================
#  AUTO-CORRECT DIALOG
# =============================================================================
class AutoCorrectDialog(tk.Toplevel):
    def __init__(self, parent, word, editor):
        super().__init__(parent)
        self.editor = editor
        self.word = word
        self.title("Auto-Correct Suggestions")
        self.geometry("350x300")
        self.transient(parent)
        
        tk.Label(self, text=f'Misspelled word: "{word}"', 
                font=("Arial", 11, "bold"), pady=10, fg="red").pack()
        
        tk.Label(self, text="Suggestions:", font=("Arial", 10)).pack(anchor="w", padx=10)
        
        frame = tk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.suggestions_list = tk.Listbox(frame, yscrollcommand=scrollbar.set,
                                          font=("Arial", 11), height=8)
        self.suggestions_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.suggestions_list.yview)
        
        self.suggestions_list.bind("<Double-1>", self.replace_word)
        
        # Get suggestions
        suggestions = ((c_char * 64) * 5)()
        count = backend.lib.autocorrect(word.encode(), suggestions)
        
        if count == 0:
            self.suggestions_list.insert(tk.END, "No suggestions found")
        else:
            for i in range(count):
                self.suggestions_list.insert(tk.END, suggestions[i].value.decode())
        
        # Buttons
        btn_frame = tk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(btn_frame, text="Replace", command=self.replace_word,
                 bg="#4CAF50", fg="white", relief=tk.FLAT, width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Ignore", command=self.destroy,
                 bg="#FF5722", fg="white", relief=tk.FLAT, width=10).pack(side=tk.LEFT, padx=5)
    
    def replace_word(self, event=None):
        selection = self.suggestions_list.curselection()
        if not selection:
            return
        
        replacement = self.suggestions_list.get(selection[0])
        if replacement == "No suggestions found":
            return
        
        cursor_pos = self.editor.index(tk.INSERT)
        line, col = map(int, cursor_pos.split('.'))
        line_text = self.editor.get(f"{line}.0", f"{line}.end")
        
        start_col = col
        while start_col > 0 and (line_text[start_col-1].isalnum() or line_text[start_col-1] == '_'):
            start_col -= 1
        
        end_col = col
        while end_col < len(line_text) and (line_text[end_col].isalnum() or line_text[end_col] == '_'):
            end_col += 1
        
        self.editor.delete(f"{line}.{start_col}", f"{line}.{end_col}")
        self.editor.insert(f"{line}.{start_col}", replacement)
        
        self.destroy()


# =============================================================================
#  FIND DIALOG
# =============================================================================
class FindReplaceDialog(tk.Toplevel):
    def __init__(self, parent, editor):
        super().__init__(parent)
        self.editor = editor
        self.title("Find & Replace")
        self.geometry("500x400")
        self.transient(parent)
        
        find_frame = tk.Frame(self, pady=10)
        find_frame.pack(fill=tk.X, padx=10)
        
        tk.Label(find_frame, text="Find:", font=("Arial", 10, "bold")).pack(anchor="w")
        self.find_var = tk.StringVar()
        find_entry = tk.Entry(find_frame, textvariable=self.find_var, font=("Arial", 11))
        find_entry.pack(fill=tk.X, pady=5)
        find_entry.focus_set()
        
        btn_frame = tk.Frame(find_frame)
        btn_frame.pack(fill=tk.X)
        tk.Button(btn_frame, text="🔍 Find All", command=self.find_all,
                 bg="#2196F3", fg="white", relief=tk.FLAT).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Next", command=self.find_next).pack(side=tk.LEFT, padx=2)
        
        results_frame = tk.Frame(self)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        tk.Label(results_frame, text="Results:", font=("Arial", 9, "bold")).pack(anchor="w")
        
        scrollbar = tk.Scrollbar(results_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.results_list = tk.Listbox(results_frame, yscrollcommand=scrollbar.set,
                                       font=("Consolas", 9), height=10)
        self.results_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.results_list.yview)
        
        self.results_list.bind("<Double-1>", self.jump_to_result)
        
        self.current_result = 0
        
    def find_all(self):
        query = self.find_var.get()
        if not query:
            return
        
        self.results_list.delete(0, tk.END)
        
        content = self.editor.get("1.0", tk.END).encode()
        count = backend.lib.find_text(content, query.encode())
        
        if count == 0:
            self.results_list.insert(tk.END, "No results found")
            return
        
        for i in range(count):
            line = c_int()
            col = c_int()
            context = create_string_buffer(100)
            
            backend.lib.get_find_result(i, byref(line), byref(col), context)
            
            display = f"Line {line.value}, Col {col.value}: {context.value.decode()[:50]}..."
            self.results_list.insert(tk.END, display)
        
        self.current_result = 0
        if count > 0:
            self.jump_to_index(0)
    
    def find_next(self):
        if self.results_list.size() == 0:
            self.find_all()
            return
        
        self.current_result = (self.current_result + 1) % self.results_list.size()
        self.jump_to_index(self.current_result)
    
    def jump_to_index(self, index):
        line = c_int()
        col = c_int()
        context = create_string_buffer(100)
        
        if backend.lib.get_find_result(index, byref(line), byref(col), context):
            self.editor.mark_set(tk.INSERT, f"{line.value}.{col.value}")
            self.editor.see(f"{line.value}.{col.value}")
            
            search_text = self.find_var.get()
            end_col = col.value + len(search_text)
            self.editor.tag_remove("sel", "1.0", tk.END)
            self.editor.tag_add("sel", f"{line.value}.{col.value}", 
                               f"{line.value}.{end_col}")
            self.editor.focus_set()
            
            self.results_list.selection_clear(0, tk.END)
            self.results_list.selection_set(index)
            self.results_list.see(index)
    
    def jump_to_result(self, event):
        selection = self.results_list.curselection()
        if selection:
            self.current_result = selection[0]
            self.jump_to_index(self.current_result)


# =============================================================================
#  WORD FREQUENCY DIALOG
# =============================================================================
class WordFrequencyDialog(tk.Toplevel):
    def __init__(self, parent, content):
        super().__init__(parent)
        self.title("Word Frequency Analysis")
        self.geometry("400x500")
        self.transient(parent)
        
        tk.Label(self, text="Most Common Words", font=("Arial", 12, "bold"), 
                pady=10).pack()
        
        frame = tk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.word_list = tk.Listbox(frame, yscrollcommand=scrollbar.set,
                                    font=("Consolas", 10), height=20)
        self.word_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.word_list.yview)
        
        count = backend.lib.analyze_word_frequency(content.encode())
        
        for i in range(min(count, 50)):
            word = create_string_buffer(64)
            freq = c_int()
            
            if backend.lib.get_word_frequency(i, word, byref(freq)):
                display = f"{word.value.decode():<20} : {freq.value:>3} times"
                self.word_list.insert(tk.END, display)


# =============================================================================
#  EDITOR
# =============================================================================
class SmartEditor(tk.Frame):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        
        self.linenumbers = tk.Text(self, width=5, padx=5, takefocus=0, border=0,
                                   background='#f5f5f5', foreground='#666', 
                                   state='disabled', font=("Consolas", 11))
        
        self.text = tk.Text(self, wrap=tk.WORD, undo=False, font=("Arial", 12), 
                           padx=10, pady=5)
        
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
        self.text.bind('<Down>', self.focus_autocomplete)
        self.text.bind('<Return>', self.auto_indent)

        self.autocomplete_list = None
        self.autocorrect_popup = None
        self.save_timer = None
        self.is_restoring = False

    def sync_scroll(self, *args):
        self.hide_autocomplete()
        self.hide_autocorrect()
        self.text.yview(*args)
        self.linenumbers.yview(*args)

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
        self.hide_autocomplete()
        self.hide_autocorrect()

    def auto_indent(self, event):
        content = self.text.get("1.0", tk.END).encode()
        current_line = int(self.text.index(tk.INSERT).split('.')[0])
        
        indent = backend.lib.calculate_indent(content, current_line + 1)
        
        self.text.insert(tk.INSERT, '\n' + ' ' * indent)
        return "break"

    def on_change(self, event=None):
        if self.is_restoring:
            return
        
        self.update_line_numbers()
        
        # Check if spacebar was pressed
        if event and event.keysym == "space":
            self.hide_autocomplete()
            
            index = self.text.index(tk.INSERT)
            line, col = map(int, index.split('.'))
            line_text = self.text.get(f"{line}.0", f"{line}.{col}")
            
            if line_text and line_text[-1] == ' ':
                line_text = line_text[:-1]
            
            prev_word = ""
            for c in reversed(line_text):
                if not c.isalnum() and c != "_":
                    break
                prev_word = c + prev_word
            
            if len(prev_word) >= 2:
                suggestions = ((c_char * 64) * 5)()
                count = backend.lib.autocorrect(prev_word.encode(), suggestions)
                
                if count > 0:
                    self.show_autocorrect_for_word(prev_word, suggestions, count)
                else:
                    self.hide_autocorrect()
            else:
                self.hide_autocorrect()
            
            if self.save_timer:
                self.after_cancel(self.save_timer)
            self.save_timer = self.after(500, self.push_state)
            return
        
        if event and event.keysym in ("Return", "Tab", "Escape", "space"):
            self.hide_autocomplete()
            if self.save_timer:
                self.after_cancel(self.save_timer)
            self.save_timer = self.after(500, self.push_state)
            return
        
        self.hide_autocorrect()
        self.show_autocomplete()
        
        if self.save_timer:
            self.after_cancel(self.save_timer)
        self.save_timer = self.after(500, self.push_state)

    def push_state(self):
        content = self.text.get("1.0", "end-1c").encode('utf-8')
        backend.lib.push_undo_state(content)

    def get_current_word(self):
        index = self.text.index(tk.INSERT)
        text_before = self.text.get("1.0", index)
        word = ""
        for c in reversed(text_before):
            if not c.isalnum() and c != "_":
                break
            word = c + word
        return word

    def show_autocomplete(self):
        prefix = self.get_current_word()
        if len(prefix) < 2:
            self.hide_autocomplete()
            return

        suggestions = ((c_char * 64) * 5)()
        count = backend.lib.autocomplete(prefix.encode(), suggestions)

        if count == 0:
            self.hide_autocomplete()
            return

        if self.autocomplete_list:
            self.autocomplete_list.destroy()
        
        self.autocomplete_list = tk.Listbox(self.text, height=5, width=30, 
                                           bg="white", bd=1, relief=tk.SOLID)
        self.autocomplete_list.bind("<ButtonRelease-1>", self.apply_suggestion)
        self.autocomplete_list.bind("<Return>", self.apply_suggestion)
        
        for i in range(count):
            self.autocomplete_list.insert(tk.END, suggestions[i].value.decode())

        bbox = self.text.bbox(tk.INSERT)
        if bbox:
            x, y, w, h = bbox
            self.autocomplete_list.place(x=x, y=y+h)
            self.autocomplete_list.lift()

    def hide_autocomplete(self):
        if self.autocomplete_list:
            self.autocomplete_list.destroy()
            self.autocomplete_list = None

    def focus_autocomplete(self, event):
        if self.autocomplete_list:
            self.autocomplete_list.focus_set()
            self.autocomplete_list.selection_set(0)
            return "break"
    
    def apply_suggestion(self, event=None):
        if not self.autocomplete_list:
            return
            
        selection = self.autocomplete_list.curselection()
        if not selection:
            return

        selected = self.autocomplete_list.get(selection[0])

        index = self.text.index(tk.INSERT)
        line, col = map(int, index.split('.'))
        line_text = self.text.get(f"{line}.0", f"{line}.end")

        pos = col - 1
        while pos >= 0:
            if not (line_text[pos].isalnum() or line_text[pos] == "_"):
                break
            pos -= 1
        word_start_col = pos + 1
        start_index = f"{line}.{word_start_col}"

        self.is_restoring = True
        self.text.delete(start_index, tk.INSERT)
        self.text.insert(start_index, selected)
        self.is_restoring = False

        self.hide_autocomplete()
        self.text.focus_set()
        return "break"

    def show_autocorrect_for_word(self, word, suggestions, count):
        if not self.autocorrect_popup:
            self.autocorrect_popup = tk.Toplevel(self)
            self.autocorrect_popup.wm_overrideredirect(True)
            self.autocorrect_popup.attributes("-topmost", True)
            self.autocorrect_popup.config(bg="#ffffe0", bd=1, relief=tk.SOLID)
        
        for widget in self.autocorrect_popup.winfo_children():
            widget.destroy()

        limit = min(count, 2)
        
        header = tk.Label(self.autocorrect_popup, text="Did you mean?", bg="#ffffe0", font=("Arial", 8, "bold"))
        header.pack(anchor="w", padx=2)

        for i in range(limit):
            sugg = suggestions[i].value.decode()
            lbl = tk.Label(
                self.autocorrect_popup, 
                text=sugg, 
                bg="#ffffe0", 
                fg="blue",
                font=("Arial", 10, "underline"),
                padx=5, pady=1,
                cursor="hand2"
            )
            lbl.pack(anchor="w")
            lbl.bind("<Button-1>", lambda e, w=word, s=sugg: self.apply_correction_for_word(w, s))

        bbox = self.text.bbox(tk.INSERT)
        if bbox:
            x, y, w, h = bbox
            abs_x = self.text.winfo_rootx() + x
            abs_y = self.text.winfo_rooty() + y + h + 5
            
            self.autocorrect_popup.geometry(f"+{abs_x}+{abs_y}")

    def hide_autocorrect(self):
        if self.autocorrect_popup:
            self.autocorrect_popup.destroy()
            self.autocorrect_popup = None

    def apply_correction_for_word(self, word, correction):
        index = self.text.index(tk.INSERT)
        line, col = map(int, index.split('.'))
        
        line_text = self.text.get(f"{line}.0", f"{line}.{col}")
        
        word_pos = line_text.rfind(word)
        if word_pos != -1:
            start_col = word_pos
            end_col = word_pos + len(word)
            start_index = f"{line}.{start_col}"
            end_index = f"{line}.{end_col}"
            
            self.is_restoring = True
            self.text.delete(start_index, end_index)
            self.text.insert(start_index, correction)
            self.is_restoring = False
        
        self.hide_autocorrect()
        self.text.focus_set()


# =============================================================================
#  MAIN APP
# =============================================================================
class TextEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Advanced Smart Text Editor")
        self.geometry("1100x750")
        
        self.file_map = {} 
        self.current_theme = "light"
        
        self.create_menus()
        self.create_toolbar()
        
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        status_frame = tk.Frame(self, bd=1, relief=tk.SUNKEN)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_var = tk.StringVar(value="Ready")
        tk.Label(status_frame, textvariable=self.status_var, anchor=tk.W, padx=10).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.stats_var = tk.StringVar(value="Lines: 0 | Words: 0 | Chars: 0")
        tk.Label(status_frame, textvariable=self.stats_var, anchor=tk.E, padx=10, 
                font=("Arial", 9), fg="#666").pack(side=tk.RIGHT)
        
        # Shortcuts
        self.bind("<Control-n>", lambda e: self.file_new())
        self.bind("<Control-o>", lambda e: self.file_open())
        self.bind("<Control-s>", lambda e: self.file_save())
        self.bind("<Control-z>", self.edit_undo)
        self.bind("<Control-y>", self.edit_redo)
        self.bind("<Control-f>", lambda e: self.open_find())
        self.bind("<Control-g>", lambda e: self.goto_line())
        self.bind("<Control-d>", lambda e: self.duplicate_line())
        self.bind("<Control-slash>", lambda e: self.toggle_comment())
        self.bind("<Alt-Up>", lambda e: self.move_line_up())
        self.bind("<Alt-Down>", lambda e: self.move_line_down())
        self.bind("<Control-b>", lambda e: self.format_text("bold"))
        self.bind("<Control-i>", lambda e: self.format_text("italic"))
        self.bind("<Control-u>", lambda e: self.format_text("underline"))
        self.bind("<F7>", lambda e: self.check_word_spelling())
        
        self.after(1000, self.update_statistics)
        
        self.apply_theme("light")
        self.file_new()
    
    def create_menus(self):
        menubar = tk.Menu(self)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New", accelerator="Ctrl+N", command=self.file_new)
        file_menu.add_command(label="Open", accelerator="Ctrl+O", command=self.file_open)
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.file_save)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Undo", accelerator="Ctrl+Z", command=self.edit_undo)
        edit_menu.add_command(label="Redo", accelerator="Ctrl+Y", command=self.edit_redo)
        edit_menu.add_separator()
        edit_menu.add_command(label="Find", accelerator="Ctrl+F", command=self.open_find)
        edit_menu.add_command(label="Go to Line", accelerator="Ctrl+G", command=self.goto_line)
        edit_menu.add_command(label="Duplicate Line", accelerator="Ctrl+D", command=self.duplicate_line)
        edit_menu.add_separator()
        edit_menu.add_command(label="Toggle Comment", accelerator="Ctrl+/", command=self.toggle_comment)
        edit_menu.add_command(label="Move Line Up", accelerator="Alt+Up", command=self.move_line_up)
        edit_menu.add_command(label="Move Line Down", accelerator="Alt+Down", command=self.move_line_down)
        edit_menu.add_separator()
        edit_menu.add_command(label="UPPERCASE", command=self.convert_to_uppercase)
        edit_menu.add_command(label="lowercase", command=self.convert_to_lowercase)
        edit_menu.add_command(label="Sort Lines", command=self.sort_lines)
        edit_menu.add_command(label="Trim Whitespace", command=self.trim_whitespace)
        edit_menu.add_command(label="Remove Empty Lines", command=self.remove_empty_lines)
        edit_menu.add_separator()
        edit_menu.add_command(label="Check Spelling", accelerator="F7", command=self.check_word_spelling)
        edit_menu.add_command(label="Auto-Correct Document", command=self.autocorrect_document)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Statistics", command=self.show_statistics)
        view_menu.add_command(label="Word Frequency", command=self.show_word_frequency)
        view_menu.add_command(label="Toggle Theme", command=self.toggle_theme)
        menubar.add_cascade(label="View", menu=view_menu)
        
        self.config(menu=menubar)

    def create_toolbar(self):
        toolbar = tk.Frame(self, bd=1, relief=tk.RAISED, bg="#e1e1e1", height=40)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        self.font_var = tk.StringVar(value="Arial")
        font_box = ttk.Combobox(toolbar, textvariable=self.font_var, 
                               values=["Arial", "Courier New", "Consolas", "Times New Roman"], 
                               width=15, state="readonly")
        font_box.pack(side=tk.LEFT, padx=(10, 2), pady=5)
        font_box.bind("<<ComboboxSelected>>", self.apply_font)

        self.size_var = tk.StringVar(value="12")
        size_box = ttk.Combobox(toolbar, textvariable=self.size_var, 
                               values=[10, 11, 12, 14, 16, 18, 20, 24], width=3)
        size_box.pack(side=tk.LEFT, padx=2, pady=5)
        size_box.bind("<<ComboboxSelected>>", self.apply_font)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5)

        def make_btn(text, cmd, font_style):
            btn = tk.Button(toolbar, text=text, command=cmd, font=font_style, 
                           width=3, relief=tk.FLAT, bg="#e1e1e1")
            btn.pack(side=tk.LEFT, padx=2, pady=5)

        make_btn("B", lambda: self.format_text("bold"), ("Times", 11, "bold"))
        make_btn("I", lambda: self.format_text("italic"), ("Times", 11, "italic"))
        make_btn("U", lambda: self.format_text("underline"), ("Times", 11, "underline"))

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5)

        tk.Button(toolbar, text="🔍 Find", command=self.open_find, 
                 bg="#2196F3", fg="white", relief=tk.FLAT).pack(side=tk.LEFT, padx=2, pady=5)
        
        tk.Button(toolbar, text="📊 Stats", command=self.show_statistics, 
                 bg="#4CAF50", fg="white", relief=tk.FLAT).pack(side=tk.LEFT, padx=2, pady=5)
        
        tk.Button(toolbar, text="✓ Spell", command=self.check_word_spelling, 
                 bg="#9C27B0", fg="white", relief=tk.FLAT).pack(side=tk.LEFT, padx=2, pady=5)
        
        tk.Button(toolbar, text="Sort", command=self.sort_lines, 
                 bg="#FF9800", fg="white", relief=tk.FLAT).pack(side=tk.LEFT, padx=2, pady=5)
        
        tk.Button(toolbar, text="Theme", command=self.toggle_theme, 
                 bg="#444", fg="white", relief=tk.FLAT).pack(side=tk.LEFT, padx=2, pady=5)

    def get_active_editor(self):
        try:
            tab_id = self.notebook.select()
            return self.notebook.nametowidget(tab_id).text
        except:
            return None

    def file_new(self):
        editor_frame = SmartEditor(self.notebook)
        self.notebook.add(editor_frame, text="Untitled")
        self.notebook.select(editor_frame)
        self.file_map[editor_frame] = None

    def file_open(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
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

    def file_save(self):
        current_tab = self.notebook.nametowidget(self.notebook.select())
        editor = current_tab.text
        filepath = self.file_map.get(current_tab)

        if not filepath:
            filepath = filedialog.asksaveasfilename(
                defaultextension=".txt", 
                filetypes=[("Text Files", "*.txt")]
            )
            if not filepath: 
                return
            self.file_map[current_tab] = filepath
            self.notebook.tab(current_tab, text=os.path.basename(filepath))

        content = editor.get("1.0", tk.END).encode('utf-8')
        backend.lib.save_file(filepath.encode('utf-8'), content)
        self.status_var.set(f"Saved: {filepath}")

    def edit_undo(self, event=None):
        editor = self.get_active_editor()
        if not editor:
            return "break"

        current = editor.get("1.0", tk.END).encode()
        buffer = create_string_buffer(10000)

        editor.master.is_restoring = True

        if backend.lib.perform_undo(current, buffer):
            editor.delete("1.0", tk.END)
            editor.insert("1.0", buffer.value.decode())
            self.status_var.set("Undo")
        else:
            self.status_var.set("Nothing to undo")

        editor.master.is_restoring = False
        return "break"

    def edit_redo(self, event=None):
        editor = self.get_active_editor()
        if not editor:
            return "break"

        current = editor.get("1.0", tk.END).encode()
        buffer = create_string_buffer(10000)

        if backend.lib.perform_redo(current, buffer):
            editor.delete("1.0", tk.END)
            editor.insert("1.0", buffer.value.decode())
            self.status_var.set("Redo")
        else:
            self.status_var.set("Nothing to redo")

        return "break"

    def format_text(self, tag_name):
        editor = self.get_active_editor()
        if not editor: 
            return "break"
        
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

    def apply_font(self, event=None):
        editor = self.get_active_editor()
        if not editor: 
            return
        
        f_name = self.font_var.get()
        f_size = self.size_var.get()
        
        editor.configure(font=(f_name, int(f_size)))
        editor.tag_configure("bold", font=(f_name, int(f_size), "bold"))
        editor.tag_configure("italic", font=(f_name, int(f_size), "italic"))

    def toggle_theme(self):
        if self.current_theme == "light":
            self.apply_theme("dark")
            self.current_theme = "dark"
        else:
            self.apply_theme("light")
            self.current_theme = "light"

    def apply_theme(self, theme):
        if theme == "dark":
            text_bg = "#1e1e1e"
            fg = "#ffffff"
            insert_color = "white"
            ln_bg = "#333333"
            ln_fg = "#888"
        else:
            text_bg = "#ffffff"
            fg = "#000000"
            insert_color = "black"
            ln_bg = "#f5f5f5"
            ln_fg = "#666"
        
        for tab in self.notebook.tabs():
            widget = self.notebook.nametowidget(tab)
            widget.text.config(bg=text_bg, fg=fg, insertbackground=insert_color)
            widget.linenumbers.config(background=ln_bg, foreground=ln_fg)
    
    def update_statistics(self):
        editor = self.get_active_editor()
        if editor:
            content = editor.get("1.0", tk.END).encode()
            
            words = backend.lib.count_words(content)
            lines = backend.lib.count_lines(content)
            chars = backend.lib.count_characters(content)
            
            self.stats_var.set(f"Lines: {lines} | Words: {words} | Chars: {chars}")
        
        self.after(1000, self.update_statistics)
    
    def show_statistics(self):
        editor = self.get_active_editor()
        if not editor:
            return
        
        content = editor.get("1.0", tk.END).encode()
        
        words = backend.lib.count_words(content)
        lines = backend.lib.count_lines(content)
        chars = backend.lib.count_characters(content)
        
        msg = f"Document Statistics:\n\n"
        msg += f"Lines: {lines}\n"
        msg += f"Words: {words}\n"
        msg += f"Characters: {chars}\n"
        
        messagebox.showinfo("Statistics", msg)
    
    def open_find(self):
        editor = self.get_active_editor()
        if editor:
            FindReplaceDialog(self, editor)
    
    def goto_line(self):
        editor = self.get_active_editor()
        if not editor:
            return
        
        line_num = simpledialog.askinteger("Go to Line", "Line number:", minvalue=1)
        if line_num:
            content = editor.get("1.0", tk.END).encode()
            char_pos = c_int()
            
            if backend.lib.get_line_position(content, line_num, byref(char_pos)):
                editor.mark_set(tk.INSERT, f"1.0+{char_pos.value}c")
                editor.see(tk.INSERT)
                self.status_var.set(f"Line {line_num}")
    
    def duplicate_line(self):
        editor = self.get_active_editor()
        if not editor:
            return
        
        current_line = int(editor.index(tk.INSERT).split('.')[0])
        content = create_string_buffer(editor.get("1.0", tk.END).encode(), 10000)
        
        backend.lib.duplicate_line(content, current_line, 10000)
        
        editor.master.is_restoring = True
        editor.delete("1.0", tk.END)
        editor.insert("1.0", content.value.decode())
        editor.master.is_restoring = False
        
        self.status_var.set(f"Line {current_line} duplicated")
        return "break"
    
    def sort_lines(self):
        editor = self.get_active_editor()
        if not editor:
            return
        
        content = create_string_buffer(editor.get("1.0", tk.END).encode(), 10000)
        
        backend.lib.sort_lines(content, 10000)
        
        editor.master.is_restoring = True
        editor.delete("1.0", tk.END)
        editor.insert("1.0", content.value.decode())
        editor.master.is_restoring = False
        
        self.status_var.set("Lines sorted")
    
    def show_word_frequency(self):
        editor = self.get_active_editor()
        if not editor:
            return
        
        content = editor.get("1.0", tk.END)
        WordFrequencyDialog(self, content)
    
    def toggle_comment(self):
        editor = self.get_active_editor()
        if not editor:
            return
        
        current_line = int(editor.index(tk.INSERT).split('.')[0])
        content = create_string_buffer(editor.get("1.0", tk.END).encode(), 10000)
        
        backend.lib.toggle_comment(content, current_line, 10000)
        
        editor.master.is_restoring = True
        editor.delete("1.0", tk.END)
        editor.insert("1.0", content.value.decode())
        editor.master.is_restoring = False
        
        self.status_var.set("Comment toggled")
        return "break"
    
    def trim_whitespace(self):
        editor = self.get_active_editor()
        if not editor:
            return
        
        content = create_string_buffer(editor.get("1.0", tk.END).encode(), 10000)
        backend.lib.trim_trailing_whitespace(content, 10000)
        
        editor.master.is_restoring = True
        editor.delete("1.0", tk.END)
        editor.insert("1.0", content.value.decode())
        editor.master.is_restoring = False
        
        self.status_var.set("Whitespace trimmed")
    
    def convert_to_uppercase(self):
        editor = self.get_active_editor()
        if not editor:
            return
        
        try:
            sel_start = editor.index("sel.first")
            sel_end = editor.index("sel.last")
            
            selected_text = editor.get(sel_start, sel_end)
            editor.delete(sel_start, sel_end)
            editor.insert(sel_start, selected_text.upper())
            
            self.status_var.set("Converted to UPPERCASE")
        except tk.TclError:
            messagebox.showinfo("Info", "Select text first")
    
    def convert_to_lowercase(self):
        editor = self.get_active_editor()
        if not editor:
            return
        
        try:
            sel_start = editor.index("sel.first")
            sel_end = editor.index("sel.last")
            
            selected_text = editor.get(sel_start, sel_end)
            editor.delete(sel_start, sel_end)
            editor.insert(sel_start, selected_text.lower())
            
            self.status_var.set("Converted to lowercase")
        except tk.TclError:
            messagebox.showinfo("Info", "Select text first")
    
    def move_line_up(self):
        editor = self.get_active_editor()
        if not editor:
            return
        
        current_line = int(editor.index(tk.INSERT).split('.')[0])
        if current_line <= 1:
            return "break"
        
        content = create_string_buffer(editor.get("1.0", tk.END).encode(), 10000)
        backend.lib.move_line_up(content, current_line, 10000)
        
        editor.master.is_restoring = True
        editor.delete("1.0", tk.END)
        editor.insert("1.0", content.value.decode())
        editor.mark_set(tk.INSERT, f"{current_line-1}.0")
        editor.master.is_restoring = False
        
        return "break"
    
    def move_line_down(self):
        editor = self.get_active_editor()
        if not editor:
            return
        
        current_line = int(editor.index(tk.INSERT).split('.')[0])
        content = create_string_buffer(editor.get("1.0", tk.END).encode(), 10000)
        
        backend.lib.move_line_down(content, current_line, 10000)
        
        editor.master.is_restoring = True
        editor.delete("1.0", tk.END)
        editor.insert("1.0", content.value.decode())
        editor.mark_set(tk.INSERT, f"{current_line+1}.0")
        editor.master.is_restoring = False
        
        return "break"
    
    def remove_empty_lines(self):
        editor = self.get_active_editor()
        if not editor:
            return
        
        content = create_string_buffer(editor.get("1.0", tk.END).encode(), 10000)
        backend.lib.remove_empty_lines(content, 10000)
        
        editor.master.is_restoring = True
        editor.delete("1.0", tk.END)
        editor.insert("1.0", content.value.decode())
        editor.master.is_restoring = False
        
        self.status_var.set("Empty lines removed")
    
    def check_word_spelling(self):
        editor = self.get_active_editor()
        if not editor:
            return
        
        word = editor.master.get_current_word()
        if len(word) < 2:
            messagebox.showinfo("Info", "Place cursor on a word")
            return
        
        AutoCorrectDialog(self, word, editor)
    
    def autocorrect_document(self):
        editor = self.get_active_editor()
        if not editor:
            return
        
        content = create_string_buffer(editor.get("1.0", tk.END).encode(), 10000)
        corrections_made = backend.lib.autocorrect_text(content, 10000)
        
        if corrections_made > 0:
            editor.master.is_restoring = True
            editor.delete("1.0", tk.END)
            editor.insert("1.0", content.value.decode())
            editor.master.is_restoring = False
            
            self.status_var.set(f"{corrections_made} corrections made")
            messagebox.showinfo("Auto-Correct", f"Made {corrections_made} corrections")
        else:
            messagebox.showinfo("Auto-Correct", "No corrections needed")


if __name__ == "__main__":
    app = TextEditor()
    app.mainloop()
