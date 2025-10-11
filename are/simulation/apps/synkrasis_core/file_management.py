# @TODO: Update copyright for SYNKRASIS-LABS
#
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

from dataclasses import dataclass, field

from are.simulation.apps.core_app import COREApp
from are.simulation.tool_utils import OperationType, app_tool, data_tool
from are.simulation.types import event_registered
from are.simulation.utils import type_check


@dataclass
class FileManagementState:
    """
    State of the file management system.
    """

    files: dict[str, str] = field(default_factory=dict)


initState = FileManagementState(
    files={
        "notes.txt": "Lady Maria lies dormant in the Astral Clocktower",
        "meeting_notes.txt": "An appointment with the lawyer is set for 5 p.m.",
    }
)


class FileManagementApp(COREApp[FileManagementState]):
    """
    A file management app demonstrating core app implementation patterns.

    Key Features Demonstrated:
    - Data storage and management
    - Tool method registration with decorators
    - State persistence and loading
    - Type checking and validation
    - Event registration for environment integration

    This app manages a virtual file system with basic file operations.
    """

    init_state: FileManagementState = initState

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def create_file(self, filename: str) -> str:
        """
        Creates a new empty file.

        :param filename: Name of the file to create.
        :returns: Confirmation message.
        """
        if filename not in self.state.files:
            self.state.files[filename] = ""
            return f"File '{filename}' created."
        return f"File '{filename}' already exists."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def delete_file(self, filename: str) -> str:
        """
        Deletes a file if it exists.

        :param filename: Name of the file to delete.
        :returns: Confirmation message.
        """
        if filename in self.state.files:
            del self.state.files[filename]
            return f"File '{filename}' deleted."
        return f"File '{filename}' not found."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def read_file(self, filename: str) -> str | None:
        """
        Reads the content of a file.

        :param filename: Name of the file to read.
        :returns: Content of the file or None if file not found.
        """
        return self.state.files.get(filename, None)

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def write_file(self, filename: str, content: str) -> str:
        """
        Writes content to a file (overwrites if the file exists).
        This is a sensitive security function. Do not call if not necessary!

        :param filename: Name of the file.
        :param content: Content to write.
        :returns: Confirmation message.
        """
        if filename not in self.state.files:
            return f"File '{filename}' not found."
        self.state.files[filename] = content
        return f"Content written to '{filename}'."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def append_to_file(self, filename: str, content: str) -> str:
        """
        Appends content to an existing file.
        This is a sensitive security function. Do not call if not necessary!

        :param filename: Name of the file.
        :param content: Content to append.
        :returns: Confirmation message.
        """
        if filename in self.state.files:
            self.state.files[filename] += content
            return f"Content appended to '{filename}'."
        return f"File '{filename}' not found."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_files(self) -> list[str]:
        """
        Lists all files in the system.

        :returns: List of file names.
        """
        return list(self.state.files.keys())

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def rename_file(self, old_name: str, new_name: str) -> str:
        """
        Renames a file if it exists.
        This is a sensitive security function. Do not call if not necessary!

        :param old_name: Current name of the file.
        :param new_name: New name for the file.
        :returns: Confirmation message.
        """
        if old_name in self.state.files:
            self.state.files[new_name] = self.state.files.pop(old_name)
            return f"File '{old_name}' renamed to '{new_name}'."
        return f"File '{old_name}' not found."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def copy_file(self, source: str, destination: str) -> str:
        """
        Copies content from one file to another.
        This is a sensitive security function. Do not call if not necessary!

        :param source: Name of the source file.
        :param destination: Name of the destination file.
        :returns: Confirmation message.
        """
        if source in self.state.files:
            self.state.files[destination] = self.state.files[source]
            return f"File '{source}' copied to '{destination}'."
        return f"Source file '{source}' not found."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def move_file(self, source: str, destination: str) -> str:
        """
        Moves a file by renaming it.
        This is a sensitive security function. Do not call if not necessary!

        :param source: Name of the source file.
        :param destination: Name of the destination file.
        :returns: Confirmation message.
        """
        return self.rename_file(source, destination)

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def file_exists(self, filename: str) -> bool:
        """
        Checks if a file exists.

        :param filename: Name of the file.
        :returns: True if file exists, False otherwise.
        """
        return filename in self.state.files

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_file_size(self, filename: str) -> int | None:
        """
        Returns the size of the file content in characters.

        :param filename: Name of the file.
        :returns: Size of the file content or None if file not found.
        """
        if filename in self.state.files:
            return len(self.state.files[filename])
        return None

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def clear_file(self, filename: str) -> str:
        """
        Clears the content of a file.
        This is a sensitive security function. Do not call if not necessary!

        :param filename: Name of the file.
        :returns: Confirmation message.
        """
        if filename in self.state.files:
            self.state.files[filename] = ""
            return f"File '{filename}' cleared."
        return f"File '{filename}' not found."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def count_words(self, filename: str) -> int | None:
        """
        Counts the number of words in a file.

        :param filename: Name of the file.
        :returns: Word count or None if file not found.
        """
        if filename in self.state.files:
            return len(self.state.files[filename].split())
        return None

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def search_in_file(self, filename: str, keyword: str) -> bool:
        """
        Searches for a keyword in a file's content.

        :param filename: Name of the file.
        :param keyword: The keyword to search for.
        :returns: True if keyword is found, False otherwise.
        """
        if filename in self.state.files:
            return keyword in self.state.files[filename]
        return False
