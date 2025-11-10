from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, GroundRover, CentralHub
)
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.scenarios.utils.registry import register_scenario
from are.simulation.types import EventRegisterer

class CustomScenario(COREScenario):
    """
    scenarios45: After confirming that A4 has no crops in the field, remove all plant stubble.
    """

    prompt: str | None = (
        "After confirming that A4 has no crops in the field, remove all plant stubble."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        rover = GroundRover(farm_state=state, device_id='rover-1')
        hub = CentralHub(farm_state=state)

        state.register_rover(rover)
        state.register_central_hub(hub)

        # Setup A4 as empty field (no living crops, just stubble)
        a4_land = state.lands.get('A4')
        if a4_land:
            # Clear all plants - field is empty
            for x in range(a4_land.width):
                for y in range(a4_land.height):
                    cell = a4_land.grid[x][y]
                    cell.plant = None

        self.apps = [agui, state, rover, hub]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        rover = self.get_typed_app(GroundRover)

        with EventRegisterer.capture_mode():
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # Get A4 coordinates
            info = state.get_coordinates(land_name="A4").oracle().depends_on(e0, delay_seconds=1)
            (x, y) = state.lands["A4"].origin

            # Move to A4
            o_move = rover.move_to(x=x, y=y).oracle().depends_on(info, delay_seconds=1)

            # Check if field is empty (no living crops)
            o_check = rover.check_field_empty(land_name="A4").oracle().depends_on(o_move, delay_seconds=1)

            # Remove stubble (field confirmed empty)
            o_remove = rover.remove_stubble(land_name="A4").oracle().depends_on(o_check, delay_seconds=2)

            # Return to base
            o_return = rover.return_to_base().oracle().depends_on(o_remove, delay_seconds=1)

        self.events = [e0, info, o_move, o_check, o_remove, o_return]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate
    run_and_validate(CustomScenario())

