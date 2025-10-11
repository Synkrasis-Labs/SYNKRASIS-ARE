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

    def __post_init__(self):
        """Initialize the app - always call super().__init__()"""
        self.name = __class__.__name__
        self.state = self.init_state
        super().__init__(self.name)
        print(f"{self.name} initialized", flush=True)

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
        super().reset()
        print(f"Resetting {self.name}", flush=True)
        self.state = self.init_state
