# HOI4 Character Creator

**Version 2.4.0 — English Edition**

HOI4 Character Creator is a desktop tool for creating and organizing
Hearts of Iron IV character definitions for the **Beneath the Maroon Sky**
Rumburg project.

The application uses a modern CustomTkinter interface with a permanent
code preview, portrait management, ideology selection, trait libraries,
multi-character files, and direct export to a HOI4 mod folder.

## Main Features

- English user interface;
- modern dark interface inspired by grand-strategy modding tools;
- country leader, military commander, and advisor creation;
- 8 ideology families and 111 sub-ideologies;
- complete land commander trait library;
- reorganized Rumburg trait library;
- search, detailed definitions, and double-click trait insertion;
- multiple characters in one project file;
- JSON project save and load;
- automatic localisation generation;
- automatic portrait conversion to DDS;
- automatic `interface/*.gfx` generation;
- Windows application icon and PyInstaller build files.

## Trait Library Organization

### Commanders

- Army Personality;
- Field Marshal;
- Corps Commander.

### Advisors

- Army Chief;
- Army High Command;
- Advisor Trait.

### Rumburg Politics

- RUM Leaders;
- RUM Ministers;
- RUM Ideologies;
- RUM Influential Figures;
- RUM Negative Traits.

### Military and Industry

- RUM Theorists;
- RUM Aviation;
- RUM Armor & Land;
- RUM Navy;
- RUM Companies.

Duplicate identifiers are removed from the visible library. The original
source definitions remain available in the `sources` directory.

## Installation

### Windows automatic installation

Run:

```text
install_windows.bat
```

Then launch:

```text
run_windows.bat
```

### Manual installation

```bash
python -m pip install -r requirements.txt
python main.py
```

## Building the Windows Executable

Run:

```text
build_exe_windows.bat
```

Or use PowerShell:

```powershell
.\build_exe_windows.ps1
```

The executable will be created at:

```text
dist/HOI4 Character Creator.exe
```

## Portraits

Supported input formats:

- PNG;
- JPG/JPEG;
- WEBP;
- DDS.

During export, portraits are converted to DDS and placed in:

```text
gfx/leaders/TAG/
```

The matching GFX definition is generated in:

```text
interface/
```

## Ideologies

The application reads ideology data from:

```text
data/ideologies.json
sources/00_ideologies.txt
```

A character uses the complete sub-ideology key, for example:

```hoi4
country_leader = {
    ideology = paternal_despotism_rumburgian_monarchism
}
```

Legacy project values containing only a main ideology family are mapped
to the generic subtype of that family.

## Project Files

Project files use the extension:

```text
.hoi4char.json
```

A project stores:

- the current character;
- saved characters;
- export base name;
- leader, commander, and advisor settings;
- selected portrait path.

## Included Data

```text
data/army_command_traits.json
data/unit_leader_traits.json
data/ideologies.json
data/rumburg_traits.json
sources/00_ideologies.txt
sources/Rumburg_Leaders_Trait.txt
sources/00_unit_leader_traits_source.txt
```

## Credits

A full credits page is available here:

[Open the Credits page](CREDITS.md)

### Core Credits

- **Project creator and lead developer:** Duke of Eskdaleton
- **Project:** Beneath the Maroon Sky — Rumburg
- **Application:** HOI4 Character Creator
- **Development correction:** OpenAI ChatGPT
- **Interface framework:** CustomTkinter
- **Image processing:** Pillow
- **Windows packaging:** PyInstaller

## Disclaimer

This is an unofficial fan-made modding tool.

Hearts of Iron IV, Suzerain, Rumburg, and all related names, settings,
trademarks, and intellectual properties belong to their respective owners.
This project is not affiliated with or endorsed by Paradox Interactive,
Paradox Development Studio, or Torpor Games.

## Version History

### 2.4.0

- translated the complete user interface into English;
- translated validation messages, dialogs, buttons, and file selectors;
- translated Windows installation and build scripts;
- rewrote the README in English;
- added a dedicated credits page.

### 2.3.1

- removed duplicate trait identifiers;
- reorganized theorists, aviation, land designers, naval designers, and
  companies into separate categories;
- added a scrollable category panel.

### 2.3.0

- integrated the Rumburg trait source file into the application library;
- added trait definitions, categories, modifiers, and double-click insertion.

### 2.2.0

- added 8 ideology families and 111 sub-ideologies;
- added separate family and subtype selectors;
- added legacy ideology compatibility.

### 2.0.3

- added the custom Windows icon;
- added AppUserModelID support;
- added PyInstaller build scripts.
