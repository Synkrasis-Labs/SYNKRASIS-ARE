import copy
from typing import Any, Generic

from typing_extensions import TypeVar

from are.simulation.apps.app import App
from are.simulation.utils.data_utils import get_state_dict

AppState = TypeVar("AppState")


class COREApp(App, Generic[AppState]):
    # App-specific configuration
    name: str | None
    init_state: AppState
    state: AppState

    def __init__(self):
        self.state = copy.copy(self.init_state)
        super().__init__()

    def get_state(self) -> dict[str, Any]:
        """
        Return the app's current state for persistence.
        Use get_state_dict utility for consistent serialization.
        """
        print(f"Getting state for {self.name}", flush=True)
        return get_state_dict(self, ["state"])

    def load_state(self, state_dict: dict[str, Any]):
        """
        Restore app state from saved data.
        Handle data conversion and validation carefully.
        """
        # @TODO: when is this called?
        pass

    def reset(self):
        """Reset app to initial state - important for scenario repeatability"""
        self.state = copy.copy(self.init_state)
        super().reset()
