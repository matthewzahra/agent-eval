from enum import Enum

# defines the available actions to the agent
class Action(Enum):
    WRITE_FILE = "write_file"
    OPEN_FILE = "open_file"
    DELETE_FILE = "delete_file"
    COMPLETED="completed"