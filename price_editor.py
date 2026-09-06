import logging
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from bot.config import validate_config
from bot.editor import (
    BAD_AMOUNT,
    BAD_PRICE,
    EMPTY_TITLE,
    RUSSIAN_IN_ENGLISH,
    apply_price_changes,
    collect_price_changes,
    format_counter,
    matches_filter,
    should_scroll_inner,
    title_column_width,
    validate_lot_form,
)
from bot.lots import (
    LOT_FIELD_LABELS,
    fetch_lot_fields,
    read_lot_values,
    save_lot_values,
    strip_broken_surrogates,
)
from bot.main import create_account
from bot.pricing import format_price, load_lots

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)

BG = "#eef1f6"
CARD = "#ffffff"
ROW_ALT = "#f7f9fc"
BORDER = "#dfe4ec"
TEXT = "#1f2329"
MUTED = "#6b7280"
ACCENT = "#2f6fed"
ACCENT_DARK = "#2559c4"
DANGER = "#c0392b"

TITLE_MIN_WIDTH = 320
PRICE_WIDTH = 96
NEW_PRICE_WIDTH = 118
ACTION_WIDTH = 120
COLUMNS_WIDTH = PRICE_WIDTH + NEW_PRICE_WIDTH + ACTION_WIDTH
ROW_PADDING = 24
ROW_HEIGHT = 30
RESIZE_DEBOUNCE_MS = 160
PREVIEW_HEIGHT = 26

SINGLE_LINE_FIELDS = ("title_ru", "title_en")
MULTI_LINE_FIELDS = (
    "description_ru",
    "description_en",
    "payment_msg_ru",
    "payment_msg_en",
)

try:
    from PIL import ImageTk

    from bot.emoji_text import hex_to_rgb, load_fonts, render_text_image

    EMOJI_FONTS = load_fonts()
except Exception as emoji_error:
    logging.getLogger(__name__).warning(
        "Цветные эмодзи недоступны (%s), названия будут обычным текстом.",
        emoji_error,
    )
    EMOJI_FONTS = None


def run_async(root, work, on_done):
    def runner():
        try:
            result = work()
        except Exception as error:
            root.after(0, lambda exc=error: on_done(None, exc))
        else:
            root.after(0, lambda value=result: on_done(value, None))

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    return thread


def setup_styles(root):
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".", font=("Segoe UI", 10), background=BG, foreground=TEXT)
    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=CARD)
    style.configure("Row.TFrame", background=CARD)
    style.configure("RowAlt.TFrame", background=ROW_ALT)

    style.configure("TLabel", background=BG, foreground=TEXT)
    style.configure("Card.TLabel", background=CARD, foreground=TEXT)
    style.configure("Muted.TLabel", background=CARD, foreground=MUTED)
    style.configure(
        "Header.TLabel",
        background=BG,
        foreground=MUTED,
        font=("Segoe UI", 9, "bold"),
    )
    style.configure(
        "Section.TLabel",
        background=CARD,
        foreground=MUTED,
        font=("Segoe UI", 9, "bold"),
    )
    style.configure("Row.TLabel", background=CARD, foreground=TEXT)
    style.configure("RowAlt.TLabel", background=ROW_ALT, foreground=TEXT)
    style.configure(
        "Price.TLabel",
        background=CARD,
        foreground=MUTED,
        font=("Segoe UI", 10),
    )
    style.configure(
        "PriceAlt.TLabel",
        background=ROW_ALT,
        foreground=MUTED,
        font=("Segoe UI", 10),
    )

    style.configure(
        "TButton",
        background="#e8ecf3",
        foreground=TEXT,
        borderwidth=0,
        focuscolor=BG,
        padding=(14, 7),
    )
    style.map(
        "TButton",
        background=[("active", "#dbe2ee"), ("disabled", "#f0f2f6")],
        foreground=[("disabled", "#a9b0bd")],
    )

    style.configure(
        "Accent.TButton",
        background=ACCENT,
        foreground="#ffffff",
        borderwidth=0,
        padding=(16, 7),
    )
    style.map(
        "Accent.TButton",
        background=[("active", ACCENT_DARK), ("disabled", "#b6c7ee")],
        foreground=[("disabled", "#eef2fb")],
    )

    style.configure(
        "Small.TButton",
        background="#eef1f6",
        foreground=ACCENT,
        borderwidth=0,
        padding=(10, 4),
        font=("Segoe UI", 9),
    )
    style.map("Small.TButton", background=[("active", "#dde4f1")])

    style.configure(
        "TEntry",
        fieldbackground=CARD,
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
        borderwidth=1,
        padding=5,
    )
    style.configure("TCheckbutton", background=CARD, foreground=TEXT)
    style.map("TCheckbutton", background=[("active", CARD)])
    style.configure(
        "Vertical.TScrollbar",
        background="#cfd6e2",
        troughcolor=BG,
        borderwidth=0,
        arrowsize=12,
    )

    return style


def fixed_cell(parent, width, height, background):
    cell = tk.Frame(
        parent, width=width, height=height, background=background, bd=0
    )
    cell.pack_propagate(False)
    cell.pack(side="left")
    return cell


def make_scrollable(parent, background):
    canvas = tk.Canvas(
        parent, highlightthickness=0, background=background, bd=0
    )
    scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    inner = ttk.Frame(canvas, style="Card.TFrame")

    window = canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    inner.bind(
        "<Configure>",
        lambda _: canvas.configure(scrollregion=canvas.bbox("all")),
    )
    canvas.bind(
        "<Configure>",
        lambda event: canvas.itemconfigure(window, width=event.width),
    )

    def on_wheel(event):
        canvas.yview_scroll(int(-event.delta / 120), "units")

    canvas.bind("<Enter>", lambda _: canvas.bind_all("<MouseWheel>", on_wheel))
    canvas.bind("<Leave>", lambda _: canvas.unbind_all("<MouseWheel>"))

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    return inner


class LotDialog(tk.Toplevel):
    def __init__(self, parent, acc, lot, on_saved):
        super().__init__(parent)

        self.acc = acc
        self.lot = lot
        self.on_saved = on_saved
        self.widgets = {}
        self.previews = {}
        self.preview_jobs = {}
        self._healing = False

        title = lot.title or f"Лот {lot.id}"
        self.title(f"Редактирование лота — {title[:60]}")
        self.geometry("1000x820")
        self.minsize(760, 560)
        self.configure(background=BG)
        self.grab_set()

        head = ttk.Frame(self, style="Card.TFrame", padding=(16, 12))
        head.pack(fill="x")
        self.status = tk.StringVar(value="Загружаю поля лота...")
        ttk.Label(
            head,
            textvariable=self.status,
            style="Muted.TLabel",
            font=("Segoe UI", 10),
        ).pack(anchor="w")

        body = ttk.Frame(self, style="Card.TFrame", padding=(16, 10))
        body.pack(fill="both", expand=True, padx=12, pady=10)
        self.form = make_scrollable(body, CARD)

        buttons = ttk.Frame(self, padding=(16, 10))
        buttons.pack(fill="x")
        self.save_button = ttk.Button(
            buttons, text="Сохранить", style="Accent.TButton",
            command=self.save, state="disabled",
        )
        self.save_button.pack(side="right")
        ttk.Button(buttons, text="Отмена", command=self.destroy).pack(
            side="right", padx=8
        )

        run_async(self, self._load, self._on_loaded)

    def _load(self):
        fields = fetch_lot_fields(self.acc, self.lot)
        return read_lot_values(fields), fields

    def _on_loaded(self, result, error):
        if error is not None:
            self.status.set("Не удалось загрузить лот")
            messagebox.showerror("Ошибка", str(error), parent=self)
            return

        values, fields = result
        self._build_form(values, fields)
        self.status.set(f"Лот id={self.lot.id}")
        self.save_button.configure(state="normal")

    def _build_form(self, values, fields):
        for name in SINGLE_LINE_FIELDS:
            ttk.Label(
                self.form,
                text=LOT_FIELD_LABELS[name],
                style="Section.TLabel",
            ).pack(anchor="w", pady=(6, 3))
            var = tk.StringVar(value=values.get(name, ""))
            ttk.Entry(self.form, textvariable=var).pack(fill="x", pady=(0, 2))
            self.widgets[name] = var
            var.trace_add("write", lambda *_, v=var: self._heal_surrogates(v))
            self._add_preview(name, var)

        for name in MULTI_LINE_FIELDS:
            ttk.Label(
                self.form,
                text=LOT_FIELD_LABELS[name],
                style="Section.TLabel",
            ).pack(anchor="w", pady=(6, 3))
            text = tk.Text(
                self.form,
                height=6,
                wrap="word",
                font=("Segoe UI", 10),
                background=CARD,
                foreground=TEXT,
                relief="solid",
                borderwidth=1,
                highlightthickness=0,
                padx=6,
                pady=5,
            )
            text.configure(highlightbackground=BORDER)
            text.insert("1.0", values.get(name, ""))
            text.pack(fill="x", pady=(0, 6))
            text.bind("<MouseWheel>", self._scroll_text)
            self.widgets[name] = text

        numbers = ttk.Frame(self.form, style="Card.TFrame")
        numbers.pack(fill="x", pady=(10, 6))

        ttk.Label(numbers, text="Цена", style="Section.TLabel").pack(
            side="left"
        )
        self.price_var = tk.StringVar(value=format_price(fields.price))
        ttk.Entry(numbers, textvariable=self.price_var, width=12).pack(
            side="left", padx=(8, 24)
        )

        ttk.Label(
            numbers, text="Количество", style="Section.TLabel"
        ).pack(side="left")
        self.amount_var = tk.StringVar(
            value="" if fields.amount is None else str(fields.amount)
        )
        ttk.Entry(numbers, textvariable=self.amount_var, width=12).pack(
            side="left", padx=(8, 24)
        )

        self.active_var = tk.BooleanVar(value=fields.active)
        ttk.Checkbutton(
            numbers, text="Активен", variable=self.active_var
        ).pack(side="left")

    def _scroll_text(self, event):
        text = event.widget
        first, last = text.yview()

        if not should_scroll_inner(first, last, event.delta):
            return None

        text.yview_scroll(int(-event.delta / 120), "units")
        return "break"

    def _heal_surrogates(self, var):
        if self._healing:
            return

        value = var.get()
        clean = strip_broken_surrogates(value)

        if clean == value:
            return

        self._healing = True
        try:
            var.set(clean)
        finally:
            self._healing = False

    def _add_preview(self, name, var):
        if EMOJI_FONTS is None:
            return

        label = tk.Label(self.form, background=CARD, bd=0, anchor="w")
        label.pack(fill="x", pady=(0, 6))
        label.drawn_width = 0
        self.previews[name] = label

        var.trace_add("write", lambda *_: self._schedule_preview(name, var))
        label.bind("<Configure>", lambda _: self._schedule_preview(name, var))
        self._draw_preview(name, var)

    def _schedule_preview(self, name, var):
        job = self.preview_jobs.get(name)

        if job is not None:
            self.after_cancel(job)

        self.preview_jobs[name] = self.after(
            RESIZE_DEBOUNCE_MS, lambda: self._draw_preview(name, var)
        )

    def _draw_preview(self, name, var):
        self.preview_jobs.pop(name, None)
        label = self.previews.get(name)

        if label is None:
            return

        width = max(label.winfo_width(), 400)

        drawn_text = getattr(label, "drawn_text", None)

        if width == label.drawn_width and var.get() == drawn_text:
            return

        label.drawn_width = width
        label.drawn_text = var.get()

        image = render_text_image(
            var.get(),
            EMOJI_FONTS,
            hex_to_rgb(TEXT),
            hex_to_rgb(CARD),
            width,
            PREVIEW_HEIGHT,
        )
        photo = ImageTk.PhotoImage(image)
        label.configure(image=photo)
        label.image = photo

    def _collect_values(self):
        values = {}

        for name, widget in self.widgets.items():
            if isinstance(widget, tk.Text):
                raw = widget.get("1.0", "end-1c")
            else:
                raw = widget.get()

            values[name] = strip_broken_surrogates(raw)

        return values

    def _show_validation_error(self, kind, fields):
        if kind == EMPTY_TITLE:
            messagebox.showerror(
                "Пустое название",
                "Название (RU) не может быть пустым.",
                parent=self,
            )
        elif kind == RUSSIAN_IN_ENGLISH:
            messagebox.showerror(
                "Русские буквы в английской версии",
                "Уберите русские буквы из полей:\n\n"
                + "\n".join(LOT_FIELD_LABELS[name] for name in fields),
                parent=self,
            )
        elif kind == BAD_PRICE:
            messagebox.showerror(
                "Некорректная цена",
                "Цена должна быть положительным числом.",
                parent=self,
            )
        elif kind == BAD_AMOUNT:
            messagebox.showerror(
                "Некорректное количество",
                "Количество должно быть целым числом (или пустым).",
                parent=self,
            )

    def save(self):
        values = self._collect_values()
        price, amount, error = validate_lot_form(
            values, self.price_var.get(), self.amount_var.get()
        )

        if error is not None:
            self._show_validation_error(*error)
            return

        active = self.active_var.get()

        self.save_button.configure(state="disabled")
        self.status.set("Сохраняю...")

        run_async(
            self,
            lambda: save_lot_values(
                self.acc, self.lot, values, price, amount, active
            ),
            self._on_saved,
        )

    def _on_saved(self, _result, error):
        if error is not None:
            self.status.set("Ошибка сохранения")
            self.save_button.configure(state="normal")
            messagebox.showerror("Ошибка", str(error), parent=self)
            return

        messagebox.showinfo("Готово", "Лот сохранён.", parent=self)
        self.on_saved()
        self.destroy()


class PriceEditor:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.acc = None
        self.rows = []

        root.title("Редактор лотов FunPay")
        root.geometry("1180x720")
        root.configure(background=BG)
        setup_styles(root)

        toolbar = ttk.Frame(root, style="Card.TFrame", padding=(16, 12))
        toolbar.pack(fill="x", padx=12, pady=(12, 0))

        ttk.Label(toolbar, text="Поиск", style="Section.TLabel").pack(
            side="left"
        )
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", lambda *_: self._apply_filter())
        ttk.Entry(toolbar, textvariable=self.filter_var, width=38).pack(
            side="left", padx=(8, 20)
        )

        self.save_button = ttk.Button(
            toolbar, text="Сохранить цены", style="Accent.TButton",
            command=self.save_changes,
        )
        self.save_button.pack(side="right")

        self.reload_button = ttk.Button(
            toolbar, text="Обновить", command=self.reload_lots
        )
        self.reload_button.pack(side="right", padx=8)

        self.counter = tk.StringVar(value="")
        ttk.Label(
            toolbar, textvariable=self.counter, style="Muted.TLabel"
        ).pack(side="right", padx=12)

        header = tk.Frame(root, background=BG)
        header.pack(fill="x", padx=25, pady=(12, 6))

        self.header_title_cell = fixed_cell(header, TITLE_MIN_WIDTH, 18, BG)
        ttk.Label(
            self.header_title_cell,
            text="ЛОТ",
            style="Header.TLabel",
            anchor="w",
        ).pack(fill="both", expand=True)

        for text, width, anchor in (
            ("ЦЕНА", PRICE_WIDTH, "e"),
            ("НОВАЯ ЦЕНА", NEW_PRICE_WIDTH, "center"),
        ):
            cell = fixed_cell(header, width, 18, BG)
            ttk.Label(
                cell, text=text, style="Header.TLabel", anchor=anchor
            ).pack(fill="both", expand=True)

        container = ttk.Frame(root, style="Card.TFrame", padding=1)
        container.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self.inner = make_scrollable(container, CARD)

        self.title_width = TITLE_MIN_WIDTH
        self._resize_job = None
        self.inner.bind("<Configure>", self._on_resize)

        footer = ttk.Frame(root, style="Card.TFrame", padding=(16, 10))
        footer.pack(fill="x", padx=12, pady=(0, 12))
        self.status = tk.StringVar(value="Подключаюсь к FunPay...")
        ttk.Label(footer, textvariable=self.status, style="Muted.TLabel").pack(
            side="left"
        )

        self._set_busy(True)
        run_async(self.root, self._connect, self._on_connected)

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.reload_button.configure(state=state)
        self.save_button.configure(state=state)

    def _connect(self):
        validate_config()
        self.acc = create_account()
        return load_lots(self.acc)

    def _on_connected(self, lots, error) -> None:
        if error is not None:
            self.status.set(f"Ошибка подключения: {error}")
            messagebox.showerror(
                "Ошибка", f"Не удалось подключиться:\n{error}"
            )
            self._set_busy(False)
            return

        self.status.set(f"Авторизован как {self.acc.username}")
        self._render_lots(lots)
        self._set_busy(False)

    def reload_lots(self) -> None:
        self._set_busy(True)
        self.status.set("Загружаю лоты...")
        run_async(self.root, lambda: load_lots(self.acc), self._on_lots_loaded)

    def _on_lots_loaded(self, lots, error) -> None:
        if error is not None:
            self.status.set(f"Ошибка загрузки: {error}")
            messagebox.showerror(
                "Ошибка", f"Не удалось загрузить лоты:\n{error}"
            )
        else:
            self._render_lots(lots)
            self.status.set(f"Обновлено. Лотов: {len(lots)}")

        self._set_busy(False)

    def _on_resize(self, event) -> None:
        width = title_column_width(
            event.width, COLUMNS_WIDTH, ROW_PADDING, TITLE_MIN_WIDTH
        )

        if width == self.title_width:
            return

        self.title_width = width

        if self._resize_job is not None:
            self.root.after_cancel(self._resize_job)

        self._resize_job = self.root.after(
            RESIZE_DEBOUNCE_MS, self._relayout_titles
        )

    def _relayout_titles(self) -> None:
        self._resize_job = None
        self.header_title_cell.configure(width=self.title_width)

        for row in self.rows:
            row["title_cell"].configure(width=self.title_width)
            self._fill_title(
                row["title_label"], row["raw_title"], row["background"]
            )

    def _fill_title(self, label, title, background) -> None:
        if EMOJI_FONTS is None:
            label.configure(text=title, wraplength=self.title_width)
            return

        image = render_text_image(
            title,
            EMOJI_FONTS,
            hex_to_rgb(TEXT),
            hex_to_rgb(background),
            self.title_width,
            ROW_HEIGHT,
        )
        photo = ImageTk.PhotoImage(image)
        label.configure(image=photo)
        label.image = photo

    def _title_widget(self, parent, title, background):
        if EMOJI_FONTS is None:
            label = tk.Label(
                parent,
                text=title,
                background=background,
                foreground=TEXT,
                font=("Segoe UI", 10),
                anchor="w",
                bd=0,
            )
        else:
            label = tk.Label(parent, background=background, bd=0)

        self._fill_title(label, title, background)
        return label

    def _render_lots(self, lots) -> None:
        for child in self.inner.winfo_children():
            child.destroy()

        self.rows = []

        for index, lot in enumerate(lots):
            alt = index % 2 == 1
            background = ROW_ALT if alt else CARD
            price_style = "PriceAlt.TLabel" if alt else "Price.TLabel"

            row = tk.Frame(self.inner, background=background)
            row.pack(fill="x")

            title = lot.title or f"Лот {lot.id}"
            title_cell = fixed_cell(
                row, self.title_width, ROW_HEIGHT, background
            )
            title_label = self._title_widget(title_cell, title, background)
            title_label.pack(side="left", fill="both", expand=True)

            price_cell = fixed_cell(row, PRICE_WIDTH, ROW_HEIGHT, background)
            ttk.Label(
                price_cell,
                text=format_price(lot.price),
                style=price_style,
                anchor="e",
            ).pack(fill="both", expand=True, padx=(0, 14))

            var = tk.StringVar(value=format_price(lot.price))
            entry_cell = fixed_cell(
                row, NEW_PRICE_WIDTH, ROW_HEIGHT, background
            )
            ttk.Entry(entry_cell, textvariable=var, justify="center").pack(
                fill="x", padx=(0, 12), pady=3
            )

            action_cell = fixed_cell(row, ACTION_WIDTH, ROW_HEIGHT, background)
            ttk.Button(
                action_cell,
                text="Изменить",
                style="Small.TButton",
                command=lambda item=lot: self.open_lot(item),
            ).pack(side="left", pady=2)

            self.rows.append({
                "lot": lot,
                "frame": row,
                "var": var,
                "original": format_price(lot.price),
                "title": title.lower(),
                "raw_title": title,
                "title_cell": title_cell,
                "title_label": title_label,
                "background": background,
            })

        self.counter.set(f"Лотов: {len(lots)}")

    def open_lot(self, lot) -> None:
        if self.acc is None:
            return

        LotDialog(self.root, self.acc, lot, self.reload_lots)

    def _apply_filter(self) -> None:
        needle = self.filter_var.get()
        shown = 0

        for row in self.rows:
            if matches_filter(row["raw_title"], needle):
                row["frame"].pack(fill="x")
                shown += 1
            else:
                row["frame"].pack_forget()

        self.counter.set(format_counter(shown, len(self.rows)))

    def _collect_changes(self):
        entries = [
            (row, row["var"].get(), row["original"]) for row in self.rows
        ]
        changes, invalid_rows = collect_price_changes(entries)

        invalid = [
            row["lot"].title or row["lot"].id for row in invalid_rows
        ]

        return changes, invalid

    def save_changes(self) -> None:
        changes, invalid = self._collect_changes()

        if invalid:
            messagebox.showerror(
                "Некорректная цена",
                "Проверьте значения у лотов:\n"
                + "\n".join(str(i) for i in invalid),
            )
            return

        if not changes:
            messagebox.showinfo("Нет изменений", "Ни одна цена не изменена.")
            return

        if not messagebox.askyesno(
            "Подтверждение",
            f"Изменить цены у {len(changes)} лот(ов) на FunPay?",
        ):
            return

        self._set_busy(True)
        self.status.set(f"Сохраняю {len(changes)} лот(ов)...")
        run_async(self.root, lambda: self._save_all(changes), self._on_saved)

    def _save_all(self, changes):
        def on_progress(index, total):
            self.root.after(
                0,
                lambda i=index, t=total: self.status.set(
                    f"Сохраняю {i}/{t}..."
                ),
            )

        return apply_price_changes(
            self.acc,
            [(row, row["lot"], price) for row, price in changes],
            on_progress=on_progress,
        )

    def _on_saved(self, result, error) -> None:
        self._set_busy(False)

        if error is not None:
            self.status.set(f"Ошибка сохранения: {error}")
            messagebox.showerror("Ошибка", str(error))
            return

        saved, failed = result

        for row, price in saved:
            row["original"] = format_price(price)
            row["var"].set(format_price(price))

        self.status.set(f"Сохранено: {len(saved)}, ошибок: {len(failed)}")

        if failed:
            details = "\n".join(
                f"{lot.title or lot.id}: {err}" for lot, err in failed
            )
            messagebox.showwarning(
                "Часть лотов не сохранена",
                f"Успешно: {len(saved)}\nОшибок: {len(failed)}\n\n{details}",
            )
        else:
            messagebox.showinfo("Готово", f"Цены обновлены: {len(saved)}")


def main() -> None:
    root = tk.Tk()
    PriceEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
