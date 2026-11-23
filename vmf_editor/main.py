
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES

from vmf_parser import VMFParser, VMFNode


class VMFExplorer:

    def __init__(self, root):

        self.root = root

        self.root.title("VMF Explorer")
        self.root.geometry("900x600")
        self.root.minsize(500, 300)
        self.root.configure(background="#111111")

        self.parser = VMFParser()

        self.document = None
        self.file_path = None

        self.node_by_iid = {}

        # Search

        self.search_window = None
        self.search_key = None
        self.search_value = None
        self.search_message = None

        self.search_matches = []
        self.search_index = -1
        self.search_query = None

        self.create_styles()
        self.create_menu()
        self.create_layout()
        self.create_context_menu()
        self.setup_drag_drop()

    # -----------------------------------------
    # STYLES
    # -----------------------------------------

    def create_styles(self):

        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure(
            "Custom.Treeview",
            background="#252525",
            foreground="#eeeeee",
            fieldbackground="#252525",
            font=("Arial", 11),
            rowheight=25
        )

        style.configure(
            "Custom.Treeview.Heading",
            background="#333333",
            foreground="white"
        )

        style.map(
            "Custom.Treeview",
            background=[("selected", "#454f65")],
            foreground=[("selected", "white")]
        )

        style.configure(
            "Custom.TLabel",
            foreground="#eeeeee",
            background="#202020",
            font=("Arial", 10)
        )

    # -----------------------------------------
    # MENU
    # -----------------------------------------

    def create_menu(self):

        menu_bar = tk.Menu(
            self.root,
            background="#202020",
            foreground="#eeeeee"
        )

        file_menu = tk.Menu(
            menu_bar,
            tearoff=False,
            background="#202020",
            foreground="#eeeeee"
        )

        file_menu.add_command(
            label="Open...",
            accelerator="Ctrl+O",
            command=self.open_file
        )

        file_menu.add_separator()

        file_menu.add_command(
            label="Close",
            command=self.close_file
        )

        file_menu.add_command(
            label="Exit",
            command=self.root.destroy
        )

        menu_bar.add_cascade(
            label="File",
            menu=file_menu
        )

        edit_menu = tk.Menu(
            menu_bar,
            tearoff=False,
            background="#202020",
            foreground="#eeeeee"
        )

        edit_menu.add_command(
            label="Find...",
            accelerator="Ctrl+F",
            command=self.open_search
        )

        menu_bar.add_cascade(
            label="Edit",
            menu=edit_menu
        )

        self.root.configure(menu=menu_bar)

        self.root.bind(
            "<Control-o>",
            lambda event: self.open_file()
        )

        self.root.bind(
            "<Control-f>",
            lambda event: self.open_search()
        )

    # -----------------------------------------
    # LAYOUT
    # -----------------------------------------

    def create_layout(self):

        self.columns = ttk.PanedWindow(
            self.root,
            orient="horizontal"
        )

        self.columns.pack(
            fill="both",
            expand=True,
            padx=5,
            pady=5
        )

        self.left_side = tk.Frame(
            self.columns,
            background="#252525"
        )

        self.right_side = tk.Frame(
            self.columns,
            background="#202020"
        )

        self.columns.add(
            self.left_side,
            weight=2
        )

        self.columns.add(
            self.right_side,
            weight=3
        )

        # TREEVIEW

        self.tree_view = ttk.Treeview(
            self.left_side,
            columns=("type", "value"),
            show="tree headings",
            style="Custom.Treeview",
            selectmode="browse"
        )

        self.tree_view.heading("#0", text="VMF")
        self.tree_view.heading("type", text="Type")
        self.tree_view.heading("value", text="Value")

        self.tree_view.column(
            "#0",
            width=200,
            minwidth=100
        )

        self.tree_view.column(
            "type",
            width=75,
            minwidth=60
        )

        self.tree_view.column(
            "value",
            width=130,
            minwidth=70
        )

        tree_scroll = ttk.Scrollbar(
            self.left_side,
            orient="vertical",
            command=self.tree_view.yview
        )

        self.tree_view.configure(
            yscrollcommand=tree_scroll.set
        )

        self.tree_view.pack(
            side="left",
            fill="both",
            expand=True
        )

        tree_scroll.pack(
            side="right",
            fill="y"
        )

        self.tree_view.bind(
            "<<TreeviewSelect>>",
            self.on_select
        )

        # PROPERTIES

        ttk.Label(
            self.right_side,
            text="Properties",
            style="Custom.TLabel"
        ).pack(
            anchor="w",
            padx=10,
            pady=10
        )

        self.properties = tk.Text(
            self.right_side,
            background="#202020",
            foreground="#eeeeee",
            insertbackground="white",
            selectbackground="#455a78",
            selectforeground="white",
            font=("Consolas", 11),
            relief="flat",
            wrap="none",
            padx=10,
            pady=10
        )

        self.properties.pack(
            fill="both",
            expand=True
        )

        # Read-only, but allows selection and copying.

        self.properties.bind(
            "<Key>",
            self.properties_key
        )

        self.properties.bind(
            "<Control-c>",
            self.copy_properties
        )

        self.properties.bind(
            "<Control-C>",
            self.copy_properties
        )

        self.properties.bind(
            "<Control-a>",
            self.select_all_properties
        )

        self.properties.bind(
            "<Control-A>",
            self.select_all_properties
        )

        self.properties.bind(
            "<Button-3>",
            self.properties_context_menu
        )

        self.properties_menu = tk.Menu(
            self.root,
            tearoff=False
        )

        self.properties_menu.add_command(
            label="Copy",
            command=self.copy_properties
        )

        self.properties_menu.add_command(
            label="Select all",
            command=self.select_all_properties
        )

        # STATUS BAR

        self.status = ttk.Label(
            self.root,
            text="Ready",
            style="Custom.TLabel"
        )

        self.status.pack(
            fill="x",
            padx=8,
            pady=5
        )

    # -----------------------------------------
    # DRAG & DROP
    # -----------------------------------------

    def setup_drag_drop(self):

        # Главному окну
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind("<<Drop>>", self.on_drop)

        # Дереву
        self.tree_view.drop_target_register(DND_FILES)
        self.tree_view.dnd_bind("<<Drop>>", self.on_drop)
        
    def on_drop(self, event):

        files = self.root.tk.splitlist(event.data)

        if not files:
            return

        file_path = files[0]

        if not file_path.lower().endswith(".vmf"):
            self.status.configure(
                text="Invalid file. Only VMF files are supported."
            )
            return

        # Если файл уже открыт — заменяем его.
        # Если не открыт — загружаем впервые.
        self.load_file(file_path)

    # -----------------------------------------
    # PROPERTIES INPUT CONTROL
    # -----------------------------------------

    def properties_key(self, event):

        # Allow copy, select all and navigation.
        # Block editing.

        if event.state & 0x4:

            if event.keysym.lower() in ("c", "a"):
                return None

        allowed = (
            "Left", "Right", "Up", "Down",
            "Home", "End", "Prior", "Next"
        )

        if event.keysym in allowed:
            return None

        return "break"

    def copy_properties(self, event=None):

        try:
            selected = self.properties.get(
                "sel.first",
                "sel.last"
            )

        except tk.TclError:
            return "break"

        self.root.clipboard_clear()
        self.root.clipboard_append(selected)

        return "break"

    def select_all_properties(self, event=None):

        self.properties.tag_add(
            "sel",
            "1.0",
            "end-1c"
        )

        return "break"

    def properties_context_menu(self, event):

        self.properties_menu.tk_popup(
            event.x_root,
            event.y_root
        )

    # -----------------------------------------
    # CONTEXT MENU
    # -----------------------------------------

    def create_context_menu(self):

        self.context_menu = tk.Menu(
            self.root,
            tearoff=False,
            background="#202020",
            foreground="#eeeeee"
        )

        self.context_menu.add_command(
            label="Find...",
            command=self.open_search
        )

        self.context_menu.add_separator()

        self.context_menu.add_command(
            label="Expand all",
            command=self.expand_all
        )

        self.context_menu.add_command(
            label="Collapse all",
            command=self.collapse_all
        )

        self.tree_view.bind(
            "<Button-3>",
            self.show_context_menu
        )

    def show_context_menu(self, event):

        item = self.tree_view.identify_row(event.y)

        if item:
            self.tree_view.selection_set(item)

        try:

            self.context_menu.tk_popup(
                event.x_root,
                event.y_root
            )

        finally:
            self.context_menu.grab_release()

    # -----------------------------------------
    # FILE
    # -----------------------------------------

    def open_file(self):

        path = filedialog.askopenfilename(
            title="Open VMF",
            filetypes=[
                ("Valve Map Format", "*.vmf"),
                ("All files", "*.*")
            ]
        )

        if path:
            self.load_file(path)

    def load_file(self, path):

        self.status.configure(
            text="Reading file..."
        )

        self.root.update_idletasks()

        self.document = self.parser.parse(path)
        self.file_path = path

        self.search_matches.clear()
        self.search_index = -1
        self.search_query = None

        self.populate_tree()

        self.root.title(
            f"VMF Explorer - {path}"
        )

        self.status.configure(
            text=(
                f"Loaded | Encoding: {self.document.encoding} | "
                f"Errors: {len(self.document.errors)}"
            )
        )

        if self.document.errors:

            messagebox.showwarning(
                "VMF Parser",
                "\n".join(self.document.errors)
            )

        if self.search_window is not None:
            if self.search_window.winfo_exists():
                self.update_search_status(
                    "File changed. Search again."
                )

    def close_file(self):

        self.tree_view.delete(
            *self.tree_view.get_children()
        )

        self.node_by_iid.clear()

        self.document = None
        self.file_path = None

        self.search_matches.clear()
        self.search_index = -1
        self.search_query = None

        self.root.title("VMF Explorer")

        self.set_properties("No file opened")

        self.status.configure(
            text="Ready"
        )

    # -----------------------------------------
    # TREE GENERATION
    # -----------------------------------------

    def populate_tree(self):

        self.tree_view.delete(
            *self.tree_view.get_children()
        )

        self.node_by_iid.clear()

        if self.document is None:
            return

        self.insert_node(
            "",
            self.document.root
        )

        for item in self.tree_view.get_children():
            self.tree_view.item(
                item,
                open=True
            )

    def insert_node(self, parent, node):

        if node.kind == "block":
            node_type = "BLOCK"
            value = ""

        else:
            node_type = "VALUE"
            value = node.value

        iid = self.tree_view.insert(
            parent,
            "end",
            text=node.name,
            values=(node_type, value)
        )

        self.node_by_iid[iid] = node

        for child in node.children:

            self.insert_node(
                iid,
                child
            )

        return iid

    # -----------------------------------------
    # SELECTION
    # -----------------------------------------

    def on_select(self, event):

        selection = self.tree_view.selection()

        if not selection:
            return

        iid = selection[0]
        node = self.node_by_iid.get(iid)

        if node is None:
            return

        self.show_properties(node, iid)

    def show_properties(self, node, iid):

        path = self.get_node_path(iid)

        lines = [
            f"Name: {node.name}",
            f"Type: {node.kind}",
            f"Line: {node.line}",
            f"Path: {path}",
            ""
        ]

        if node.kind == "value":

            lines.append(
                f"Value: {node.value}"
            )

        else:

            lines.append(
                f"Children: {len(node.children)}"
            )

            lines.append("")
            lines.append("Child elements:")

            for child in node.children:

                if child.kind == "value":

                    lines.append(
                        f'  {child.name} = "{child.value}"'
                    )

                else:

                    lines.append(
                        f"  {child.name} {{...}}"
                    )

        self.set_properties(
            "\n".join(lines)
        )

    def get_node_path(self, iid):

        path = []

        while iid:

            path.append(
                self.tree_view.item(
                    iid,
                    "text"
                )
            )

            iid = self.tree_view.parent(iid)

        return " / ".join(
            reversed(path)
        )

    def set_properties(self, text):

        self.properties.delete(
            "1.0",
            "end"
        )

        self.properties.insert(
            "1.0",
            text
        )

    # -----------------------------------------
    # SEARCH WINDOW
    # -----------------------------------------

    def open_search(self):

        if self.document is None:

            messagebox.showinfo(
                "Find",
                "Open a VMF file first."
            )

            return

        if (
            self.search_window is not None
            and self.search_window.winfo_exists()
        ):

            self.search_window.deiconify()
            self.search_window.lift()
            self.search_key.focus_set()
            return

        window = tk.Toplevel(self.root)

        self.search_window = window

        window.title("Find")
        window.geometry("700x210")
        # window.resizable(False, False)
        window.configure(background="#202020")

        window.transient(self.root)

        mainframe = ttk.Frame(
            window,
            padding=(12, 12, 12, 12),
            style="Custom.TLabel"
        )

        mainframe.pack(
            fill="both",
            expand=True
        )

        # KEY

        ttk.Label(
            mainframe,
            text="Key:",
            style="Custom.TLabel"
        ).grid(
            row=0,
            column=0,
            sticky="w"
        )

        self.search_key = tk.StringVar()

        key_entry = ttk.Entry(
            mainframe,
            textvariable=self.search_key,
            justify="left",
            width=35
        )

        key_entry.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=(0, 8),
            pady=5
        )

        # VALUE

        ttk.Label(
            mainframe,
            text="Value:",
            style="Custom.TLabel"
        ).grid(
            row=0,
            column=1,
            sticky="w"
        )

        self.search_value = tk.StringVar()

        value_entry = ttk.Entry(
            mainframe,
            textvariable=self.search_value,
            justify="left",
            width=35
        )

        value_entry.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(8, 0),
            pady=5
        )

        # BUTTONS

        previous_button = ttk.Button(
            mainframe,
            text="To Find Previous...",
            command=lambda: self.find_previous()
        )

        previous_button.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=(0, 8),
            pady=10
        )

        next_button = ttk.Button(
            mainframe,
            text="To Find Next...",
            command=lambda: self.find_next()
        )

        next_button.grid(
            row=2,
            column=1,
            sticky="ew",
            padx=(8, 0),
            pady=10
        )

        # RESULT

        self.search_message = ttk.Label(
            mainframe,
            text="Enter a key or value.",
            style="Custom.TLabel"
        )

        self.search_message.grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="w",
            pady=8
        )

        mainframe.columnconfigure(0, weight=1)
        mainframe.columnconfigure(1, weight=1)

        key_entry.bind(
            "<Return>",
            lambda event: self.find_next()
        )

        value_entry.bind(
            "<Return>",
            lambda event: self.find_next()
        )

        window.bind(
            "<Escape>",
            lambda event: window.destroy()
        )

        window.protocol(
            "WM_DELETE_WINDOW",
            window.destroy
        )

        key_entry.focus_set()

    # -----------------------------------------
    # SEARCH ENGINE
    # -----------------------------------------

    def collect_nodes(self):

        result = []

        def recursive(node):

            result.append(node)

            for child in node.children:
                recursive(child)

        recursive(self.document.root)

        return result

    def find_nodes(self, key, value):

        key = key.strip().casefold()
        value = value.strip().casefold()

        if not key and not value:
            return []

        matches = []

        for iid, node in self.node_by_iid.items():

            key_match = (
                not key
                or key in node.name.casefold()
            )

            value_match = (
                not value
                or (
                    node.kind == "value"
                    and value in node.value.casefold()
                )
            )

            if key_match and value_match:
                matches.append(iid)

        return matches

    def prepare_search(self):

        key = self.search_key.get()
        value = self.search_value.get()

        query = (
            key.strip().casefold(),
            value.strip().casefold()
        )

        if not any(query):

            self.search_matches = []
            self.search_index = -1
            self.search_query = None

            self.update_search_status(
                "Enter a key or value."
            )

            return False

        if query != self.search_query:

            self.search_matches = self.find_nodes(
                key,
                value
            )

            self.search_query = query
            self.search_index = -1

            if not self.search_matches:

                self.update_search_status(
                    "Nothing found."
                )

                return False

            self.update_search_status(
                f"Found {len(self.search_matches)} items."
            )

        return bool(self.search_matches)

    # -----------------------------------------
    # SEARCH NEXT
    # -----------------------------------------

    def find_next(self):

        if not self.prepare_search():
            return

        self.search_index += 1

        if self.search_index >= len(self.search_matches):
            self.search_index = 0

        self.select_search_result()

    # -----------------------------------------
    # SEARCH PREVIOUS
    # -----------------------------------------

    def find_previous(self):

        if not self.prepare_search():
            return

        self.search_index -= 1

        if self.search_index < 0:
            self.search_index = len(self.search_matches) - 1

        self.select_search_result()

    # -----------------------------------------
    # SELECT SEARCH RESULT
    # -----------------------------------------

    def select_search_result(self):

        iid = self.search_matches[self.search_index]

        parent = self.tree_view.parent(iid)

        while parent:

            self.tree_view.item(
                parent,
                open=True
            )

            parent = self.tree_view.parent(parent)

        self.tree_view.selection_set(iid)

        self.tree_view.focus(iid)

        self.tree_view.see(iid)

        self.tree_view.focus_set()

        self.show_properties(
            self.node_by_iid[iid],
            iid
        )

        self.update_search_status(
            f"Found {self.search_index + 1} "
            f"of {len(self.search_matches)}"
        )

        if self.search_window is not None:
            self.search_window.lift()

    def update_search_status(self, message):

        if (
            self.search_message is not None
            and self.search_message.winfo_exists()
        ):

            self.search_message.configure(
                text=message
            )

    # -----------------------------------------
    # TREE CONTROLS
    # -----------------------------------------

    def expand_all(self):

        def expand(parent):

            for item in self.tree_view.get_children(parent):

                self.tree_view.item(
                    item,
                    open=True
                )

                expand(item)

        expand("")

    def collapse_all(self):

        def collapse(parent):

            for item in self.tree_view.get_children(parent):

                collapse(item)

                self.tree_view.item(
                    item,
                    open=False
                )

        collapse("")


# ---------------------------------------------
# APPLICATION
# ---------------------------------------------

if __name__ == "__main__":

    root = TkinterDnD.Tk()

    app = VMFExplorer(root)

    root.mainloop()
