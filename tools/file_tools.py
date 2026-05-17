from pathlib import Path

from config.config import TOOL_CONFIG


# ============================================================
# WRITE FILE
# ============================================================

def write_file(
    path: str,
    content: str
) -> str:
    """
    Create or overwrite a file safely.
    """

    file_path = Path(path)

    # --------------------------------------------------------
    # Validate extension
    # --------------------------------------------------------

    if (
        file_path.suffix
        not in TOOL_CONFIG.ALLOWED_FILE_EXTENSIONS
    ):
        raise ValueError(
            f"File extension '{file_path.suffix}' "
            f"is not allowed."
        )

    # --------------------------------------------------------
    # Validate file size
    # --------------------------------------------------------

    encoded_size = len(content.encode("utf-8"))

    if (
        encoded_size >
        TOOL_CONFIG.MAX_FILE_WRITE_SIZE
    ):
        raise ValueError(
            "Content exceeds maximum allowed file size."
        )

    # --------------------------------------------------------
    # Ensure parent directory exists
    # --------------------------------------------------------

    file_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Write file
    # --------------------------------------------------------

    with open(file_path, "w", encoding="utf-8") as file:

        file.write(content)

    return f"File written successfully: {path}"


# ============================================================
# READ FILE
# ============================================================

def read_file(
    path: str
) -> str:
    """
    Read contents of a file safely.
    """

    file_path = Path(path)

    if not file_path.exists():

        raise FileNotFoundError(
            f"File does not exist: {path}"
        )

    with open(file_path, "r", encoding="utf-8") as file:

        return file.read()


# ============================================================
# LIST DIRECTORY
# ============================================================

def list_dir(
    path: str = "."
) -> list:
    """
    List files and directories.
    """

    dir_path = Path(path)

    if not dir_path.exists():

        raise FileNotFoundError(
            f"Directory does not exist: {path}"
        )

    if not dir_path.is_dir():

        raise ValueError(
            f"Path is not a directory: {path}"
        )

    items = []

    for item in dir_path.iterdir():

        items.append({
            "name": item.name,
            "type": (
                "directory"
                if item.is_dir()
                else "file"
            )
        })

    return items
