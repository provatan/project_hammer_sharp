
import math
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from PIL import Image, ImageTk, ImageDraw
from tkinterdnd2 import DND_FILES

from vtf.reader import VTFReader


class VTViewer:

    def __init__(self, root, filepath=None):

        self.root = root

        self.root.title("VTF Viewer")
        self.root.geometry("1100x750")
        self.root.minsize(700, 450)
        self.root.configure(bg="#202020")

        # ---------------------------------------------
        # DATA
        # ---------------------------------------------

        self.file_path = None
        self.image = None
        self.photo = None

        self.scale = 1.0

        self.offset_x = 0
        self.offset_y = 0

        self.drag_start = None
        self.checkerboard = True
        self.repeat_images = False
        self.repeat = False
        self.repeat_var = None
        self._repeat_photo = None

        self.bg = "#202020"
        self.panel_bg = "#292929"
        self.canvas_bg = "#151515"
        self.fg = "#dddddd"
        self.muted = "#999999"
        self.accent = "#3979b8"

        # ---------------------------------------------
        # INTERFACE
        # ---------------------------------------------

        self.create_menu()
        self.create_interface()
        self.create_bindings()

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.close_application
        )

        if filepath:
            self.open_file(filepath)

    # ---------------------------------------------
    # MENU
    # ---------------------------------------------

    def create_menu(self):

        menu = tk.Menu(
            self.root,
            bg=self.panel_bg,
            fg=self.fg,
            activebackground=self.accent,
            activeforeground="white",
            tearoff=False
        )

        file_menu = tk.Menu(
            menu,
            tearoff=False,
            bg=self.panel_bg,
            fg=self.fg
        )

        file_menu.add_command(
            label="Открыть",
            accelerator="Ctrl+O",
            command=self.open_dialog
        )

        file_menu.add_command(
            label="Закрыть",
            accelerator="Ctrl+W",
            command=self.close_file
        )

        file_menu.add_separator()

        file_menu.add_command(
            label="Выход",
            command=self.close_application
        )

        menu.add_cascade(
            label="Файл",
            menu=file_menu
        )

        view_menu = tk.Menu(
            menu,
            tearoff=False,
            bg=self.panel_bg,
            fg=self.fg
        )

        view_menu.add_command(
            label="Масштаб 100%",
            command=self.zoom_100
        )

        view_menu.add_command(
            label="Вписать изображение",
            command=self.fit_image
        )

        view_menu.add_separator()

        self.repeat_var = tk.BooleanVar(
            self.root,
            value=False
        )

        view_menu.add_checkbutton(
            label="Повторять изображения",
            variable=self.repeat_var,
            command=self.toggle_repeat
        )

        view_menu.add_command(
            label="Шахматный фон",
            command=self.toggle_checkerboard
        )

        menu.add_cascade(
            label="Вид",
            menu=view_menu
        )

        self.root.config(menu=menu)

    # ---------------------------------------------
    # INTERFACE
    # ---------------------------------------------

    def create_interface(self):

        main = tk.Frame(
            self.root,
            bg=self.bg
        )

        main.pack(
            fill="both",
            expand=True
        )

        main.grid_rowconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=1)

        # ---------------------------------------------
        # SIDEBAR
        # ---------------------------------------------

        self.sidebar = tk.Frame(
            main,
            bg=self.panel_bg,
            width=245
        )

        self.sidebar.grid(
            row=0,
            column=0,
            sticky="ns"
        )

        self.sidebar.grid_propagate(False)

        self.create_sidebar()

        # ---------------------------------------------
        # CANVAS
        # ---------------------------------------------

        self.canvas = tk.Canvas(
            main,
            bg=self.canvas_bg,
            highlightthickness=0
        )

        self.canvas.grid(
            row=0,
            column=1,
            sticky="nsew"
        )

        self.draw_empty()

        # ---------------------------------------------
        # STATUS
        # ---------------------------------------------

        self.status = tk.Label(
            self.root,
            text="Готово",
            bg="#252525",
            fg=self.muted,
            anchor="w",
            padx=10,
            pady=4
        )

        self.status.pack(
            fill="x",
            side="bottom"
        )


    # ---------------------------------------------
    # SIDEBAR
    # ---------------------------------------------

    def create_sidebar(self):

        # Контейнер боковой панели
        self.right_side = tk.Frame(
            self.sidebar,
            bg=self.panel_bg
        )

        self.right_side.pack(
            fill="both",
            expand=True
        )

        self.right_side.grid_rowconfigure(0, weight=1)
        self.right_side.grid_columnconfigure(0, weight=1)

        # Canvas для прокрутки
        self.sidebar_canvas = tk.Canvas(
            self.right_side,
            bg=self.panel_bg,
            highlightthickness=0,
            borderwidth=0
        )

        self.sidebar_canvas.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        # Scrollbar
        self.sidebar_scrollbar = ttk.Scrollbar(
            self.right_side,
            orient="vertical",
            command=self.sidebar_canvas.yview
        )

        self.sidebar_scrollbar.grid(
            row=0,
            column=1,
            sticky="ns"
        )

        self.sidebar_canvas.configure(
            yscrollcommand=self.sidebar_scrollbar.set
        )

        # Внутренняя панель с элементами
        self.sidebar_content = tk.Frame(
            self.sidebar_canvas,
            bg=self.panel_bg
        )

        self.sidebar_window = self.sidebar_canvas.create_window(
            (0, 0),
            window=self.sidebar_content,
            anchor="nw"
        )

        # Обновление области прокрутки
        self.sidebar_content.bind(
            "<Configure>",
            self.update_sidebar_scroll
        )

        # Подгонка ширины внутренней панели
        self.sidebar_canvas.bind(
            "<Configure>",
            self.resize_sidebar_content
        )

        # Прокрутка колёсиком
        self.sidebar_canvas.bind(
            "<Enter>",
            self.bind_sidebar_mousewheel
        )

        self.sidebar_canvas.bind(
            "<Leave>",
            self.unbind_sidebar_mousewheel
        )

        # ---------------------------------------------
        # FILE
        # ---------------------------------------------

        self.add_section("ФАЙЛ")

        self.file_label = self.add_info("Файл", "-")
        self.version_label = self.add_info("Версия", "-")
        self.size_label = self.add_info("Размер файла", "-")

        # ---------------------------------------------
        # IMAGE
        # ---------------------------------------------

        self.add_section("ИЗОБРАЖЕНИЕ")

        self.resolution_label = self.add_info("Разрешение", "-")
        self.format_label = self.add_info("Формат", "-")
        self.frames_label = self.add_info("Кадры", "-")

        self.image_state_label = self.add_info(
            "Состояние изображения",
            "Не загружено"
        )

        self.mipmaps_label = self.add_info("MipMaps", "-")
        self.depth_label = self.add_info("Глубина", "-")

        # ---------------------------------------------
        # VIEW
        # ---------------------------------------------

        self.add_section("ПРОСМОТР")

        self.zoom_label = self.add_info("Масштаб", "100%")
        self.position_label = self.add_info("Позиция", "0, 0")

        # ---------------------------------------------
        # CONTROLS
        # ---------------------------------------------

        self.add_section("УПРАВЛЕНИЕ")

        self.add_button("Масштаб 100%", self.zoom_100)
        self.add_button("Вписать изображение", self.fit_image)
        self.add_button("Шахматный фон", self.toggle_checkerboard)


    # ---------------------------------------------
    # SIDEBAR SCROLL
    # ---------------------------------------------

    def update_sidebar_scroll(self, event=None):

        self.sidebar_canvas.configure(
            scrollregion=self.sidebar_canvas.bbox("all")
        )


    def resize_sidebar_content(self, event):

        self.sidebar_canvas.itemconfigure(
            self.sidebar_window,
            width=event.width
        )


    def bind_sidebar_mousewheel(self, event=None):

        self.sidebar_canvas.bind_all(
            "<MouseWheel>",
            self.on_sidebar_mousewheel
        )


    def unbind_sidebar_mousewheel(self, event=None):

        self.sidebar_canvas.unbind_all(
            "<MouseWheel>"
        )


    def on_sidebar_mousewheel(self, event):

        self.sidebar_canvas.yview_scroll(
            -int(event.delta / 120),
            "units"
        )


    # ---------------------------------------------
    # SIDEBAR ELEMENTS
    # ---------------------------------------------

    def add_section(self, text):

        tk.Label(
            self.sidebar_content,
            text=text,
            bg=self.panel_bg,
            fg="#75a9df",
            font=("Segoe UI", 9, "bold"),
            anchor="w",
            padx=12,
            pady=12
        ).pack(
            fill="x"
        )

        ttk.Separator(
            self.sidebar_content,
            orient="horizontal"
        ).pack(
            fill="x",
            padx=10
        )


    def add_info(self, title, value):

        frame = tk.Frame(
            self.sidebar_content,
            bg=self.panel_bg
        )

        frame.pack(
            fill="x",
            padx=12,
            pady=3
        )

        tk.Label(
            frame,
            text=title,
            bg=self.panel_bg,
            fg=self.muted,
            font=("Segoe UI", 9),
            anchor="w"
        ).pack(
            fill="x"
        )

        label = tk.Label(
            frame,
            text=value,
            bg=self.panel_bg,
            fg=self.fg,
            font=("Segoe UI", 10),
            anchor="w"
        )

        label.pack(
            fill="x"
        )

        return label


    def add_button(self, text, command):

        tk.Button(
            self.sidebar_content,
            text=text,
            command=command,
            bg="#383838",
            fg=self.fg,
            activebackground=self.accent,
            activeforeground="white",
            relief="flat",
            padx=8,
            pady=6
        ).pack(
            fill="x",
            padx=12,
            pady=3
        )

    # ---------------------------------------------
    # BINDINGS
    # ---------------------------------------------

    def create_bindings(self):

        self.root.bind(
            "<Control-o>",
            lambda event: self.open_dialog()
        )

        self.root.bind(
            "<Control-w>",
            lambda event: self.close_file()
        )

        self.canvas.bind(
            "<MouseWheel>",
            self.on_zoom
        )

        self.canvas.bind(
            "<Button-3>",
            self.on_drag_start
        )

        self.canvas.bind(
            "<B3-Motion>",
            self.on_drag
        )

        self.canvas.bind(
            "<ButtonRelease-3>",
            self.on_drag_stop
        )

        self.canvas.bind(
            "<Configure>",
            lambda event: self.redraw()
        )

        self.root.drop_target_register(DND_FILES)

        self.root.dnd_bind(
            "<<Drop>>",
            self.on_drop
        )

    # ---------------------------------------------
    # DRAG & DROP
    # ---------------------------------------------

    def on_drop(self, event):

        files = self.root.tk.splitlist(event.data)

        if files:
            self.open_file(files[0])

    # ---------------------------------------------
    # OPEN
    # ---------------------------------------------

    def open_dialog(self):

        filepath = filedialog.askopenfilename(
            title="Открыть VTF",
            filetypes=[
                ("Valve Texture Format", "*.vtf"),
                ("Все файлы", "*.*")
            ]
        )

        if filepath:
            self.open_file(filepath)

    def open_file(self, filepath):

        if not os.path.isfile(filepath):
            return

        if not filepath.lower().endswith(".vtf"):
            messagebox.showerror(
                "Ошибка",
                "Поддерживаются только VTF-файлы."
            )
            return

        try:

            reader = VTFReader(filepath)
            image, info = reader.read()

        except Exception as error:

            messagebox.showerror(
                "Ошибка чтения VTF",
                str(error)
            )

            return

        self.file_path = filepath
        self.image = image

        self.update_information(info)

        self.root.title(
            f"VTF Viewer - {os.path.basename(filepath)}"
        )

        if image is not None:
            self.fit_image()
        else:
            self.redraw()

        image_error = info.get("image_error")
        if image_error:
            self.status.config(
                text=f"Файл открыт. Изображение: {image_error}"
            )
        else:
            self.status.config(
                text=f"Открыт: {filepath}"
            )

    # ---------------------------------------------
    # INFORMATION
    # ---------------------------------------------

    def update_information(self, info):

        self.file_label.config(
            text=os.path.basename(self.file_path)
        )

        self.version_label.config(
            text=f'{info["major"]}.{info["minor"]}'
        )

        self.size_label.config(
            text=f'{info["file_size"] / 1024:.1f} KB'
        )

        self.resolution_label.config(
            text=f'{info["width"]} × {info["height"]}'
        )

        self.format_label.config(
            text=info["format_name"]
        )

        self.frames_label.config(
            text=str(info["frames"])
        )

        self.mipmaps_label.config(
            text=str(info["mipmaps"])
        )

        self.depth_label.config(
            text=str(info["depth"])
        )
        
        self.image_state_label.config(
            text=(
                "Загружено"
                if self.image is not None
                else "Нет изображения"
            )
        )

    # ---------------------------------------------
    # EMPTY VIEW
    # ---------------------------------------------

    def draw_empty(self):
        self.canvas.delete("empty")
        self.redraw()

    # ---------------------------------------------
    # CHECKERBOARD
    # ---------------------------------------------

    def draw_checkerboard(self):

        self.canvas.delete("checker")

        if not self.checkerboard or self.image is None:
            return

        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()

        if width <= 1 or height <= 1:
            return

        size = 16

        colors = (
            "#282828",
            "#383838"
        )

        cache_key = (
            width,
            height,
            size,
            colors
        )

        # Создаём фон только при изменении размеров
        if getattr(self, "_checker_cache_key", None) != cache_key:

            background = Image.new(
                "RGB",
                (width, height),
                colors[0]
            )

            draw = ImageDraw.Draw(background)

            for y in range(0, height, size):
                for x in range(0, width, size):

                    if ((x // size) + (y // size)) % 2:

                        draw.rectangle(
                            (
                                x,
                                y,
                                x + size - 1,
                                y + size - 1
                            ),
                            fill=colors[1]
                        )

            self._checker_photo = ImageTk.PhotoImage(background)
            self._checker_cache_key = cache_key

        self.canvas.create_image(
            0,
            0,
            image=self._checker_photo,
            anchor="nw",
            tags="checker"
        )

        self.canvas.tag_lower("checker")


    def toggle_checkerboard(self):

        self.checkerboard = not self.checkerboard

        self.redraw()

    def toggle_repeat(self):

        if self.repeat_var is not None:
            enabled = bool(self.repeat_var.get())
        else:
            enabled = not self.repeat_images

        self.repeat_images = enabled
        self.repeat = enabled

        self.redraw()

    # ---------------------------------------------
    # REDRAW
    # ---------------------------------------------

    def redraw(self):
        self.canvas.delete("image")
        self.canvas.delete("empty")

        self.draw_checkerboard()

        if self.image is None:
            if self.file_path is None:
                message = "Перетащите VTF сюда\nили нажмите Ctrl + O"
            else:
                message = "Изображение недоступно\nДанные VTF прочитаны"

            self.canvas.create_text(
                self.canvas.winfo_width() // 2,
                self.canvas.winfo_height() // 2,
                text=message,
                fill=self.muted,
                font=("Segoe UI", 14),
                justify="center",
                tags="empty"
            )

            return

        repeat_enabled = (
            getattr(self, "repeat_images", False)
            or getattr(self, "repeat", False)
        )

        if repeat_enabled:
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            if canvas_width > 1 and canvas_height > 1:
                if self.checkerboard:
                    base = Image.new(
                        "RGBA",
                        (canvas_width, canvas_height),
                        (56, 56, 56, 255)
                    )
                    draw = ImageDraw.Draw(base)
                    size = 16

                    for y in range(0, canvas_height, size):
                        for x in range(0, canvas_width, size):
                            if ((x // size) + (y // size)) % 2:
                                draw.rectangle(
                                    (
                                        x,
                                        y,
                                        min(x + size - 1, canvas_width - 1),
                                        min(y + size - 1, canvas_height - 1)
                                    ),
                                    fill=(32, 32, 32, 255)
                                )
                else:
                    base = Image.new(
                        "RGBA",
                        (canvas_width, canvas_height),
                        (21, 21, 21, 255)
                    )

                scale = max(0.001, self.scale)
                tile_width = max(1, round(self.image.width * scale))
                tile_height = max(1, round(self.image.height * scale))
                resized = self.image.resize(
                    (tile_width, tile_height),
                    Image.Resampling.BILINEAR
                ).convert("RGBA")

                first_x = math.floor(-self.offset_x / tile_width)
                last_x = math.ceil((canvas_width - self.offset_x) / tile_width)
                first_y = math.floor(-self.offset_y / tile_height)
                last_y = math.ceil((canvas_height - self.offset_y) / tile_height)

                for tile_y in range(first_y, last_y):
                    y = round(self.offset_y + tile_y * tile_height)

                    for tile_x in range(first_x, last_x):
                        x = round(self.offset_x + tile_x * tile_width)
                        base.paste(
                            resized,
                            (x, y),
                            resized.getchannel("A")
                        )

                self._repeat_photo = ImageTk.PhotoImage(base)
                self.canvas.create_image(
                    0,
                    0,
                    image=self._repeat_photo,
                    anchor="nw",
                    tags="image"
                )

            self.zoom_label.config(
                text=f"{self.scale * 100:.1f}%"
            )
            self.position_label.config(
                text=f"{self.offset_x:.0f}, {self.offset_y:.0f}"
            )

            return

        scale = max(0.001, self.scale)

        image_width = self.image.width
        image_height = self.image.height

        width = round(image_width * scale)
        height = round(image_height * scale)

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        # Видимая часть изображения в исходных координатах
        left = max(0, int(-self.offset_x / scale))
        top = max(0, int(-self.offset_y / scale))

        right = min(
            image_width,
            int((canvas_width - self.offset_x) / scale) + 1
        )

        bottom = min(
            image_height,
            int((canvas_height - self.offset_y) / scale) + 1
        )

        # Изображение полностью за пределами окна
        if right <= left or bottom <= top:
            self.canvas.create_rectangle(
                self.offset_x,
                self.offset_y,
                self.offset_x + width,
                self.offset_y + height,
                outline="#777777",
                width=1,
                tags="image"
            )
            return

        # Вырезаем только видимую часть
        cropped = self.image.crop(
            (left, top, right, bottom)
        )

        resized = cropped.resize(
            (
                max(1, round(cropped.width * scale)),
                max(1, round(cropped.height * scale))
            ),
            Image.Resampling.BILINEAR
        )

        self.photo = ImageTk.PhotoImage(resized)

        self.canvas.create_image(
            self.offset_x + left * scale,
            self.offset_y + top * scale,
            image=self.photo,
            anchor="nw",
            tags="image"
        )

        self.canvas.create_rectangle(
            self.offset_x,
            self.offset_y,
            self.offset_x + width,
            self.offset_y + height,
            outline="#777777",
            width=1,
            tags="image"
        )

        self.zoom_label.config(
            text=f"{self.scale * 100:.1f}%"
        )

        self.position_label.config(
            text=f"{self.offset_x:.0f}, {self.offset_y:.0f}"
        )

    # ---------------------------------------------
    # ZOOM
    # ---------------------------------------------

    def on_zoom(self, event):

        if self.image is None:
            return

        factor = 1.15 if event.delta > 0 else 1 / 1.15

        mouse_x = event.x
        mouse_y = event.y

        old_scale = self.scale

        new_scale = max(
            0.02,
            min(20.0, old_scale * factor)
        )

        if old_scale == new_scale:
            return

        ratio = new_scale / old_scale

        self.offset_x = (
            mouse_x - (mouse_x - self.offset_x) * ratio
        )

        self.offset_y = (
            mouse_y - (mouse_y - self.offset_y) * ratio
        )

        self.scale = new_scale

        self.redraw()

    # ---------------------------------------------
    # RIGHT MOUSE DRAG
    # ---------------------------------------------

    def on_drag_start(self, event):

        self.drag_start = (
            event.x,
            event.y,
            self.offset_x,
            self.offset_y
        )

    def on_drag(self, event):

        if self.drag_start is None:
            return

        sx, sy, ox, oy = self.drag_start

        self.offset_x = ox + event.x - sx
        self.offset_y = oy + event.y - sy

        self.redraw()

    def on_drag_stop(self, event):

        self.drag_start = None

    # ---------------------------------------------
    # VIEW CONTROLS
    # ---------------------------------------------

    def zoom_100(self):

        if self.image is None:
            return

        self.canvas.update_idletasks()

        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()

        self.scale = 1.0

        # Центрируем изображение
        self.offset_x = (
            width - self.image.width
        ) / 2

        self.offset_y = (
            height - self.image.height
        ) / 2

        self.redraw()


    def fit_image(self):

        if self.image is None:
            return

        self.canvas.update_idletasks()

        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()

        if width <= 1 or height <= 1:
            return

        scale_x = width / self.image.width
        scale_y = height / self.image.height

        self.scale = min(scale_x, scale_y) * 0.95

        self.offset_x = (
            width - self.image.width * self.scale
        ) / 2

        self.offset_y = (
            height - self.image.height * self.scale
        ) / 2

        self.redraw()

    # ---------------------------------------------
    # CLOSE FILE
    # ---------------------------------------------

    def close_file(self):

        self.file_path = None
        self.image = None
        self.photo = None

        self.scale = 1.0

        self.offset_x = 0
        self.offset_y = 0

        self.canvas.delete("all")

        self.draw_empty()

        self.root.title("VTF Viewer")

        for label in (
            self.file_label,
            self.version_label,
            self.size_label,
            self.resolution_label,
            self.format_label,
            self.frames_label,
            self.mipmaps_label,
            self.depth_label
        ):
            label.config(text="-")

        self.zoom_label.config(text="100%")
        self.position_label.config(text="0, 0")

        self.status.config(text="Файл закрыт")

    # ---------------------------------------------
    # APPLICATION
    # ---------------------------------------------

    def close_application(self):

        self.root.destroy()
