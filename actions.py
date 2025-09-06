from enum import Enum

class Action(Enum):
    WRITE_FILE = "write_file"
    EDIT_FILE = "edit_file"
    CREATE_DIR = "create_dir"
    OPEN_FILE = "open_file"
    DELETE_FILE = "delete_file"
    