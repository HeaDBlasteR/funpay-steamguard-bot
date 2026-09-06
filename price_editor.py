import logging
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

from bot.config import PRICE_SAVE_DELAY, validate_config
from bot.lots import (
    LOT_FIELD_LABELS,
    fetch_lot_fields,
    find_russian_in_english,
    read_lot_values,
    save_lot_values,
)
from bot.main import create_account
from bot.pricing import (
    format_price,
    load_lots,
    parse_amount,
    parse_price,
    set_lot_price,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)

SINGLE_LINE_FIELDS = ("title_ru", "title_en")
MULTI_LINE_FIELDS = (
    "description_ru",
    "description_en",
    "payment_msg_ru",
    "payment_msg_en",
)


def run_async(root, work, on_done):
    def runner():
        try:
            result = work()
        except Exception as error:
            root.after(0, lambda exc=error: on_done(None, exc))
        else:
            root.after(0, lambda value=result: on_done(value, None))

    threading.Thread(target=runner, daemon=True).start()


class LotDialog(tk.Toplevel):
    def __init__(self, parent, acc, lot, on_saved):
        super().__init__(parent)

        self.acc = acc
        self.lot = lot
        self.on_saved = on_saved
        self.widgets = {}

        title = lot.title or f"Лот {lot.id}"
        self.title(f"Редактирование: {title[:50]}")
        self.geometry("820x760")
        self.transient(parent)
        self.grab_set()

        self.status = tk.StringVar(value="Загружаю поля лота...")
        ttk.Label(self, textvariable=self.status, padding=8).pack(fill="x")

        body = ttk.Frame(self, padding=10)
        body.pack(fill="both", expand=True)

        canvas = tk.Canvas(body, highlightthickness=0)
        scrollbar = ttk.Scrollbar(body, orient="vertical", command=canvas.yview)
        self.form = ttk.Frame(canvas)
        self.form.bind(
            "<Configure>",
            lambda _: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self.form, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        buttons = ttk.Frame(self, padding=10)
        buttons.pack(fill="x")
        self.save_button = ttk.Button(
            buttons,
            text="Сохранить",
            command=self.save,
            state="disabled",
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
            ttk.Label(self.form, text=LOT_FIELD_LABELS[name]).pack(anchor="w")
            var = tk.StringVar(value=values.get(name, ""))
            ttk.Entry(self.form, textvariable=var, width=90).pack(
                fill="x", pady=(0, 8)
            )
            self.widgets[name] = var

        for name in MULTI_LINE_FIELDS:
            ttk.Label(self.form, text=LOT_FIELD_LABELS[name]).pack(anchor="w")
            text = tk.Text(self.form, height=6, wrap="word")
            text.insert("1.0", values.get(name, ""))
            text.pack(fill="x", pady=(0, 8))
            self.widgets[name] = text

        numbers = ttk.Frame(self.form)
        numbers.pack(fill="x", pady=(4, 0))

        ttk.Label(numbers, text="Цена").pack(side="left")
        self.price_var = tk.StringVar(value=format_price(fields.price))
        ttk.Entry(numbers, textvariable=self.price_var, width=12).pack(
            side="left", padx=(5, 20)
        )

        ttk.Label(numbers, text="Количество").pack(side="left")
        self.amount_var = tk.StringVar(
            value="" if fields.amount is None else str(fields.amount)
        )
        ttk.Entry(numbers, textvariable=self.amount_var, width=12).pack(
            side="left", padx=(5, 20)
        )

        self.active_var = tk.BooleanVar(value=fields.active)
        ttk.Checkbutton(numbers, text="Активен", variable=self.active_var).pack(
            side="left"
        )

    def _collect_values(self):
        values = {}

        for name, widget in self.widgets.items():
            if isinstance(widget, tk.Text):
                values[name] = widget.get("1.0", "end-1c")
            else:
                values[name] = widget.get()

        return values

    def save(self):
        values = self._collect_values()

        if not values["title_ru"].strip():
            messagebox.showerror(
                "Пустое название", "Название (RU) не может быть пустым.", parent=self
            )
            return

        russian = find_russian_in_english(values)
        if russian:
            messagebox.showerror(
                "Русские буквы в английской версии",
                "Уберите русские буквы из полей:\n\n"
                + "\n".join(LOT_FIELD_LABELS[name] for name in russian),
                parent=self,
            )
            return

        try:
            price = parse_price(self.price_var.get())
        except ValueError:
            messagebox.showerror(
                "Некорректная цена", "Цена должна быть положительным числом.", parent=self
            )
            return

        try:
            amount = parse_amount(self.amount_var.get())
        except ValueError:
            messagebox.showerror(
                "Некорректное количество",
                "Количество должно быть целым числом (или пустым).",
                parent=self,
            )
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
        root.geometry("1100x680")

        top = ttk.Frame(root, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Поиск:").pack(side="left")
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", lambda *_: self._apply_filter())
        ttk.Entry(top, textvariable=self.filter_var, width=40).pack(
            side="left", padx=(5, 15)
        )

        self.reload_button = ttk.Button(
            top, text="Обновить список", command=self.reload_lots
        )
        self.reload_button.pack(side="left")

        self.save_button = ttk.Button(
            top, text="Сохранить цены", command=self.save_changes
        )
        self.save_button.pack(side="left", padx=10)

        header = ttk.Frame(root, padding=(10, 0))
        header.pack(fill="x")
        ttk.Label(header, text="Лот", width=60).pack(side="left")
        ttk.Label(header, text="Текущая", width=10).pack(side="left")
        ttk.Label(header, text="Новая цена", width=14).pack(side="left")

        container = ttk.Frame(root, padding=10)
        container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            container, orient="vertical", command=self.canvas.yview
        )
        self.inner = ttk.Frame(self.canvas)

        self.inner.bind(
            "<Configure>",
            lambda _: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self.status = tk.StringVar(value="Подключаюсь к FunPay...")
        ttk.Label(root, textvariable=self.status, padding=10).pack(fill="x")

        self._set_busy(True)
        run_async(self.root, self._connect, self._on_connected)

    def _on_mousewheel(self, event) -> None:
        self.canvas.yview_scroll(int(-event.delta / 120), "units")

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
            messagebox.showerror("Ошибка", f"Не удалось подключиться:\n{error}")
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
            messagebox.showerror("Ошибка", f"Не удалось загрузить лоты:\n{error}")
        else:
            self._render_lots(lots)
            self.status.set(f"Загружено лотов: {len(lots)}")

        self._set_busy(False)

    def _render_lots(self, lots) -> None:
        for child in self.inner.winfo_children():
            child.destroy()

        self.rows = []

        for lot in lots:
            row = ttk.Frame(self.inner)
            row.pack(fill="x", pady=1)

            title = lot.title or f"Лот {lot.id}"
            ttk.Label(row, text=title[:60], width=60).pack(side="left")
            ttk.Label(row, text=format_price(lot.price), width=10).pack(side="left")

            var = tk.StringVar(value=format_price(lot.price))
            ttk.Entry(row, textvariable=var, width=12).pack(side="left", padx=(0, 10))

            ttk.Button(
                row,
                text="Изменить",
                width=10,
                command=lambda item=lot: self.open_lot(item),
            ).pack(side="left")

            self.rows.append({
                "lot": lot,
                "frame": row,
                "var": var,
                "original": format_price(lot.price),
                "title": title.lower(),
            })

    def open_lot(self, lot) -> None:
        if self.acc is None:
            return

        LotDialog(self.root, self.acc, lot, self.reload_lots)

    def _apply_filter(self) -> None:
        needle = self.filter_var.get().strip().lower()

        for row in self.rows:
            if needle in row["title"]:
                row["frame"].pack(fill="x", pady=1)
            else:
                row["frame"].pack_forget()

    def _collect_changes(self):
        changes = []
        invalid = []

        for row in self.rows:
            value = row["var"].get().strip()

            if value == row["original"]:
                continue

            try:
                price = parse_price(value)
            except ValueError:
                invalid.append(row["lot"].title or row["lot"].id)
                continue

            changes.append((row, price))

        return changes, invalid

    def save_changes(self) -> None:
        changes, invalid = self._collect_changes()

        if invalid:
            messagebox.showerror(
                "Некорректная цена",
                "Проверьте значения у лотов:\n" + "\n".join(str(i) for i in invalid),
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
        saved = []
        failed = []

        for index, (row, price) in enumerate(changes, start=1):
            lot = row["lot"]
            self.root.after(
                0,
                lambda i=index, t=len(changes): self.status.set(
                    f"Сохраняю {i}/{t}..."
                ),
            )

            try:
                set_lot_price(self.acc, lot, price)
            except Exception as error:
                failed.append((lot, error))
            else:
                saved.append((row, price))

            if index < len(changes):
                time.sleep(PRICE_SAVE_DELAY)

        return saved, failed

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
