from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import HitFarmState
from are.simulation.apps.synkrasis_core.hit_farm import Drone, GroundRover, CentralHub, IrrigationSystem, SensorNetwork, \
    HitFarmState

from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.scenarios.utils.registry import register_scenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    scenarios15: Corn seeding with starter banding in A1
    - 75 cm rows, 5 cm depth, 25 cm spacing; band 6-24-24 starter at 112 kg/ha.
    """

    prompt: str | None = (
        "Sow seeds in A1 with a row spacing of 75 cm, a sowing depth of 5 cm, and a seed spacing of 25 cm， 4000 corn seeds are needed; "
        "then apply fertilizer in strips，50kg fertilizer are needed;"
        "return to the base after all is completed."
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

            e_load_hub = hub.refill_seeds(device_id=rover.state.device_id, seed_type="corn",
                                          count=4000).oracle().depends_on(e0, delay_seconds=1)

            o_coordinate_1 = state.get_coordinates(land_name="A1").oracle().depends_on(e0, delay_seconds=0)
            (x, y) = state.lands["A1"].origin
            o_move = rover.move_to(x=x, y=y).oracle().depends_on([o_coordinate_1], delay_seconds=1)
            o_seed = rover.plant_seed(seed_type="corn", row_spacing_cm=75.0, depth_cm=5.0,
                                      in_row_spacing_cm=25.0).oracle().depends_on(o_move, delay_seconds=0)

            o_return_1 = rover.return_to_base().oracle().depends_on(o_seed, delay_seconds=1)
            o_refill_2 = hub.refill_fertilizer(device_id=rover.state.device_id, amount_kg=50.0).oracle().depends_on(
                o_return_1, delay_seconds=1)
            o_move_2 = rover.move_to(x=x, y=y).oracle().depends_on(o_refill_2, delay_seconds=1)
            o_band = rover.apply_fertilizer(kg=50.0).oracle().depends_on(o_move_2, delay_seconds=0)

            o_return_2 = rover.return_to_base().oracle().depends_on(o_band, delay_seconds=1)
        self.events = [e0, e_load_hub, o_move, o_seed, o_return_1, o_refill_2, o_move_2, o_band, o_return_2]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
