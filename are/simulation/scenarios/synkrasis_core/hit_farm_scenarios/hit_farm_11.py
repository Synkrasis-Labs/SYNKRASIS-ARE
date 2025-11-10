from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import GroundRover, CentralHub, HitFarmState

from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    scenarios11: Precision drill seeding for winter wheat (D1, D2)
    - Row spacing 20 cm, depth 3.8 cm, in-row spacing 8 cm.
    """
    prompt: str | None = (
        "Precision drill wheat on D1 and D2 at 20 cm rows, 3.8 cm depth, 8 cm spacing."
        "After completing seeding, return to central hub."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        rover = GroundRover(farm_state=state, device_id='rover-1')
        hub = CentralHub()

        state.register_rover(rover)
        state.register_central_hub(hub)
        self.apps = [agui, state, rover, hub]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        rover = self.get_typed_app(GroundRover)
        hub = self.get_typed_app(CentralHub)

        with EventRegisterer.capture_mode():
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # Load wheat seeds at base and set planter config
            oracle_1 = hub.refill_seeds(device_id=rover.state.device_id, seed_type="wheat",
                                        count=2000).oracle().depends_on(
                e0, delay_seconds=1)

            o_coordinate_1 = state.get_coordinates(land_name="D1").oracle().depends_on(e0, delay_seconds=0)
            (x, y) = state.lands["D1"].origin
            o_move_1 = rover.move_to(x=x, y=y).oracle().depends_on([o_coordinate_1, oracle_1], delay_seconds=1)
            o_plant_1 = rover.plant_seed(seed_type="wheat", row_spacing_cm=20.0, depth_cm=3.8,
                                         in_row_spacing_cm=8.0).oracle().depends_on(o_move_1, delay_seconds=0)

            o_coordinate_2 = state.get_coordinates(land_name="D2").oracle().depends_on(e0, delay_seconds=0)
            (x, y) = state.lands["D2"].origin
            o_move_2 = rover.move_to(x=x, y=y).oracle().depends_on([o_coordinate_2, oracle_1], delay_seconds=1)
            o_plant_2 = rover.plant_seed(seed_type="wheat", row_spacing_cm=20.0, depth_cm=3.8,
                                         in_row_spacing_cm=8.0).oracle().depends_on(o_move_2, delay_seconds=0)

            # Return to base
            o_return = rover.return_to_base().oracle().depends_on([o_plant_1, o_plant_2], delay_seconds=1)

        self.events = [e0, oracle_1, o_coordinate_1, o_move_1, o_plant_1, o_coordinate_2, o_move_2, o_plant_2, o_return]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
