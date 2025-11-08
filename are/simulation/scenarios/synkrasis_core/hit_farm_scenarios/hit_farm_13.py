from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import HitFarmState, GroundRover, IrrigationSystem, SensorNetwork, \
    CentralHub
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    scenarios13: Rice mechanized transplanting in B1
    - Establish 3 cm water layer (±0.5), transplant on 20×20 cm grid,
    """
    prompt: str | None = (
        "B1 Rice Planting: Check if the plot has a water depth of 3 cm. If not, establish a water depth of 3 cm. "
        "After establishing a water depth of 3 cm, plant at 20 cm rows,5 cm depth, 20 cm spacing.2000 rice seeds are needed;"
        "Initially, all devices are in the central hub. The format of the rover id is rover-1."
        "After completing seeding, return to central hub."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        rover = GroundRover(farm_state=state, device_id='rover-1')
        hub = CentralHub()
        irrigation = IrrigationSystem(farm_state=state)

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


            # Move once to B1 center then single transplant action
            info = state.get_coordinates(land_name="B1").oracle().depends_on(e0, delay_seconds=1)
            oracle_1 = hub.refill_seeds(device_id=rover.state.device_id, seed_type="rice",
                                        count=2000).oracle().depends_on(
                e_close, delay_seconds=1)

            (x, y) = state.lands["B1"].origin
            o_move = rover.move_to(x=x, y=y).oracle().depends_on([info, oracle_1], delay_seconds=1)
            o_transplant = rover.plant_seed(seed_type="rice",row_spacing_cm=20.0, depth_cm=5.0,
                                                in_row_spacing_cm=20.0).oracle().depends_on(o_move, delay_seconds=0)
            o_return = rover.return_to_base().oracle().depends_on(o_transplant, delay_seconds=1)

            # Water maintenance continues (no additional events needed)

        self.events = [e0, o_1, e_open, o_2, e_close, info, oracle_1, o_move, o_transplant, o_return]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
