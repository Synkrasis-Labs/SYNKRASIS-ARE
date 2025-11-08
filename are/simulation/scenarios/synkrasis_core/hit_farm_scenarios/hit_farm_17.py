from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, Drone, GroundRover, CentralHub, IrrigationSystem, SensorNetwork
)
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.scenarios.utils.registry import register_scenario
from are.simulation.types import EventRegisterer

class CustomScenario(COREScenario):
    """
    scenarios17: Rice flood establishment at 3–4-leaf in B2
    - Maintain continuous 5 cm water; 2-hour inspections.
    """

    prompt: str | None = (
        "B2: if phenology=3–4 leaves, fill to 5 cm (±0.5) and maintain; inspect every 2 h; log start and device status."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        drone = Drone(farm_state=state)
        rover = GroundRover(farm_state=state, device_id='rover-1')
        hub = CentralHub(farm_state=state)
        irrigation = IrrigationSystem(farm_state=state)
        sensors = SensorNetwork(farm_state=state)
        state.register_drone(drone)
        state.register_rover(rover)
        state.register_central_hub(hub)
        state.register_irrigation_system(irrigation)
        state.register_sensor_network(sensors)
        self.apps = [agui, state] + state.drones + state.rovers + state.central_hubs + state.irrigation_systems + state.sensor_networks

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        irrigation = self.get_typed_app(IrrigationSystem)
        sensors = self.get_typed_app(SensorNetwork)

        with EventRegisterer.capture_mode():
            # Single user message to trigger the entire workflow
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # Get coordinates for B2
            info = state.get_coordinates(land_name="B2").oracle().depends_on(e0, delay_seconds=1)

            # Check initial water depth
            o_depth_initial = sensors.get_water_depth(land_name="B2").oracle().depends_on(info, delay_seconds=1)

            # Open valve to fill to 5 cm (using land_name parameter)
            e_open = irrigation.open_valve(land_name="B2", duration_minutes=45).oracle().depends_on(o_depth_initial, delay_seconds=1)

            # Update sensor cache to record target water depth
            e_set = sensors.update_cache(sensor_id="B2_water", data_dict={"water_depth_cm": 5.0}).oracle().depends_on(e_open, delay_seconds=1)

            # Check water depth after opening valve
            o_depth_check1 = sensors.get_water_depth(land_name="B2").oracle().depends_on(e_set, delay_seconds=1)

            # Close valve after reaching target
            e_close = irrigation.close_valve(land_name="B2").oracle().depends_on(o_depth_check1, delay_seconds=1)

            # Two-hour inspection checks
            # First check at 2 hours
            o_depth_2h = sensors.get_water_depth(land_name="B2").oracle().depends_on(e_close, delay_seconds=1)

            # Second check at 4 hours
            o_depth_4h = sensors.get_water_depth(land_name="B2").oracle().depends_on(o_depth_2h, delay_seconds=1)

            self.events = [e0, info, o_depth_initial, e_open, e_set, o_depth_check1, e_close, o_depth_2h, o_depth_4h]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate
    run_and_validate(CustomScenario())


