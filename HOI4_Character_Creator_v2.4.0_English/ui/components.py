from __future__ import annotations

import tkinter as tk
from typing import Callable

import customtkinter as ctk


class Theme:
    BG = "#171D25"
    SIDEBAR = "#111720"
    TOPBAR = "#1C2430"
    PANEL = "#202A35"
    CARD = "#27323F"
    CARD_ALT = "#2D3947"
    INPUT = "#344252"
    BORDER = "#46566A"

    PRIMARY = "#4E7FC4"
    PRIMARY_HOVER = "#6192D6"
    PRIMARY_DARK = "#315D91"

    TEXT = "#F2F5F8"
    MUTED = "#AAB6C4"

    SUCCESS = "#4FA66B"
    WARNING = "#D4A64A"
    DANGER = "#C55C5C"
    CHIP = "#3A4A5D"


class Card(ctk.CTkFrame):
    def __init__(
        self,
        master,
        title: str,
        subtitle: str = "",
        **kwargs,
    ):
        super().__init__(
            master,
            fg_color=Theme.CARD,
            corner_radius=14,
            border_width=1,
            border_color=Theme.BORDER,
            **kwargs,
        )

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(16, 8))

        ctk.CTkLabel(
            header,
            text=title,
            text_color=Theme.TEXT,
            font=ctk.CTkFont(size=17, weight="bold"),
        ).pack(anchor="w")

        if subtitle:
            ctk.CTkLabel(
                header,
                text=subtitle,
                text_color=Theme.MUTED,
                justify="left",
                wraplength=760,
                font=ctk.CTkFont(size=12),
            ).pack(anchor="w", pady=(3, 0))

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=18, pady=(4, 18))


class StatusBadge(ctk.CTkLabel):
    COLORS = {
        "success": Theme.SUCCESS,
        "warning": Theme.WARNING,
        "danger": Theme.DANGER,
        "neutral": Theme.INPUT,
    }

    def __init__(self, master, text: str = "Not checked"):
        super().__init__(
            master,
            text=text,
            fg_color=self.COLORS["neutral"],
            text_color=Theme.TEXT,
            corner_radius=12,
            height=28,
            padx=12,
            font=ctk.CTkFont(size=12, weight="bold"),
        )

    def set_status(self, text: str, kind: str = "neutral") -> None:
        self.configure(
            text=text,
            fg_color=self.COLORS.get(kind, self.COLORS["neutral"]),
        )


class TraitChipEditor(ctk.CTkFrame):
    def __init__(
        self,
        master,
        variable: tk.StringVar,
        library_callback: Callable[[], None] | None = None,
    ):
        super().__init__(
            master,
            fg_color=Theme.CARD_ALT,
            corner_radius=10,
            border_width=1,
            border_color=Theme.BORDER,
        )

        self.variable = variable
        self.library_callback = library_callback
        self.enabled = True
        self._refresh_pending = False

        self.chips_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.chips_frame.pack(fill="x", padx=10, pady=(10, 4))

        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.pack(fill="x", padx=10, pady=(4, 10))
        controls.grid_columnconfigure(0, weight=1)

        self.entry_var = tk.StringVar()
        self.entry = ctk.CTkEntry(
            controls,
            textvariable=self.entry_var,
            placeholder_text="Add a trait manually…",
            fg_color=Theme.INPUT,
            border_color=Theme.BORDER,
            height=36,
        )
        self.entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.entry.bind("<Return>", lambda _event: self.add_trait())

        self.add_button = ctk.CTkButton(
            controls,
            text="+ Add",
            width=92,
            height=36,
            fg_color=Theme.PRIMARY,
            hover_color=Theme.PRIMARY_HOVER,
            command=self.add_trait,
        )
        self.add_button.grid(row=0, column=1, padx=(0, 8))

        self.library_button = ctk.CTkButton(
            controls,
            text="Library",
            width=104,
            height=36,
            fg_color=Theme.INPUT,
            hover_color=Theme.BORDER,
            command=self._open_library,
        )
        self.library_button.grid(row=0, column=2)

        self.variable.trace_add("write", self._queue_refresh)
        self.refresh()

    def _open_library(self) -> None:
        if self.library_callback:
            self.library_callback()

    def values(self) -> list[str]:
        return [
            item.strip()
            for item in self.variable.get().split(",")
            if item.strip()
        ]

    def add_trait(self, trait: str | None = None) -> None:
        if not self.enabled:
            return

        new_trait = (trait or self.entry_var.get()).strip()
        if not new_trait:
            return

        values = self.values()
        if new_trait not in values:
            values.append(new_trait)
            self.variable.set(", ".join(values))

        self.entry_var.set("")

    def remove_trait(self, trait: str) -> None:
        if not self.enabled:
            return

        values = [value for value in self.values() if value != trait]
        self.variable.set(", ".join(values))

    def _queue_refresh(self, *_args) -> None:
        if self._refresh_pending:
            return
        self._refresh_pending = True
        self.after_idle(self._run_refresh)

    def _run_refresh(self) -> None:
        self._refresh_pending = False
        self.refresh()

    def refresh(self) -> None:
        for child in self.chips_frame.winfo_children():
            child.destroy()

        values = self.values()

        if not values:
            ctk.CTkLabel(
                self.chips_frame,
                text="No trait selected",
                text_color=Theme.MUTED,
                font=ctk.CTkFont(size=12),
            ).grid(row=0, column=0, sticky="w", padx=2, pady=4)
            return

        columns = 2
        for index, trait in enumerate(values):
            row = index // columns
            column = index % columns

            chip = ctk.CTkButton(
                self.chips_frame,
                text=f"{trait}   ×",
                height=29,
                corner_radius=14,
                fg_color=Theme.CHIP,
                hover_color=Theme.DANGER,
                text_color=Theme.TEXT,
                command=lambda value=trait: self.remove_trait(value),
            )
            chip.grid(
                row=row,
                column=column,
                sticky="w",
                padx=(0, 7),
                pady=4,
            )

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        state = "normal" if enabled else "disabled"
        self.entry.configure(state=state)
        self.add_button.configure(state=state)
        self.library_button.configure(state=state)
        self.configure(
            fg_color=Theme.CARD_ALT if enabled else Theme.PANEL
        )
        self.refresh()
