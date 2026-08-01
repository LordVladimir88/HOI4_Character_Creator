from __future__ import annotations

import ctypes
import sys


APP_USER_MODEL_ID = "KingdomOfRumburg.HOI4CharacterCreator.2.4.0"


def configure_windows_app_id() -> None:
    """Make Windows use the application icon instead of the Python icon."""
    if sys.platform != "win32":
        return

    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            APP_USER_MODEL_ID
        )
    except (AttributeError, OSError):
        pass


def main() -> None:
    configure_windows_app_id()

    try:
        from ui.app import main as run_app
    except ModuleNotFoundError as error:
        missing = error.name or "a dependency"
        print(
            "\nMissing dependency: "
            f"{missing}\n\n"
            "Install the dependencies with:\n"
            "    python -m pip install -r requirements.txt\n"
        )
        raise SystemExit(1) from error

    run_app()


if __name__ == "__main__":
    main()
