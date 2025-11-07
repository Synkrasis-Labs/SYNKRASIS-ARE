from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import HitFarmState, GroundRover, IrrigationSystem, SensorNetwork, \
    CentralHub
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    scenarios13: Rice mechanized transplanting in B1
    - Establish 3 cm water layer (±0.5), transplant on 20×20 cm grid, 2–3 seedlings/hill.
    """

    prompt: str | None = (
        "B1 Rice Planting: Check if the plot has a water depth of 3 cm. If not, establish a water depth of 3 cm. After establishing a water depth of 3 cm, set up a 20x20 cm grid and plant 2-3 seedlings per hole."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        rover = GroundRover(env=None, device_id='rover-1')
        hub = CentralHub()
        irrigation = IrrigationSystem()

        sensors = SensorNetwork(farm_state=state)
        state.register_rover(rover)
        state.register_central_hub(hub)
        state.register_irrigation_system(irrigation)
        state.register_sensor_network(sensors)
        self.apps = [agui, state] + state.rovers + state.central_hubs + state.irrigation_systems + state.sensor_networks

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        rover = self.get_typed_app(GroundRover)
        irrigation = self.get_typed_app(IrrigationSystem)
        sensors = self.get_typed_app(SensorNetwork)
        hub = self.get_typed_app(CentralHub)

        with EventRegisterer.capture_mode():
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # Navigate to B1 and establish water depth ~3 cm
            o_1 = sensors.get_water_depth(land_name="B1").oracle().depends_on(e0, delay_seconds=1)
            e_open = irrigation.open_valve(land_name="B1").oracle().depends_on(o_1, delay_seconds=1)

            o_2 = sensors.get_water_depth(land_name="B1").oracle().depends_on(e_open, delay_seconds=1)
            e_close = irrigation.close_valve(land_name="B1").oracle().depends_on(o_2, delay_seconds=1)

            captured = [e0, o_1, e_open, o_2, e_close]

            # Move once to B1 center then single transplant action
            info = state.get_coordinates(land_name="B1").oracle().depends_on(e0, delay_seconds=1)
            oracle_1 = hub.refill_seeds(device_id=rover.state.device_id, seed_type="wheat",
                                        count=2000).oracle().depends_on(
                e_close, delay_seconds=1)
            oracle_2 = rover.load_seeds(seed_type="wheat", count=2000).oracle().depends_on(oracle_1, delay_seconds=1)
            o_config = rover.set_planter_config(row_spacing_cm=20.0, depth_cm=3.0,
                                                in_row_spacing_cm=20.0).oracle().depends_on(e0, delay_seconds=1)

            (x, y) = state.lands["B1"].origin
            o_move = rover.move_to(x=x, y=y).oracle().depends_on([info, e_close, oracle_2], delay_seconds=1)
            o_transplant = rover.plant_seed(seed_type="rice").oracle().depends_on([o_move, o_config], delay_seconds=0)

            captured.extend([info, o_move, o_transplant, oracle_1, oracle_2, o_config])
            # Water maintenance continues (no additional events needed)

        self.events = captured


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
