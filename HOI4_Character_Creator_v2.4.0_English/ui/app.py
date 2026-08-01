from __future__ import annotations

import json
import re
import shutil
import sys
import tkinter as tk
import webbrowser
from dataclasses import asdict
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image, ImageTk

from generators.character_generator import (
    AdvisorData,
    CharacterData,
    CharacterGenerator,
    LeaderData,
    MilitaryData,
)
from ui.components import Card, StatusBadge, Theme, TraitChipEditor


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class HOI4CharacterCreator(ctk.CTk):
    APP_NAME = "HOI4 Character Creator"
    APP_VERSION = "2.4.0"
    PROJECT_NAME = "Beneath the Maroon Sky"
    GITHUB_URL = "https://github.com/LordVladimir88"
    DISCORD_URL = "https://discord.gg/NEz4pMTbXf"

    IDEOLOGY_FAMILY_ALIASES = {
        "conservatism": "conservativism",
        "paternal_autocracy": "paternal_despotism",
        "national_populist": "national_populism",
    }

    MILITARY_ROLES = [
        "corps_commander",
        "field_marshal",
        "navy_leader",
    ]

    ADVISOR_SLOTS = [
        "army_chief",
        "navy_chief",
        "air_chief",
        "high_command",
        "political_advisor",
        "theorist",
    ]

    ADVISOR_TRAITS = [
        "silent_workhorse",
        "popular_figurehead",
        "captain_of_industry",
        "war_industrialist",
        "fortification_engineer",
        "prince_of_terror",
        "backroom_backstabber",
        "compassionate_gentleman",
    ]


    PAGE_META = {
        "home": (
            "Home",
            "Project overview and quick access.",
        ),
        "library": (
            "Trait Library",
            "Search HOI4 traits and add them to the character.",
        ),
        "information": (
            "Character Information",
            "Identity, localisation keys, and portrait preview.",
        ),
        "leader": (
            "Country Leader",
            "Configure the political role and ideology.",
        ),
        "military": (
            "Military Command",
            "Create a general, field marshal, or admiral.",
        ),
        "advisor": (
            "Advisor",
            "Configure a political or military advisor.",
        ),
        "file": (
            "File and Export",
            "Group several characters and export them to the mod.",
        ),
    }

    def __init__(self) -> None:
        super().__init__()

        self.title(f"{self.APP_NAME} — {self.PROJECT_NAME}")
        self.geometry("1500x900")
        self.minsize(1220, 760)
        self.configure(fg_color=Theme.BG)

        self.root_dir = self._resource_root()
        self.assets_dir = self.root_dir / "assets"

        # Les statistiques restent écrites à côté de l'exécutable lorsque
        # l'application est compilée avec PyInstaller.
        if getattr(sys, "frozen", False):
            self.user_data_dir = Path(sys.executable).resolve().parent
        else:
            self.user_data_dir = self.root_dir

        self.stats_path = self.user_data_dir / "data" / "statistics.json"

        self.generator = CharacterGenerator()
        self.statistics = self._load_statistics()
        self.army_command_library = self._load_json_library(
            "army_command_traits.json",
            {
                "army_chief": [],
                "army_high_command": [],
                "definitions": {},
            },
        )
        self.unit_leader_library = self._load_json_library(
            "unit_leader_traits.json",
            {
                "army_personality": [],
                "field_marshal": [],
                "corps_commander": [],
                "definitions": {},
            },
        )
        self.rumburg_trait_library = self._load_json_library(
            "rumburg_traits.json",
            {
                "trait_count": 0,
                "duplicate_count": 0,
                "categories": {},
                "definitions": {},
            },
        )
        self.ideology_library = self._load_json_library(
            "ideologies.json",
            {
                "families": [],
                "family_count": 0,
                "subtype_count": 0,
            },
        )
        self._prepare_ideology_maps()

        self.characters_in_file: list[CharacterData] = []
        self.current_page = "home"
        self._validation_after_id = None
        self._syncing_keys = False

        self._set_app_icon()
        self._create_variables()
        self._create_layout()
        self._create_pages()
        self._bind_validation()
        self.reset_example()
        self.show_page("home")
        self._update_statistics_labels()
        self._validate_form()

    # ------------------------------------------------------------------
    # Données et configuration
    # ------------------------------------------------------------------
    @staticmethod
    def _resource_root() -> Path:
        """Return the resource root in Python or PyInstaller mode."""
        if hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS)
        return Path(__file__).resolve().parent.parent

    def _set_app_icon(self) -> None:
        """Apply the PNG and ICO icons to the main window."""
        logo_png = self.assets_dir / "logo.png"
        logo_ico = self.assets_dir / "logo.ico"

        try:
            icon_image = Image.open(logo_png).convert("RGBA")
            icon_image = icon_image.resize(
                (64, 64),
                Image.Resampling.LANCZOS,
            )
            self._window_icon = ImageTk.PhotoImage(icon_image)
            self.iconphoto(True, self._window_icon)
        except (OSError, tk.TclError):
            self._window_icon = None

        if sys.platform == "win32":
            try:
                self.iconbitmap(default=str(logo_ico))
            except tk.TclError:
                try:
                    self.iconbitmap(str(logo_ico))
                except tk.TclError:
                    pass

    def _load_json_library(self, filename: str, defaults: dict) -> dict:
        path = self.root_dir / "data" / filename
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            result = dict(defaults)
            result.update(loaded)
            return result
        except (OSError, ValueError, TypeError):
            return defaults

    def _prepare_ideology_maps(self) -> None:
        """Prepare ideology family and subtype mappings."""
        families = list(self.ideology_library.get("families", []))

        if not families:
            families = [
                {
                    "key": "paternal_despotism",
                    "display_name": "Paternal Autocracy",
                    "color": [54, 54, 54],
                    "subtypes": [
                        {
                            "key": "paternal_despotism_generic",
                            "display_name": "Generic Paternal Autocracy",
                        }
                    ],
                }
            ]

        self.ideology_families = families
        self.ideology_family_by_key = {
            family["key"]: family
            for family in families
        }
        self.ideology_family_keys = [
            family["key"]
            for family in families
        ]

        self.ideology_subtype_by_key: dict[str, dict] = {}
        self.ideology_subtype_to_family: dict[str, str] = {}

        for family in families:
            for subtype in family.get("subtypes", []):
                subtype_key = subtype["key"]
                self.ideology_subtype_by_key[subtype_key] = subtype
                self.ideology_subtype_to_family[subtype_key] = family["key"]

        preferred = "paternal_despotism_rumburgian_monarchism"

        if preferred in self.ideology_subtype_by_key:
            self.default_ideology_key = preferred
        else:
            default_family = self.ideology_family_by_key.get(
                "paternal_despotism",
                families[0],
            )
            subtypes = default_family.get("subtypes", [])
            self.default_ideology_key = (
                subtypes[0]["key"]
                if subtypes
                else "paternal_despotism_generic"
            )

    def _family_subtypes(self, family_key: str) -> list[dict]:
        family = self.ideology_family_by_key.get(family_key, {})
        return list(family.get("subtypes", []))

    def _family_subtype_keys(self, family_key: str) -> list[str]:
        return [
            subtype["key"]
            for subtype in self._family_subtypes(family_key)
        ]

    def _resolve_ideology_family(self, ideology_key: str) -> str:
        """Resolve the ideology family, including legacy projects."""
        ideology_key = ideology_key.strip()

        direct_family = self.ideology_subtype_to_family.get(ideology_key)
        if direct_family:
            return direct_family

        alias = self.IDEOLOGY_FAMILY_ALIASES.get(
            ideology_key,
            ideology_key,
        )

        if alias in self.ideology_family_by_key:
            return alias

        return self.ideology_family_keys[0]

    def _generic_ideology_for_family(self, family_key: str) -> str:
        values = self._family_subtype_keys(family_key)

        for value in values:
            if value.endswith("_generic"):
                return value

        return values[0] if values else self.default_ideology_key

    def _set_ideology_from_key(self, ideology_key: str) -> None:
        """Select an ideology and configure its family."""
        family_key = self._resolve_ideology_family(ideology_key)
        values = self._family_subtype_keys(family_key)

        resolved_key = ideology_key.strip()

        # Compatibilité avec les anciennes sauvegardes qui stockaient
        # seulement la famille principale.
        if resolved_key not in values:
            resolved_key = self._generic_ideology_for_family(family_key)

        self.ideology_family_var.set(family_key)

        if hasattr(self, "ideology_combo"):
            self.ideology_combo.configure(values=values)

        self.ideology_var.set(resolved_key)

        if hasattr(self, "ideology_info_label"):
            self._update_ideology_info()

    def _on_ideology_family_changed(
        self,
        _selected: str | None = None,
    ) -> None:
        family_key = self.ideology_family_var.get().strip()
        values = self._family_subtype_keys(family_key)

        if hasattr(self, "ideology_combo"):
            self.ideology_combo.configure(values=values)

        if self.ideology_var.get() not in values:
            self.ideology_var.set(
                self._generic_ideology_for_family(family_key)
            )

        self._update_ideology_info()
        self._queue_validation()

    def _on_ideology_changed(
        self,
        _selected: str | None = None,
    ) -> None:
        self._update_ideology_info()
        self._queue_validation()

    def _update_ideology_info(self) -> None:
        if not hasattr(self, "ideology_info_label"):
            return

        family_key = self.ideology_family_var.get().strip()
        subtype_key = self.ideology_var.get().strip()

        family = self.ideology_family_by_key.get(family_key, {})
        subtype = self.ideology_subtype_by_key.get(subtype_key, {})

        family_name = family.get("display_name", family_key)
        subtype_name = subtype.get("display_name", subtype_key)
        color = family.get("color", [128, 128, 128])

        self.ideology_info_label.configure(
            text=(
                f"{subtype_name}\n"
                f"HOI4 key : {subtype_key}\n"
                f"Family : {family_name} ({family_key})"
                f"  •  RGB {color[0]} {color[1]} {color[2]}"
            )
        )

    def _load_statistics(self) -> dict[str, int]:
        defaults = {
            "characters_generated": 0,
            "exports_completed": 0,
            "codes_copied": 0,
        }

        try:
            loaded = json.loads(self.stats_path.read_text(encoding="utf-8"))
            return {
                key: int(loaded.get(key, value))
                for key, value in defaults.items()
            }
        except (OSError, ValueError, TypeError):
            return defaults

    def _save_statistics(self) -> None:
        try:
            self.stats_path.parent.mkdir(parents=True, exist_ok=True)
            self.stats_path.write_text(
                json.dumps(self.statistics, indent=4, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass

    def _increment_stat(self, key: str) -> None:
        self.statistics[key] = self.statistics.get(key, 0) + 1
        self._save_statistics()
        self._update_statistics_labels()

    def _create_variables(self) -> None:
        self.tag_var = tk.StringVar(value="RUM")
        self.identifier_var = tk.StringVar(value="new_character")
        self.name_key_var = tk.StringVar(value="RUM_new_character")
        self.display_name_var = tk.StringVar(value="New Character")
        self.portrait_key_var = tk.StringVar(
            value="GFX_portrait_RUM_new_character"
        )
        self.portrait_source_var = tk.StringVar(value="")
        self.auto_keys_var = tk.BooleanVar(value=True)

        self.leader_enabled_var = tk.BooleanVar(value=False)
        default_family = self._resolve_ideology_family(
            self.default_ideology_key
        )
        self.ideology_family_var = tk.StringVar(
            value=default_family
        )
        self.ideology_var = tk.StringVar(
            value=self.default_ideology_key
        )
        self.leader_traits_var = tk.StringVar(value="popular_queen")
        self.expire_var = tk.StringVar(value="1965.1.1")
        self.description_var = tk.StringVar(
            value="RUM_new_character_desc"
        )

        self.military_enabled_var = tk.BooleanVar(value=False)
        self.military_role_var = tk.StringVar(value="corps_commander")
        self.military_traits_var = tk.StringVar(
            value="organizer, winter_specialist"
        )
        self.skill_var = tk.StringVar(value="3")
        self.attack_var = tk.StringVar(value="3")
        self.defense_var = tk.StringVar(value="3")
        self.planning_var = tk.StringVar(value="3")
        self.logistics_var = tk.StringVar(value="3")

        self.advisor_enabled_var = tk.BooleanVar(value=False)
        self.advisor_slot_var = tk.StringVar(value="army_chief")
        self.idea_token_var = tk.StringVar(
            value="RUM_new_character_advisor"
        )
        self.advisor_traits_var = tk.StringVar(
            value="army_chief_offensive_2"
        )
        self.advisor_cost_var = tk.StringVar(value="100")

        self.file_name_var = tk.StringVar(value="RUM_characters")
        self.preview_mode_var = tk.StringVar(value="Current character")
        self.library_search_var = tk.StringVar()
        self.library_current_category = "Army Personality"

        self.tag_var.trace_add("write", self._sync_keys)
        self.identifier_var.trace_add("write", self._sync_keys)

    def _sync_keys(self, *_args) -> None:
        if self._syncing_keys or not self.auto_keys_var.get():
            return

        self._syncing_keys = True
        try:
            tag = self.tag_var.get().strip().upper() or "TAG"
            identifier = (
                self.identifier_var.get().strip().lower()
                or "new_character"
            )
            key = f"{tag}_{identifier}"

            self.name_key_var.set(key)
            self.portrait_key_var.set(f"GFX_portrait_{key}")
            self.description_var.set(f"{key}_desc")
            self.idea_token_var.set(f"{key}_advisor")
            self.file_name_var.set(f"{tag}_characters")
        finally:
            self._syncing_keys = False

    # ------------------------------------------------------------------
    # Structure visuelle
    # ------------------------------------------------------------------
    def _create_layout(self) -> None:
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)
        self.grid_rowconfigure(1, weight=1)

        self.sidebar = ctk.CTkFrame(
            self,
            width=242,
            corner_radius=0,
            fg_color=Theme.SIDEBAR,
        )
        self.sidebar.grid(
            row=0,
            column=0,
            rowspan=3,
            sticky="nsew",
        )
        self.sidebar.grid_propagate(False)

        self.topbar = ctk.CTkFrame(
            self,
            height=82,
            corner_radius=0,
            fg_color=Theme.TOPBAR,
        )
        self.topbar.grid(
            row=0,
            column=1,
            columnspan=2,
            sticky="ew",
        )
        self.topbar.grid_columnconfigure(0, weight=1)

        self.page_container = ctk.CTkFrame(
            self,
            corner_radius=0,
            fg_color=Theme.BG,
        )
        self.page_container.grid(
            row=1,
            column=1,
            sticky="nsew",
            padx=(16, 8),
            pady=14,
        )
        # Les pages utilisent exclusivement pack() dans ce conteneur.
        # Cela évite la superposition des canevas internes de
        # CTkScrollableFrame.

        self.preview_panel = ctk.CTkFrame(
            self,
            width=420,
            fg_color=Theme.PANEL,
            corner_radius=14,
            border_width=1,
            border_color=Theme.BORDER,
        )
        self.preview_panel.grid(
            row=1,
            column=2,
            sticky="nsew",
            padx=(8, 16),
            pady=14,
        )
        self.preview_panel.grid_propagate(False)

        self.actionbar = ctk.CTkFrame(
            self,
            height=70,
            corner_radius=0,
            fg_color=Theme.TOPBAR,
        )
        self.actionbar.grid(
            row=2,
            column=1,
            columnspan=2,
            sticky="ew",
        )

        self._create_sidebar()
        self._create_topbar()
        self._create_preview_panel()
        self._create_actionbar()

    def _create_sidebar(self) -> None:
        logo_image = Image.open(self.assets_dir / "logo.png")
        self.sidebar_logo = ctk.CTkImage(
            light_image=logo_image,
            dark_image=logo_image,
            size=(88, 88),
        )

        ctk.CTkLabel(
            self.sidebar,
            text="",
            image=self.sidebar_logo,
        ).pack(pady=(24, 8))

        ctk.CTkLabel(
            self.sidebar,
            text=self.APP_NAME,
            text_color=Theme.TEXT,
            font=ctk.CTkFont(size=17, weight="bold"),
        ).pack()

        ctk.CTkLabel(
            self.sidebar,
            text=self.PROJECT_NAME,
            text_color=Theme.MUTED,
            font=ctk.CTkFont(size=11),
        ).pack(pady=(2, 20))

        separator = ctk.CTkFrame(
            self.sidebar,
            height=1,
            fg_color=Theme.BORDER,
        )
        separator.pack(fill="x", padx=18, pady=(0, 12))

        nav_items = [
            ("home", "⌂  Home"),
            ("library", "▤  Trait Library"),
            ("information", "♙  Character"),
            ("leader", "♛  Country Leader"),
            ("military", "⚔  Military"),
            ("advisor", "★  Advisor"),
            ("file", "▣  File"),
        ]

        self.nav_buttons: dict[str, ctk.CTkButton] = {}

        for key, label in nav_items:
            button = ctk.CTkButton(
                self.sidebar,
                text=label,
                anchor="w",
                height=42,
                corner_radius=9,
                fg_color="transparent",
                hover_color=Theme.CARD,
                text_color=Theme.TEXT,
                font=ctk.CTkFont(size=14),
                command=lambda page=key: self.after_idle(
                    lambda selected=page: self.show_page(selected)
                ),
            )
            button.pack(fill="x", padx=14, pady=3)
            self.nav_buttons[key] = button

        ctk.CTkFrame(
            self.sidebar,
            fg_color="transparent",
        ).pack(fill="both", expand=True)

        ctk.CTkButton(
            self.sidebar,
            text="◉  GitHub",
            height=35,
            fg_color=Theme.CARD,
            hover_color=Theme.BORDER,
            command=lambda: webbrowser.open_new_tab(self.GITHUB_URL),
        ).pack(fill="x", padx=14, pady=3)

        ctk.CTkButton(
            self.sidebar,
            text="●  Discord",
            height=35,
            fg_color=Theme.CARD,
            hover_color=Theme.BORDER,
            command=lambda: webbrowser.open_new_tab(self.DISCORD_URL),
        ).pack(fill="x", padx=14, pady=3)

        ctk.CTkLabel(
            self.sidebar,
            text=f"Version {self.APP_VERSION}",
            text_color=Theme.MUTED,
            font=ctk.CTkFont(size=11),
        ).pack(pady=(14, 18))

    def _create_topbar(self) -> None:
        title_area = ctk.CTkFrame(
            self.topbar,
            fg_color="transparent",
        )
        title_area.grid(
            row=0,
            column=0,
            sticky="w",
            padx=24,
            pady=14,
        )

        self.page_title_label = ctk.CTkLabel(
            title_area,
            text="Home",
            text_color=Theme.TEXT,
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        self.page_title_label.pack(anchor="w")

        self.page_subtitle_label = ctk.CTkLabel(
            title_area,
            text="",
            text_color=Theme.MUTED,
            font=ctk.CTkFont(size=12),
        )
        self.page_subtitle_label.pack(anchor="w", pady=(2, 0))

        self.validation_badge = StatusBadge(
            self.topbar,
            "Not checked",
        )
        self.validation_badge.grid(
            row=0,
            column=1,
            padx=24,
            pady=20,
        )

    def _create_preview_panel(self) -> None:
        header = ctk.CTkFrame(
            self.preview_panel,
            fg_color="transparent",
        )
        header.pack(fill="x", padx=16, pady=(16, 8))

        ctk.CTkLabel(
            header,
            text="Code Preview",
            text_color=Theme.TEXT,
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text="The code is generated on demand in real time.",
            text_color=Theme.MUTED,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", pady=(2, 8))

        self.preview_mode = ctk.CTkSegmentedButton(
            header,
            values=["Current character", "Full file"],
            variable=self.preview_mode_var,
            command=lambda _value: self.update_preview(),
            selected_color=Theme.PRIMARY,
            selected_hover_color=Theme.PRIMARY_HOVER,
            unselected_color=Theme.INPUT,
            unselected_hover_color=Theme.BORDER,
        )
        self.preview_mode.pack(fill="x")

        self.preview_text = ctk.CTkTextbox(
            self.preview_panel,
            fg_color="#10161D",
            border_width=1,
            border_color=Theme.BORDER,
            corner_radius=10,
            text_color="#DDE7F2",
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="none",
        )
        self.preview_text.pack(
            fill="both",
            expand=True,
            padx=16,
            pady=8,
        )

        footer = ctk.CTkFrame(
            self.preview_panel,
            fg_color="transparent",
        )
        footer.pack(fill="x", padx=16, pady=(4, 16))

        self.preview_info_label = ctk.CTkLabel(
            footer,
            text="0 lines • 0 characters",
            text_color=Theme.MUTED,
            font=ctk.CTkFont(size=11),
        )
        self.preview_info_label.pack(side="left")

        ctk.CTkButton(
            footer,
            text="Copy",
            width=88,
            height=34,
            fg_color=Theme.INPUT,
            hover_color=Theme.BORDER,
            command=self.copy_preview,
        ).pack(side="right")

    def _create_actionbar(self) -> None:
        left = ctk.CTkFrame(
            self.actionbar,
            fg_color="transparent",
        )
        left.pack(side="left", padx=18, pady=12)

        right = ctk.CTkFrame(
            self.actionbar,
            fg_color="transparent",
        )
        right.pack(side="right", padx=18, pady=12)

        ctk.CTkButton(
            left,
            text="Reset Example",
            height=40,
            fg_color=Theme.INPUT,
            hover_color=Theme.BORDER,
            command=self.reset_example,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            left,
            text="Validate",
            height=40,
            fg_color=Theme.CARD,
            hover_color=Theme.BORDER,
            command=lambda: self._validate_form(show_dialog=True),
        ).pack(side="left")

        ctk.CTkButton(
            right,
            text="Preview",
            height=40,
            width=100,
            fg_color=Theme.INPUT,
            hover_color=Theme.BORDER,
            command=self.update_preview,
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            right,
            text="Add to File",
            height=40,
            width=150,
            fg_color=Theme.PRIMARY,
            hover_color=Theme.PRIMARY_HOVER,
            command=self.add_current_character,
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            right,
            text="Export to Mod",
            height=40,
            width=165,
            fg_color=Theme.SUCCESS,
            hover_color="#438D5B",
            command=self.export_to_mod,
        ).pack(side="left", padx=4)

    # ------------------------------------------------------------------
    # Pages
    # ------------------------------------------------------------------
    def _new_page(self, key: str) -> ctk.CTkScrollableFrame:
        """Create a hidden page.

        All pages use the same geometry manager, ``pack``. Only one page
        can be visible at a time.
        """
        page = ctk.CTkScrollableFrame(
            self.page_container,
            fg_color=Theme.BG,
            corner_radius=0,
            scrollbar_button_color=Theme.INPUT,
            scrollbar_button_hover_color=Theme.BORDER,
        )
        self.pages[key] = page
        return page

    def _page_header(
        self,
        page,
        title: str,
        description: str,
    ) -> None:
        ctk.CTkLabel(
            page,
            text=title,
            text_color=Theme.TEXT,
            font=ctk.CTkFont(size=25, weight="bold"),
        ).pack(anchor="w", padx=4, pady=(2, 0))

        ctk.CTkLabel(
            page,
            text=description,
            text_color=Theme.MUTED,
            justify="left",
            wraplength=760,
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=4, pady=(3, 15))

    def _create_pages(self) -> None:
        self.pages: dict[str, ctk.CTkScrollableFrame] = {}

        self._create_home_page(self._new_page("home"))
        self._create_library_page(self._new_page("library"))
        self._create_information_page(self._new_page("information"))
        self._create_leader_page(self._new_page("leader"))
        self._create_military_page(self._new_page("military"))
        self._create_advisor_page(self._new_page("advisor"))
        self._create_file_page(self._new_page("file"))

        # Aucune page ne reste affichée à la fin de la construction.
        # show_page() choisira explicitement la première page visible.
        for page in self.pages.values():
            page.pack_forget()

    def _create_home_page(self, page) -> None:
        self._page_header(
            page,
            "Welcome to HOI4 Character Creator",
            "A complete workspace for creating and organizing characters for your mod.",
        )

        hero = Card(
            page,
            "Kingdom of Rumburg Modding Tool",
            "Character creation, trait management, code preview, and direct export.",
        )
        hero.pack(fill="x", padx=4, pady=(0, 14))

        logo_image = Image.open(self.assets_dir / "logo.png")
        self.home_logo = ctk.CTkImage(
            light_image=logo_image,
            dark_image=logo_image,
            size=(118, 118),
        )

        ctk.CTkLabel(
            hero.body,
            text="",
            image=self.home_logo,
        ).pack(side="left", padx=(0, 20))

        hero_text = ctk.CTkFrame(hero.body, fg_color="transparent")
        hero_text.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(
            hero_text,
            text=f"{self.APP_NAME}  •  Version {self.APP_VERSION}",
            text_color=Theme.TEXT,
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(anchor="w")

        ctk.CTkLabel(
            hero_text,
            text=(
                "This version uses a sidebar, cards, a portrait preview, "
                "visual trait chips, and a custom application logo."
            ),
            text_color=Theme.MUTED,
            justify="left",
            wraplength=590,
            font=ctk.CTkFont(size=13),
        ).pack(anchor="w", pady=(7, 14))

        quick = ctk.CTkFrame(hero_text, fg_color="transparent")
        quick.pack(anchor="w")

        for label, page_key in [
            ("Create a Character", "information"),
            ("Browse Traits", "library"),
            ("Open File", "file"),
        ]:
            ctk.CTkButton(
                quick,
                text=label,
                height=38,
                fg_color=Theme.PRIMARY,
                hover_color=Theme.PRIMARY_HOVER,
                command=lambda key=page_key: self.show_page(key),
            ).pack(side="left", padx=(0, 8))

        stats = ctk.CTkFrame(page, fg_color="transparent")
        stats.pack(fill="x", padx=4, pady=(0, 14))
        for column in range(3):
            stats.grid_columnconfigure(column, weight=1)

        self.home_stat_labels: dict[str, ctk.CTkLabel] = {}
        stat_data = [
            ("characters_generated", "★", "Characters Added"),
            ("exports_completed", "⇩", "Exports Completed"),
            ("codes_copied", "⧉", "Codes Copied"),
        ]

        for column, (key, icon, title) in enumerate(stat_data):
            card = ctk.CTkFrame(
                stats,
                fg_color=Theme.CARD,
                corner_radius=14,
                border_width=1,
                border_color=Theme.BORDER,
            )
            card.grid(
                row=0,
                column=column,
                sticky="nsew",
                padx=(0 if column == 0 else 7, 0 if column == 2 else 7),
            )

            ctk.CTkLabel(
                card,
                text=icon,
                text_color=Theme.PRIMARY_HOVER,
                font=ctk.CTkFont(size=24, weight="bold"),
            ).pack(anchor="w", padx=16, pady=(14, 0))

            value = ctk.CTkLabel(
                card,
                text="0",
                text_color=Theme.TEXT,
                font=ctk.CTkFont(size=29, weight="bold"),
            )
            value.pack(anchor="w", padx=16, pady=(2, 0))
            self.home_stat_labels[key] = value

            ctk.CTkLabel(
                card,
                text=title,
                text_color=Theme.MUTED,
                font=ctk.CTkFont(size=12),
            ).pack(anchor="w", padx=16, pady=(0, 14))

        features = Card(
            page,
            "Version 2.4 Features",
        )
        features.pack(fill="x", padx=4, pady=(0, 14))

        ctk.CTkLabel(
            features.body,
            text=(
                "✓ Modern sidebar navigation and card layout\n"
                "✓ Custom logo in the window and interface\n"
                "✓ Prefilled fields and automatic key synchronization\n"
                "✓ PNG, JPG, WEBP, and DDS portrait preview\n"
                "✓ Removable visual trait chips\n"
                "✓ 8 ideology families and 111 sub-ideologies\n"
                f"✓ {self.rumburg_trait_library.get('trait_count', 0)} "
                "cleaned and reorganized Rumburg traits\n"
                "✓ Duplicates removed and military categories separated\n"
                "✓ Data validation and role-state controls\n"
                "✓ Multiple characters in the same file\n"
                "✓ DDS portrait conversion and automatic GFX generation"
            ),
            text_color=Theme.TEXT,
            justify="left",
            font=ctk.CTkFont(size=13),
        ).pack(anchor="w")

    def _deduplicate_library_categories(self) -> None:
        """Remove repeated identifiers from visible categories."""
        seen: set[str] = set()

        for data in self.library_categories.values():
            unique_values = []

            for trait in data.get("values", []):
                if trait in seen:
                    continue

                seen.add(trait)
                unique_values.append(trait)

            data["values"] = unique_values

    def _create_library_page(self, page) -> None:
        self._page_header(
            page,
            "Trait Library",
            "Traits are grouped by function and each identifier appears only once.",
        )

        container = ctk.CTkFrame(page, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=4, pady=(0, 14))
        container.grid_columnconfigure(1, weight=1)
        container.grid_rowconfigure(0, weight=1)

        categories_panel = ctk.CTkScrollableFrame(
            container,
            width=226,
            height=610,
            fg_color=Theme.CARD,
            corner_radius=14,
            border_width=1,
            border_color=Theme.BORDER,
            scrollbar_button_color=Theme.INPUT,
            scrollbar_button_hover_color=Theme.BORDER,
        )
        categories_panel.grid(
            row=0,
            column=0,
            sticky="nsw",
            padx=(0, 12),
        )

        ctk.CTkLabel(
            categories_panel,
            text="Categories",
            text_color=Theme.TEXT,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=8, pady=(8, 10))

        rumburg_categories = self.rumburg_trait_library.get(
            "categories",
            {},
        )

        self.library_categories = {
            "Army Personality": {
                "values": self.unit_leader_library.get(
                    "army_personality",
                    [],
                ),
                "target": "army_personality",
            },
            "Field Marshal": {
                "values": self.unit_leader_library.get(
                    "field_marshal",
                    [],
                ),
                "target": "field_marshal",
            },
            "Corps Commander": {
                "values": self.unit_leader_library.get(
                    "corps_commander",
                    [],
                ),
                "target": "corps_commander",
            },
            "Army Chief": {
                "values": self.army_command_library.get(
                    "army_chief",
                    [],
                ),
                "target": "army_chief",
            },
            "Army High Command": {
                "values": self.army_command_library.get(
                    "army_high_command",
                    [],
                ),
                "target": "high_command",
            },
            "Advisor Trait": {
                "values": self.ADVISOR_TRAITS,
                "target": "advisor",
            },
            "RUM Leaders": {
                "values": rumburg_categories.get("leaders", []),
                "target": "leader",
            },
            "RUM Ministers": {
                "values": rumburg_categories.get("ministers", []),
                "target": "advisor",
            },
            "RUM Ideologies": {
                "values": rumburg_categories.get("ideological", []),
                "target": "advisor",
            },
            "RUM Influential Figures": {
                "values": rumburg_categories.get("influential", []),
                "target": "advisor",
            },
            "RUM Negative Traits": {
                "values": rumburg_categories.get("negative", []),
                "target": "advisor",
            },
            "RUM Theorists": {
                "values": rumburg_categories.get("theorists", []),
                "target": "theorist",
            },
            "RUM Aviation": {
                "values": rumburg_categories.get("air_designers", []),
                "target": "advisor",
            },
            "RUM Armor & Land": {
                "values": rumburg_categories.get("land_designers", []),
                "target": "advisor",
            },
            "RUM Navy": {
                "values": rumburg_categories.get("naval_designers", []),
                "target": "advisor",
            },
            "RUM Companies": {
                "values": rumburg_categories.get("companies", []),
                "target": "advisor",
            },
        }

        self._deduplicate_library_categories()

        self.library_category_groups = [
            (
                "COMMANDERS",
                [
                    "Army Personality",
                    "Field Marshal",
                    "Corps Commander",
                ],
            ),
            (
                "ADVISORS",
                [
                    "Army Chief",
                    "Army High Command",
                    "Advisor Trait",
                ],
            ),
            (
                "RUMBURG POLITICS",
                [
                    "RUM Leaders",
                    "RUM Ministers",
                    "RUM Ideologies",
                    "RUM Influential Figures",
                    "RUM Negative Traits",
                ],
            ),
            (
                "MILITARY AND INDUSTRY",
                [
                    "RUM Theorists",
                    "RUM Aviation",
                    "RUM Armor & Land",
                    "RUM Navy",
                    "RUM Companies",
                ],
            ),
        ]

        self.library_category_buttons = {}

        for group_title, category_names in self.library_category_groups:
            ctk.CTkLabel(
                categories_panel,
                text=group_title,
                text_color=Theme.MUTED,
                font=ctk.CTkFont(size=10, weight="bold"),
            ).pack(
                anchor="w",
                padx=8,
                pady=(10, 3),
            )

            for title in category_names:
                data = self.library_categories[title]
                button = ctk.CTkButton(
                    categories_panel,
                    text=f"{title}  ({len(data['values'])})",
                    anchor="w",
                    height=34,
                    fg_color="transparent",
                    hover_color=Theme.CARD_ALT,
                    command=lambda name=title: (
                        self._select_library_category(name)
                    ),
                )
                button.pack(fill="x", padx=4, pady=1)
                self.library_category_buttons[title] = button

        main = ctk.CTkFrame(
            container,
            fg_color=Theme.CARD,
            corner_radius=14,
            border_width=1,
            border_color=Theme.BORDER,
        )
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(2, weight=1)
        main.grid_rowconfigure(4, weight=1)

        header = ctk.CTkFrame(main, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        header.grid_columnconfigure(0, weight=1)

        self.library_category_title = ctk.CTkLabel(
            header,
            text="Army Personality",
            text_color=Theme.TEXT,
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        self.library_category_title.grid(row=0, column=0, sticky="w")

        self.library_search_entry = ctk.CTkEntry(
            header,
            textvariable=self.library_search_var,
            placeholder_text="Search for a trait…",
            width=260,
            height=36,
            fg_color=Theme.INPUT,
            border_color=Theme.BORDER,
        )
        self.library_search_entry.grid(row=0, column=1, sticky="e")

        list_frame = ctk.CTkFrame(main, fg_color="transparent")
        list_frame.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=16,
            pady=(2, 8),
        )
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)

        self.library_listbox = tk.Listbox(
            list_frame,
            bg="#10161D",
            fg="#E4ECF5",
            selectbackground=Theme.PRIMARY,
            selectforeground="white",
            relief="flat",
            highlightthickness=1,
            highlightbackground=Theme.BORDER,
            activestyle="none",
            font=("Consolas", 11),
            exportselection=False,
        )
        self.library_listbox.grid(row=0, column=0, sticky="nsew")

        list_scroll = tk.Scrollbar(
            list_frame,
            orient="vertical",
            command=self.library_listbox.yview,
        )
        list_scroll.grid(row=0, column=1, sticky="ns")
        self.library_listbox.configure(yscrollcommand=list_scroll.set)

        ctk.CTkLabel(
            main,
            text="Definition and Information",
            text_color=Theme.MUTED,
        ).grid(row=3, column=0, sticky="w", padx=16)

        self.library_details = ctk.CTkTextbox(
            main,
            height=210,
            fg_color="#10161D",
            border_width=1,
            border_color=Theme.BORDER,
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="none",
        )
        self.library_details.grid(
            row=4,
            column=0,
            sticky="nsew",
            padx=16,
            pady=(5, 8),
        )

        actions = ctk.CTkFrame(main, fg_color="transparent")
        actions.grid(row=5, column=0, sticky="ew", padx=16, pady=(2, 16))

        ctk.CTkButton(
            actions,
            text="Copy Identifier",
            fg_color=Theme.INPUT,
            hover_color=Theme.BORDER,
            command=self._copy_library_trait,
        ).pack(side="left")

        ctk.CTkButton(
            actions,
            text="Use This Trait",
            fg_color=Theme.PRIMARY,
            hover_color=Theme.PRIMARY_HOVER,
            command=self._use_library_trait,
        ).pack(side="right")

        self.library_search_var.trace_add(
            "write",
            lambda *_args: self._refresh_library_list(),
        )
        self.library_listbox.bind(
            "<<ListboxSelect>>",
            lambda _event: self._show_library_details(),
        )
        self.library_listbox.bind(
            "<Double-Button-1>",
            lambda _event: self._use_library_trait(),
        )

        self._select_library_category("Army Personality")

    def _create_information_page(self, page) -> None:
        self._page_header(
            page,
            "Character Information",
            "Keys can be generated automatically from the country tag and identifier.",
        )

        general = Card(
            page,
            "Main Identity",
            "Fields are prefilled with an editable example.",
        )
        general.pack(fill="x", padx=4, pady=(0, 14))
        general.body.grid_columnconfigure(1, weight=1)

        self.tag_entry = self._entry_row(
            general.body,
            0,
            "Country Tag",
            self.tag_var,
            "Three letters, for example RUM.",
        )
        self.identifier_entry = self._entry_row(
            general.body,
            1,
            "Identifier",
            self.identifier_var,
            "Technical identifier without spaces.",
        )
        self.display_name_entry = self._entry_row(
            general.body,
            2,
            "Display Name",
            self.display_name_var,
            "Name displayed in the game.",
        )

        ctk.CTkSwitch(
            general.body,
            text="Automatically Synchronize Keys",
            variable=self.auto_keys_var,
            command=self._sync_keys,
            progress_color=Theme.PRIMARY,
        ).grid(
            row=3,
            column=1,
            sticky="w",
            padx=8,
            pady=(9, 0),
        )

        technical = Card(
            page,
            "Localisation and GFX Keys",
        )
        technical.pack(fill="x", padx=4, pady=(0, 14))
        technical.body.grid_columnconfigure(1, weight=1)

        self.name_key_entry = self._entry_row(
            technical.body,
            0,
            "Localisation Key",
            self.name_key_var,
        )
        self.portrait_key_entry = self._entry_row(
            technical.body,
            1,
            "Portrait GFX Key",
            self.portrait_key_var,
        )

        portrait_card = Card(
            page,
            "Portrait Preview",
            "Select a PNG, JPG, WEBP, or DDS image. It can be converted to DDS during export.",
        )
        portrait_card.pack(fill="x", padx=4, pady=(0, 14))
        portrait_card.body.grid_columnconfigure(0, weight=1)

        portrait_controls = ctk.CTkFrame(
            portrait_card.body,
            fg_color="transparent",
        )
        portrait_controls.grid(row=0, column=0, sticky="nsew", padx=(0, 18))

        self.portrait_path_entry = ctk.CTkEntry(
            portrait_controls,
            textvariable=self.portrait_source_var,
            placeholder_text="No image selected",
            fg_color=Theme.INPUT,
            border_color=Theme.BORDER,
            height=38,
        )
        self.portrait_path_entry.pack(fill="x", pady=(0, 10))

        portrait_buttons = ctk.CTkFrame(
            portrait_controls,
            fg_color="transparent",
        )
        portrait_buttons.pack(fill="x")

        ctk.CTkButton(
            portrait_buttons,
            text="Choose Image",
            fg_color=Theme.PRIMARY,
            hover_color=Theme.PRIMARY_HOVER,
            command=self.choose_portrait,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            portrait_buttons,
            text="Remove",
            fg_color=Theme.INPUT,
            hover_color=Theme.BORDER,
            command=self.clear_portrait,
        ).pack(side="left")

        ctk.CTkLabel(
            portrait_controls,
            text=(
                "During export, the image is copied to gfx/leaders/TAG "
                "and an interface/*.gfx file is generated."
            ),
            text_color=Theme.MUTED,
            justify="left",
            wraplength=480,
        ).pack(anchor="w", pady=(12, 0))

        default_portrait = Image.open(
            self.assets_dir / "default_portrait.png"
        )
        self.portrait_preview_image = ctk.CTkImage(
            light_image=default_portrait,
            dark_image=default_portrait,
            size=(168, 216),
        )
        self.portrait_preview_label = ctk.CTkLabel(
            portrait_card.body,
            text="",
            image=self.portrait_preview_image,
            fg_color=Theme.PANEL,
            corner_radius=10,
        )
        self.portrait_preview_label.grid(
            row=0,
            column=1,
            sticky="e",
        )

        self.info_status = StatusBadge(page, "Needs Review")
        self.info_status.pack(anchor="e", padx=4, pady=(0, 14))

    def _create_leader_page(self, page) -> None:
        self._page_header(
            page,
            "Country Leader",
            (
                "First select an ideology family, then a sub-ideology "
                "from the 00_ideologies.txt file."
            ),
        )

        card = Card(
            page,
            "Country Leader Role",
            (
                f"{self.ideology_library.get('family_count', 0)} families "
                f"and {self.ideology_library.get('subtype_count', 0)} "
                "sub-ideologies are available."
            ),
        )
        card.pack(fill="x", padx=4, pady=(0, 14))
        card.body.grid_columnconfigure(1, weight=1)

        self.leader_switch = ctk.CTkSwitch(
            card.body,
            text="Enable Country Leader Role",
            variable=self.leader_enabled_var,
            command=self._toggle_leader_controls,
            progress_color=Theme.SUCCESS,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.leader_switch.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 14),
        )

        self.ideology_family_combo = self._combo_row(
            card.body,
            1,
            "Ideology Family",
            self.ideology_family_var,
            self.ideology_family_keys,
        )
        self.ideology_family_combo.configure(
            command=self._on_ideology_family_changed
        )

        initial_subtypes = self._family_subtype_keys(
            self.ideology_family_var.get()
        )

        self.ideology_combo = self._combo_row(
            card.body,
            2,
            "Sub-Ideology",
            self.ideology_var,
            initial_subtypes,
        )
        self.ideology_combo.configure(
            command=self._on_ideology_changed
        )

        self.ideology_info_label = ctk.CTkLabel(
            card.body,
            text="",
            text_color=Theme.MUTED,
            justify="left",
            anchor="w",
            fg_color=Theme.CARD_ALT,
            corner_radius=9,
            padx=12,
            pady=10,
            font=ctk.CTkFont(size=11),
        )
        self.ideology_info_label.grid(
            row=3,
            column=1,
            sticky="ew",
            padx=8,
            pady=(2, 8),
        )

        self.expire_entry = self._entry_row(
            card.body,
            4,
            "Expiration Date",
            self.expire_var,
            "HOI4 format: 1965.1.1",
        )
        self.description_entry = self._entry_row(
            card.body,
            5,
            "Description Key",
            self.description_var,
        )

        traits_card = Card(
            page,
            "Leader Traits",
            "Add a trait manually or open the library.",
        )
        traits_card.pack(fill="x", padx=4, pady=(0, 14))

        self.leader_traits_editor = TraitChipEditor(
            traits_card.body,
            self.leader_traits_var,
            library_callback=lambda: self.show_page("library"),
        )
        self.leader_traits_editor.pack(fill="x")

        self.leader_controls = [
            self.ideology_family_combo,
            self.ideology_combo,
            self.expire_entry,
            self.description_entry,
            self.leader_traits_editor,
        ]

        self.leader_status = StatusBadge(page, "Disabled")
        self.leader_status.pack(anchor="e", padx=4, pady=(0, 14))

        self._set_ideology_from_key(self.ideology_var.get())

    def _create_military_page(self, page) -> None:
        self._page_header(
            page,
            "Military Command",
            "Configure the skills and traits of a general, field marshal, or admiral.",
        )

        card = Card(
            page,
            "Military Role",
        )
        card.pack(fill="x", padx=4, pady=(0, 14))
        card.body.grid_columnconfigure(1, weight=1)

        self.military_switch = ctk.CTkSwitch(
            card.body,
            text="Enable Military Role",
            variable=self.military_enabled_var,
            command=self._toggle_military_controls,
            progress_color=Theme.SUCCESS,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.military_switch.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 14),
        )

        self.military_role_combo = self._combo_row(
            card.body,
            1,
            "Commander Type",
            self.military_role_var,
            self.MILITARY_ROLES,
        )

        skills = Card(
            page,
            "Skills",
            "Values must be between 1 and 10.",
        )
        skills.pack(fill="x", padx=4, pady=(0, 14))

        skills.body.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        self.skill_controls = []
        skill_data = [
            ("Skill", self.skill_var),
            ("Attack", self.attack_var),
            ("Defense", self.defense_var),
            ("Planning", self.planning_var),
            ("Logistics", self.logistics_var),
        ]

        values = [str(value) for value in range(1, 11)]

        for column, (label, variable) in enumerate(skill_data):
            frame = ctk.CTkFrame(
                skills.body,
                fg_color=Theme.CARD_ALT,
                corner_radius=10,
            )
            frame.grid(
                row=0,
                column=column,
                sticky="nsew",
                padx=(0 if column == 0 else 5, 0 if column == 4 else 5),
            )

            ctk.CTkLabel(
                frame,
                text=label,
                text_color=Theme.MUTED,
            ).pack(pady=(10, 4))

            menu = ctk.CTkOptionMenu(
                frame,
                variable=variable,
                values=values,
                fg_color=Theme.INPUT,
                button_color=Theme.PRIMARY_DARK,
                button_hover_color=Theme.PRIMARY,
                width=105,
            )
            menu.pack(padx=10, pady=(0, 10))
            self.skill_controls.append(menu)

        traits = Card(
            page,
            "Military Traits",
        )
        traits.pack(fill="x", padx=4, pady=(0, 14))

        self.military_traits_editor = TraitChipEditor(
            traits.body,
            self.military_traits_var,
            library_callback=lambda: self.show_page("library"),
        )
        self.military_traits_editor.pack(fill="x")

        self.military_controls = [
            self.military_role_combo,
            *self.skill_controls,
            self.military_traits_editor,
        ]

        self.military_status = StatusBadge(page, "Disabled")
        self.military_status.pack(anchor="e", padx=4, pady=(0, 14))

    def _create_advisor_page(self, page) -> None:
        self._page_header(
            page,
            "Advisor",
            "Configure the slot, Idea Token, cost, and traits.",
        )

        card = Card(
            page,
            "Advisor Role",
        )
        card.pack(fill="x", padx=4, pady=(0, 14))
        card.body.grid_columnconfigure(1, weight=1)

        self.advisor_switch = ctk.CTkSwitch(
            card.body,
            text="Enable Advisor Role",
            variable=self.advisor_enabled_var,
            command=self._toggle_advisor_controls,
            progress_color=Theme.SUCCESS,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.advisor_switch.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 14),
        )

        self.advisor_slot_combo = self._combo_row(
            card.body,
            1,
            "Slot",
            self.advisor_slot_var,
            self.ADVISOR_SLOTS,
        )
        self.idea_token_entry = self._entry_row(
            card.body,
            2,
            "Idea Token",
            self.idea_token_var,
        )
        self.advisor_cost_entry = self._entry_row(
            card.body,
            3,
            "Political Power Cost",
            self.advisor_cost_var,
            "Positive integer.",
        )

        traits = Card(
            page,
            "Advisor Traits",
        )
        traits.pack(fill="x", padx=4, pady=(0, 14))

        self.advisor_traits_editor = TraitChipEditor(
            traits.body,
            self.advisor_traits_var,
            library_callback=lambda: self.show_page("library"),
        )
        self.advisor_traits_editor.pack(fill="x")

        self.advisor_controls = [
            self.advisor_slot_combo,
            self.idea_token_entry,
            self.advisor_cost_entry,
            self.advisor_traits_editor,
        ]

        self.advisor_status = StatusBadge(page, "Disabled")
        self.advisor_status.pack(anchor="e", padx=4, pady=(0, 14))

    def _create_file_page(self, page) -> None:
        self._page_header(
            page,
            "Characters in File",
            "Add multiple characters and export them in a shared file.",
        )

        settings = Card(
            page,
            "File Settings",
        )
        settings.pack(fill="x", padx=4, pady=(0, 14))
        settings.body.grid_columnconfigure(1, weight=1)

        self.file_name_entry = self._entry_row(
            settings.body,
            0,
            "Base Name",
            self.file_name_var,
            "Example: RUM_characters",
        )

        list_card = Card(
            page,
            "Saved Characters",
        )
        list_card.pack(fill="both", expand=True, padx=4, pady=(0, 14))
        list_card.body.grid_columnconfigure(0, weight=1)
        list_card.body.grid_rowconfigure(0, weight=1)

        list_frame = ctk.CTkFrame(
            list_card.body,
            fg_color="transparent",
        )
        list_frame.grid(row=0, column=0, sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)

        self.file_listbox = tk.Listbox(
            list_frame,
            height=10,
            bg="#10161D",
            fg="#E4ECF5",
            selectbackground=Theme.PRIMARY,
            selectforeground="white",
            relief="flat",
            highlightthickness=1,
            highlightbackground=Theme.BORDER,
            font=("Consolas", 11),
            exportselection=False,
        )
        self.file_listbox.grid(row=0, column=0, sticky="nsew")

        file_scroll = tk.Scrollbar(
            list_frame,
            orient="vertical",
            command=self.file_listbox.yview,
        )
        file_scroll.grid(row=0, column=1, sticky="ns")
        self.file_listbox.configure(yscrollcommand=file_scroll.set)

        buttons = ctk.CTkFrame(
            list_card.body,
            fg_color="transparent",
        )
        buttons.grid(row=1, column=0, sticky="ew", pady=(10, 0))

        ctk.CTkButton(
            buttons,
            text="Add / Replace Current",
            fg_color=Theme.PRIMARY,
            hover_color=Theme.PRIMARY_HOVER,
            command=self.add_current_character,
        ).pack(side="left", padx=(0, 7))

        ctk.CTkButton(
            buttons,
            text="Load into Editor",
            fg_color=Theme.INPUT,
            hover_color=Theme.BORDER,
            command=self.load_selected_character,
        ).pack(side="left", padx=7)

        ctk.CTkButton(
            buttons,
            text="Delete",
            fg_color=Theme.DANGER,
            hover_color="#A64C4C",
            command=self.remove_selected_character,
        ).pack(side="left", padx=7)

        ctk.CTkButton(
            buttons,
            text="Clear",
            fg_color=Theme.INPUT,
            hover_color=Theme.BORDER,
            command=self.clear_character_file,
        ).pack(side="right")

        project_card = Card(
            page,
            "Project",
            "Save the character list and current values to a JSON file.",
        )
        project_card.pack(fill="x", padx=4, pady=(0, 14))

        ctk.CTkButton(
            project_card.body,
            text="Save Project",
            fg_color=Theme.INPUT,
            hover_color=Theme.BORDER,
            command=self.save_project,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            project_card.body,
            text="Open Project",
            fg_color=Theme.INPUT,
            hover_color=Theme.BORDER,
            command=self.load_project,
        ).pack(side="left")

        self.file_count_label = ctk.CTkLabel(
            project_card.body,
            text="0 characters",
            text_color=Theme.MUTED,
        )
        self.file_count_label.pack(side="right")

    # ------------------------------------------------------------------
    # Composants de formulaire
    # ------------------------------------------------------------------
    def _entry_row(
        self,
        parent,
        row: int,
        label: str,
        variable: tk.StringVar,
        help_text: str = "",
    ) -> ctk.CTkEntry:
        label_frame = ctk.CTkFrame(parent, fg_color="transparent")
        label_frame.grid(
            row=row,
            column=0,
            sticky="nw",
            padx=(0, 14),
            pady=8,
        )

        ctk.CTkLabel(
            label_frame,
            text=label,
            text_color=Theme.TEXT,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w")

        if help_text:
            ctk.CTkLabel(
                label_frame,
                text=help_text,
                text_color=Theme.MUTED,
                justify="left",
                wraplength=235,
                font=ctk.CTkFont(size=10),
            ).pack(anchor="w", pady=(2, 0))

        entry = ctk.CTkEntry(
            parent,
            textvariable=variable,
            height=39,
            fg_color=Theme.INPUT,
            border_color=Theme.BORDER,
        )
        entry.grid(
            row=row,
            column=1,
            sticky="ew",
            padx=8,
            pady=8,
        )
        return entry

    def _combo_row(
        self,
        parent,
        row: int,
        label: str,
        variable: tk.StringVar,
        values: list[str],
    ) -> ctk.CTkComboBox:
        ctk.CTkLabel(
            parent,
            text=label,
            text_color=Theme.TEXT,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(
            row=row,
            column=0,
            sticky="w",
            padx=(0, 14),
            pady=8,
        )

        combo = ctk.CTkComboBox(
            parent,
            variable=variable,
            values=values,
            height=39,
            fg_color=Theme.INPUT,
            border_color=Theme.BORDER,
            button_color=Theme.PRIMARY_DARK,
            button_hover_color=Theme.PRIMARY,
            state="readonly",
        )
        combo.grid(
            row=row,
            column=1,
            sticky="ew",
            padx=8,
            pady=8,
        )
        return combo

    # ------------------------------------------------------------------
    # Navigation et états
    # ------------------------------------------------------------------
    def show_page(self, key: str) -> None:
        """Display one page and fully hide all others."""
        if key not in self.pages:
            return

        self.current_page = key

        # CTkScrollableFrame contient son propre Canvas. La méthode la plus
        # fiable consiste à retirer toutes les pages du conteneur avant de
        # remettre uniquement la page demandée.
        for page in self.pages.values():
            page.pack_forget()

        selected_page = self.pages[key]
        selected_page.pack(
            fill="both",
            expand=True,
        )

        # Force le recalcul de la disposition avant le rafraîchissement.
        self.page_container.update_idletasks()
        selected_page.update_idletasks()

        for page_key, button in self.nav_buttons.items():
            button.configure(
                fg_color=Theme.PRIMARY if page_key == key else "transparent"
            )

        title, subtitle = self.PAGE_META[key]
        self.page_title_label.configure(text=title)
        self.page_subtitle_label.configure(text=subtitle)

        # Replace la page en haut lorsqu'on revient dessus.
        try:
            selected_page._parent_canvas.yview_moveto(0)
        except AttributeError:
            pass

    def _set_controls_state(self, controls: list, enabled: bool) -> None:
        for control in controls:
            if isinstance(control, TraitChipEditor):
                control.set_enabled(enabled)
                continue

            try:
                if isinstance(control, ctk.CTkComboBox):
                    control.configure(
                        state="readonly" if enabled else "disabled"
                    )
                else:
                    control.configure(
                        state="normal" if enabled else "disabled"
                    )
            except (tk.TclError, ValueError):
                pass

    def _toggle_leader_controls(self) -> None:
        self._set_controls_state(
            self.leader_controls,
            self.leader_enabled_var.get(),
        )
        self._queue_validation()

    def _toggle_military_controls(self) -> None:
        self._set_controls_state(
            self.military_controls,
            self.military_enabled_var.get(),
        )
        self._queue_validation()

    def _toggle_advisor_controls(self) -> None:
        self._set_controls_state(
            self.advisor_controls,
            self.advisor_enabled_var.get(),
        )
        self._queue_validation()

    # ------------------------------------------------------------------
    # Portrait
    # ------------------------------------------------------------------
    def choose_portrait(self) -> None:
        filename = filedialog.askopenfilename(
            title="Choose a Portrait",
            filetypes=[
                ("Compatible Images", "*.png *.jpg *.jpeg *.webp *.dds"),
                ("PNG", "*.png"),
                ("JPEG", "*.jpg *.jpeg"),
                ("DDS", "*.dds"),
                ("All Files", "*.*"),
            ],
        )
        if not filename:
            return

        self.portrait_source_var.set(filename)
        self._load_portrait_preview(Path(filename))

    def clear_portrait(self) -> None:
        self.portrait_source_var.set("")
        self._load_portrait_preview(
            self.assets_dir / "default_portrait.png"
        )

    def _load_portrait_preview(self, path: Path) -> None:
        try:
            image = Image.open(path).convert("RGBA")
            image.thumbnail((310, 400), Image.Resampling.LANCZOS)

            canvas = Image.new(
                "RGBA",
                (336, 432),
                (32, 42, 53, 255),
            )
            x = (canvas.width - image.width) // 2
            y = (canvas.height - image.height) // 2
            canvas.alpha_composite(image, (x, y))

            self.portrait_preview_image = ctk.CTkImage(
                light_image=canvas,
                dark_image=canvas,
                size=(168, 216),
            )
            self.portrait_preview_label.configure(
                image=self.portrait_preview_image
            )
        except OSError as error:
            messagebox.showerror(
                "Invalid Image",
                f"Unable to open this image:\n{error}",
            )

    # ------------------------------------------------------------------
    # Bibliothèque
    # ------------------------------------------------------------------
    def _select_library_category(self, name: str) -> None:
        self.library_current_category = name
        self.library_category_title.configure(text=name)

        for title, button in self.library_category_buttons.items():
            button.configure(
                fg_color=Theme.PRIMARY if title == name else "transparent"
            )

        self.library_search_var.set("")
        self._refresh_library_list()

    def _refresh_library_list(self) -> None:
        data = self.library_categories[self.library_current_category]
        values = data["values"]
        query = self.library_search_var.get().strip().lower()

        if query:
            values = [value for value in values if query in value.lower()]

        self.library_listbox.delete(0, tk.END)
        for value in values:
            self.library_listbox.insert(tk.END, value)

        self.library_details.delete("1.0", tk.END)

    def _selected_library_trait(self) -> str | None:
        selection = self.library_listbox.curselection()
        if not selection:
            return None
        return self.library_listbox.get(selection[0])

    def _trait_metadata(self, trait: str) -> tuple[dict, str]:
        unit_definitions = self.unit_leader_library.get("definitions", {})
        command_definitions = self.army_command_library.get("definitions", {})
        rumburg_definitions = self.rumburg_trait_library.get(
            "definitions",
            {},
        )

        if trait in unit_definitions:
            return unit_definitions[trait], "unit"
        if trait in command_definitions:
            return command_definitions[trait], "command"
        if trait in rumburg_definitions:
            return rumburg_definitions[trait], "rumburg"
        return {}, "generic"

    def _show_library_details(self) -> None:
        trait = self._selected_library_trait()
        self.library_details.delete("1.0", tk.END)

        if not trait:
            return

        data, source_type = self._trait_metadata(trait)

        lines = [f"Name: {trait}"]

        if source_type == "unit":
            lines.extend(
                [
                    f"Type: {data.get('leader_type', 'unknown')}",
                    f"Category: {data.get('trait_type', 'basic_trait')}",
                ]
            )

            if data.get("cost"):
                lines.append(f"XP Cost: {data['cost']}")

            parents = (
                data.get("parents_any", [])
                + data.get("parents_all", [])
            )
            if parents:
                lines.append(
                    "Requirements: " + ", ".join(dict.fromkeys(parents))
                )

            exclusions = data.get("mutually_exclusive", [])
            if exclusions:
                lines.append(
                    "Mutually exclusive with: " + ", ".join(exclusions)
                )

            advisor = data.get("advisor_mappings", {})
            associated = [
                advisor.get("slot", ""),
                advisor.get("specialist", ""),
                advisor.get("expert", ""),
                advisor.get("genius", ""),
            ]
            associated = [item for item in associated if item]
            if associated:
                lines.append(
                    "Associated Advisor: " + ", ".join(associated)
                )

        elif source_type == "command":
            lines.append(
                "Category: "
                + data.get("category", self.library_current_category)
            )

        elif source_type == "rumburg":
            lines.extend(
                [
                    "Title: " + data.get("display_name", trait),
                    "Category: "
                    + data.get("category_label", "Custom Rumburg Trait"),
                ]
            )

            modifiers = data.get("direct_modifiers", [])
            if modifiers:
                lines.extend(
                    [
                        "",
                        "Direct Modifiers:",
                        *[
                            "• "
                            + modifier.get("modifier", "")
                            + " = "
                            + modifier.get("value", "")
                            for modifier in modifiers
                        ],
                    ]
                )

            duplicate_count = int(data.get("duplicate_count", 1))
            if duplicate_count > 1:
                lines.extend(
                    [
                        "",
                        (
                            "Warning: this identifier appears "
                            f"{duplicate_count} times in the source file."
                        ),
                    ]
                )

        definition = data.get("definition", "")
        if definition:
            lines.extend(["", "HOI4 Definition:", definition])
        else:
            lines.extend(
                [
                    "",
                    "Trait included in the program's internal library.",
                ]
            )

        self.library_details.insert("1.0", "\n".join(lines))

    def _copy_library_trait(self) -> None:
        trait = self._selected_library_trait()
        if not trait:
            messagebox.showwarning(
                "No Trait Selected",
                "Select a trait from the list.",
            )
            return

        self.clipboard_clear()
        self.clipboard_append(trait)
        messagebox.showinfo(
            "Trait Copied",
            f"The trait “{trait}” has been copied.",
        )

    def _use_library_trait(self) -> None:
        trait = self._selected_library_trait()
        if not trait:
            messagebox.showwarning(
                "No Trait Selected",
                "Select a trait from the list.",
            )
            return

        target = self.library_categories[
            self.library_current_category
        ]["target"]

        if target == "leader":
            self.leader_enabled_var.set(True)
            self.leader_traits_editor.add_trait(trait)
            self._toggle_leader_controls()
            self.show_page("leader")

        elif target == "army_personality":
            self.military_enabled_var.set(True)
            self.military_traits_editor.add_trait(trait)
            self._toggle_military_controls()
            self.show_page("military")

        elif target == "field_marshal":
            self.military_enabled_var.set(True)
            self.military_role_var.set("field_marshal")
            self.military_traits_editor.add_trait(trait)
            self._toggle_military_controls()
            self.show_page("military")

        elif target == "corps_commander":
            self.military_enabled_var.set(True)
            self.military_role_var.set("corps_commander")
            self.military_traits_editor.add_trait(trait)
            self._toggle_military_controls()
            self.show_page("military")

        elif target == "army_chief":
            self.advisor_enabled_var.set(True)
            self.advisor_slot_var.set("army_chief")
            self.advisor_traits_editor.add_trait(trait)
            self._toggle_advisor_controls()
            self.show_page("advisor")

        elif target == "high_command":
            self.advisor_enabled_var.set(True)
            self.advisor_slot_var.set("high_command")
            self.advisor_traits_editor.add_trait(trait)
            self._toggle_advisor_controls()
            self.show_page("advisor")

        elif target == "theorist":
            self.advisor_enabled_var.set(True)
            self.advisor_slot_var.set("theorist")
            self.advisor_traits_editor.add_trait(trait)
            self._toggle_advisor_controls()
            self.show_page("advisor")

        else:
            self.advisor_enabled_var.set(True)
            self.advisor_traits_editor.add_trait(trait)
            self._toggle_advisor_controls()
            self.show_page("advisor")

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def _bind_validation(self) -> None:
        variables = [
            self.tag_var,
            self.identifier_var,
            self.name_key_var,
            self.display_name_var,
            self.portrait_key_var,
            self.leader_enabled_var,
            self.ideology_family_var,
            self.ideology_var,
            self.leader_traits_var,
            self.expire_var,
            self.description_var,
            self.military_enabled_var,
            self.military_role_var,
            self.military_traits_var,
            self.skill_var,
            self.attack_var,
            self.defense_var,
            self.planning_var,
            self.logistics_var,
            self.advisor_enabled_var,
            self.advisor_slot_var,
            self.idea_token_var,
            self.advisor_traits_var,
            self.advisor_cost_var,
        ]

        for variable in variables:
            variable.trace_add("write", self._queue_validation)

    def _queue_validation(self, *_args) -> None:
        if self._validation_after_id:
            self.after_cancel(self._validation_after_id)
        self._validation_after_id = self.after(
            250,
            self._validate_form,
        )

    def _validate_form(self, show_dialog: bool = False) -> list[str]:
        self._validation_after_id = None
        errors: list[str] = []

        tag = self.tag_var.get().strip().upper()
        identifier = self.identifier_var.get().strip().lower()

        info_errors = []
        if not re.fullmatch(r"[A-Z0-9]{3}", tag):
            info_errors.append("The country tag must contain exactly 3 characters.")
        if not re.fullmatch(r"[a-z0-9_]+", identifier):
            info_errors.append(
                "The identifier may only use a-z, 0-9, and _."
            )
        if not self.name_key_var.get().strip():
            info_errors.append("The localisation key is required.")
        if not self.portrait_key_var.get().strip():
            info_errors.append("The GFX key is required.")

        if info_errors:
            self.info_status.set_status(
                f"{len(info_errors)} error(s)",
                "danger",
            )
            errors.extend(info_errors)
        else:
            self.info_status.set_status("Information Valid", "success")

        if self.leader_enabled_var.get():
            leader_errors = []

            family_key = self.ideology_family_var.get().strip()
            ideology_key = self.ideology_var.get().strip()

            if family_key not in self.ideology_family_by_key:
                leader_errors.append(
                    "The selected ideology family is unknown."
                )
            elif ideology_key not in self._family_subtype_keys(family_key):
                leader_errors.append(
                    "The sub-ideology does not match the selected family."
                )

            if not ideology_key:
                leader_errors.append("A sub-ideology is required.")

            if not re.fullmatch(
                r"\d{4}\.\d{1,2}\.\d{1,2}",
                self.expire_var.get().strip(),
            ):
                leader_errors.append(
                    "The expiration date must use the YYYY.M.D format."
                )

            if leader_errors:
                self.leader_status.set_status(
                    f"{len(leader_errors)} error(s)",
                    "danger",
                )
                errors.extend(leader_errors)
            else:
                self.leader_status.set_status("Country Leader Valid", "success")
        else:
            self.leader_status.set_status("Role Disabled", "neutral")

        if self.military_enabled_var.get():
            military_errors = []
            for label, variable in [
                ("Skill", self.skill_var),
                ("Attack", self.attack_var),
                ("Defense", self.defense_var),
                ("Planning", self.planning_var),
                ("Logistics", self.logistics_var),
            ]:
                try:
                    value = int(variable.get())
                    if not 1 <= value <= 10:
                        raise ValueError
                except ValueError:
                    military_errors.append(
                        f"{label} must be between 1 and 10."
                    )

            if military_errors:
                self.military_status.set_status(
                    f"{len(military_errors)} error(s)",
                    "danger",
                )
                errors.extend(military_errors)
            else:
                self.military_status.set_status(
                    "Commander Valid",
                    "success",
                )
        else:
            self.military_status.set_status("Role Disabled", "neutral")

        if self.advisor_enabled_var.get():
            advisor_errors = []
            if not self.idea_token_var.get().strip():
                advisor_errors.append("The Idea Token is required.")
            try:
                if int(self.advisor_cost_var.get()) < 0:
                    raise ValueError
            except ValueError:
                advisor_errors.append(
                    "The political power cost must be a positive integer."
                )

            if advisor_errors:
                self.advisor_status.set_status(
                    f"{len(advisor_errors)} error(s)",
                    "danger",
                )
                errors.extend(advisor_errors)
            else:
                self.advisor_status.set_status(
                    "Advisor Valid",
                    "success",
                )
        else:
            self.advisor_status.set_status("Role Disabled", "neutral")

        if errors:
            self.validation_badge.set_status(
                f"{len(errors)} error(s)",
                "danger",
            )
        else:
            self.validation_badge.set_status("Ready to Generate", "success")

        if show_dialog:
            if errors:
                messagebox.showerror(
                    "Validation",
                    "\n".join(f"• {error}" for error in errors),
                )
            else:
                messagebox.showinfo(
                    "Validation",
                    "All active information is valid.",
                )

        return errors

    # ------------------------------------------------------------------
    # Construction et aperçu
    # ------------------------------------------------------------------
    def _build_data(self, validate: bool = True) -> CharacterData:
        if validate:
            errors = self._validate_form()
            if errors:
                raise ValueError("\n".join(errors))

        return CharacterData(
            tag=self.tag_var.get().strip().upper(),
            identifier=self.identifier_var.get().strip().lower(),
            name_key=self.name_key_var.get().strip(),
            portrait_key=self.portrait_key_var.get().strip(),
            display_name=self.display_name_var.get().strip(),
            portrait_source=self.portrait_source_var.get().strip(),
            leader=LeaderData(
                enabled=self.leader_enabled_var.get(),
                ideology=self.ideology_var.get().strip(),
                traits=self.leader_traits_var.get().strip(),
                expire=self.expire_var.get().strip(),
                description=self.description_var.get().strip(),
            ),
            military=MilitaryData(
                enabled=self.military_enabled_var.get(),
                role=self.military_role_var.get().strip(),
                traits=self.military_traits_var.get().strip(),
                skill=int(self.skill_var.get()),
                attack=int(self.attack_var.get()),
                defense=int(self.defense_var.get()),
                planning=int(self.planning_var.get()),
                logistics=int(self.logistics_var.get()),
            ),
            advisor=AdvisorData(
                enabled=self.advisor_enabled_var.get(),
                slot=self.advisor_slot_var.get().strip(),
                idea_token=self.idea_token_var.get().strip(),
                traits=self.advisor_traits_var.get().strip(),
                cost=int(self.advisor_cost_var.get()),
            ),
        )

    def _characters_for_preview(self) -> list[CharacterData]:
        if (
            self.preview_mode_var.get() == "Full file"
            and self.characters_in_file
        ):
            return self.characters_in_file

        try:
            return [self._build_data()]
        except ValueError:
            return []

    def update_preview(self) -> None:
        characters = self._characters_for_preview()
        if not characters:
            return

        code = self.generator.generate_characters_file(characters)
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert("1.0", code)

        lines = len(code.splitlines())
        count = len(characters)
        self.preview_info_label.configure(
            text=f"{lines} lines • {count} character(s)"
        )

    def copy_preview(self) -> None:
        code = self.preview_text.get("1.0", tk.END).strip()
        if not code:
            self.update_preview()
            code = self.preview_text.get("1.0", tk.END).strip()

        if not code:
            return

        self.clipboard_clear()
        self.clipboard_append(code)
        self._increment_stat("codes_copied")
        messagebox.showinfo(
            "Code Copied",
            "The visible code has been copied to the clipboard.",
        )

    # ------------------------------------------------------------------
    # Gestion du fichier et projets
    # ------------------------------------------------------------------
    def _refresh_file_list(self) -> None:
        self.file_listbox.delete(0, tk.END)

        for character in self.characters_in_file:
            roles = ", ".join(character.roles) or "No role"
            self.file_listbox.insert(
                tk.END,
                f"{character.character_key:<28}  {roles}",
            )

        count = len(self.characters_in_file)
        self.file_count_label.configure(
            text=f"{count} character{'s' if count != 1 else ''}"
        )

    def add_current_character(self) -> None:
        try:
            character = self._build_data()
        except ValueError as error:
            messagebox.showerror("Invalid Data", str(error))
            return

        replaced = False
        for index, existing in enumerate(self.characters_in_file):
            if existing.character_key == character.character_key:
                self.characters_in_file[index] = character
                replaced = True
                break

        if not replaced:
            self.characters_in_file.append(character)
            self._increment_stat("characters_generated")

        self._refresh_file_list()
        self.preview_mode_var.set("Full file")
        self.update_preview()
        self.show_page("file")

        messagebox.showinfo(
            "Character Saved",
            (
                f"{character.character_key} was "
                + ("replaced." if replaced else "added to the file.")
            ),
        )

    def remove_selected_character(self) -> None:
        selection = self.file_listbox.curselection()
        if not selection:
            return

        del self.characters_in_file[selection[0]]
        self._refresh_file_list()
        self.update_preview()

    def clear_character_file(self) -> None:
        if not self.characters_in_file:
            return

        if not messagebox.askyesno(
            "Clear File",
            "Delete all characters from the list?",
        ):
            return

        self.characters_in_file.clear()
        self._refresh_file_list()
        self.update_preview()

    def load_selected_character(self) -> None:
        selection = self.file_listbox.curselection()
        if not selection:
            messagebox.showwarning(
                "No Selection",
                "Select a character.",
            )
            return

        self._apply_character(self.characters_in_file[selection[0]])
        self.show_page("information")

    def _apply_character(self, character: CharacterData) -> None:
        self.auto_keys_var.set(False)

        self.tag_var.set(character.tag)
        self.identifier_var.set(character.identifier)
        self.name_key_var.set(character.name_key)
        self.display_name_var.set(character.display_name)
        self.portrait_key_var.set(character.portrait_key)
        self.portrait_source_var.set(character.portrait_source)

        self.leader_enabled_var.set(character.leader.enabled)
        self._set_ideology_from_key(character.leader.ideology)
        self.leader_traits_var.set(character.leader.traits)
        self.expire_var.set(character.leader.expire)
        self.description_var.set(character.leader.description)

        self.military_enabled_var.set(character.military.enabled)
        self.military_role_var.set(character.military.role)
        self.military_traits_var.set(character.military.traits)
        self.skill_var.set(str(character.military.skill))
        self.attack_var.set(str(character.military.attack))
        self.defense_var.set(str(character.military.defense))
        self.planning_var.set(str(character.military.planning))
        self.logistics_var.set(str(character.military.logistics))

        self.advisor_enabled_var.set(character.advisor.enabled)
        self.advisor_slot_var.set(character.advisor.slot)
        self.idea_token_var.set(character.advisor.idea_token)
        self.advisor_traits_var.set(character.advisor.traits)
        self.advisor_cost_var.set(str(character.advisor.cost))

        if character.portrait_source:
            self._load_portrait_preview(Path(character.portrait_source))
        else:
            self.clear_portrait()

        self._toggle_leader_controls()
        self._toggle_military_controls()
        self._toggle_advisor_controls()
        self._validate_form()

    @staticmethod
    def _character_from_dict(data: dict) -> CharacterData:
        return CharacterData(
            tag=data.get("tag", "RUM"),
            identifier=data.get("identifier", "new_character"),
            name_key=data.get("name_key", "RUM_new_character"),
            portrait_key=data.get(
                "portrait_key",
                "GFX_portrait_RUM_new_character",
            ),
            display_name=data.get("display_name", "New Character"),
            portrait_source=data.get("portrait_source", ""),
            leader=LeaderData(**data.get("leader", {})),
            military=MilitaryData(**data.get("military", {})),
            advisor=AdvisorData(**data.get("advisor", {})),
        )

    def save_project(self) -> None:
        try:
            current = self._build_data(validate=False)
        except (ValueError, TypeError):
            current = None

        filename = filedialog.asksaveasfilename(
            title="Save Project",
            defaultextension=".hoi4char.json",
            filetypes=[
                ("HOI4 Character Creator Project", "*.hoi4char.json"),
                ("JSON", "*.json"),
            ],
        )
        if not filename:
            return

        payload = {
            "app_version": self.APP_VERSION,
            "file_name": self.file_name_var.get(),
            "current_character": asdict(current) if current else None,
            "characters": [
                asdict(character)
                for character in self.characters_in_file
            ],
        }

        try:
            Path(filename).write_text(
                json.dumps(payload, indent=4, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as error:
            messagebox.showerror(
                "Error",
                f"Unable to save the project:\n{error}",
            )
            return

        messagebox.showinfo(
            "Project Saved",
            f"Project Saved dans :\n{filename}",
        )

    def load_project(self) -> None:
        filename = filedialog.askopenfilename(
            title="Open Project",
            filetypes=[
                ("HOI4 Character Creator Project", "*.hoi4char.json"),
                ("JSON", "*.json"),
            ],
        )
        if not filename:
            return

        try:
            payload = json.loads(
                Path(filename).read_text(encoding="utf-8")
            )
            self.file_name_var.set(
                payload.get("file_name", "RUM_characters")
            )
            self.characters_in_file = [
                self._character_from_dict(item)
                for item in payload.get("characters", [])
            ]

            current = payload.get("current_character")
            if current:
                self._apply_character(
                    self._character_from_dict(current)
                )
        except (OSError, ValueError, TypeError) as error:
            messagebox.showerror(
                "Invalid Project",
                f"Unable to open this project:\n{error}",
            )
            return

        self._refresh_file_list()
        self.update_preview()
        messagebox.showinfo(
            "Project Loaded",
            f"{len(self.characters_in_file)} character(s) loaded.",
        )

    # ------------------------------------------------------------------
    # Export du mod
    # ------------------------------------------------------------------
    def export_to_mod(self) -> None:
        if self.characters_in_file:
            characters = self.characters_in_file
        else:
            try:
                characters = [self._build_data()]
            except ValueError as error:
                messagebox.showerror("Invalid Data", str(error))
                return

        directory = filedialog.askdirectory(
            title="Choose the HOI4 Mod Root Folder",
        )
        if not directory:
            return

        mod_root = Path(directory)
        base_name = (
            self.file_name_var.get().strip()
            or f"{characters[0].tag.upper()}_characters"
        )

        character_dir = mod_root / "common" / "characters"
        localisation_dir = mod_root / "localisation" / "english"
        interface_dir = mod_root / "interface"

        character_dir.mkdir(parents=True, exist_ok=True)
        localisation_dir.mkdir(parents=True, exist_ok=True)
        interface_dir.mkdir(parents=True, exist_ok=True)

        character_path = character_dir / f"{base_name}.txt"
        localisation_path = (
            localisation_dir / f"{base_name}_l_english.yml"
        )

        sprite_entries: list[tuple[str, str]] = []
        portrait_errors: list[str] = []

        for character in characters:
            if not character.portrait_source:
                continue

            source = Path(character.portrait_source)
            if not source.exists():
                portrait_errors.append(
                    f"{character.character_key}: file not found"
                )
                continue

            destination_dir = (
                mod_root
                / "gfx"
                / "leaders"
                / character.tag.upper()
            )
            destination_dir.mkdir(parents=True, exist_ok=True)
            destination = (
                destination_dir
                / f"{character.character_key}.dds"
            )

            try:
                image = Image.open(source).convert("RGBA")
                image.save(destination)
                texture_path = (
                    f"gfx/leaders/{character.tag.upper()}/"
                    f"{character.character_key}.dds"
                )
                sprite_entries.append(
                    (character.portrait_key, texture_path)
                )
            except OSError as error:
                portrait_errors.append(
                    f"{character.character_key}: {error}"
                )

        try:
            character_path.write_text(
                self.generator.generate_characters_file(characters),
                encoding="utf-8",
            )
            localisation_path.write_text(
                self.generator.generate_localisation_file(characters),
                encoding="utf-8-sig",
            )

            interface_path = None
            if sprite_entries:
                interface_path = interface_dir / f"{base_name}.gfx"
                interface_path.write_text(
                    self.generator.generate_sprite_file(
                        sprite_entries
                    ),
                    encoding="utf-8",
                )
        except OSError as error:
            messagebox.showerror(
                "Export Error",
                f"Unable to write the files:\n{error}",
            )
            return

        self._increment_stat("exports_completed")

        summary = [
            "Export completed.",
            "",
            str(character_path),
            str(localisation_path),
        ]

        if sprite_entries:
            summary.append(str(interface_path))

        if portrait_errors:
            summary.extend(
                [
                    "",
                    "Portraits not exported:",
                    *portrait_errors,
                ]
            )

        messagebox.showinfo(
            "Export Completed",
            "\n".join(summary),
        )

    # ------------------------------------------------------------------
    # Réinitialisation et statistiques
    # ------------------------------------------------------------------
    def reset_example(self) -> None:
        self.auto_keys_var.set(True)
        self.tag_var.set("RUM")
        self.identifier_var.set("new_character")
        self.display_name_var.set("New Character")
        self._sync_keys()

        self.leader_enabled_var.set(False)
        self._set_ideology_from_key(
            "paternal_despotism_rumburgian_monarchism"
        )
        self.leader_traits_var.set("popular_queen")
        self.expire_var.set("1965.1.1")

        self.military_enabled_var.set(False)
        self.military_role_var.set("corps_commander")
        self.military_traits_var.set(
            "organizer, winter_specialist"
        )
        self.skill_var.set("3")
        self.attack_var.set("3")
        self.defense_var.set("3")
        self.planning_var.set("3")
        self.logistics_var.set("3")

        self.advisor_enabled_var.set(False)
        self.advisor_slot_var.set("army_chief")
        self.advisor_traits_var.set(
            "army_chief_offensive_2"
        )
        self.advisor_cost_var.set("100")

        self.clear_portrait()
        self._toggle_leader_controls()
        self._toggle_military_controls()
        self._toggle_advisor_controls()

        self.preview_mode_var.set("Current character")
        self.preview_text.delete("1.0", tk.END)
        self.preview_info_label.configure(
            text="0 lines • 0 characters"
        )
        self._validate_form()

    def _update_statistics_labels(self) -> None:
        if not hasattr(self, "home_stat_labels"):
            return

        for key, label in self.home_stat_labels.items():
            label.configure(
                text=str(self.statistics.get(key, 0))
            )


def main() -> None:
    app = HOI4CharacterCreator()
    app.mainloop()
