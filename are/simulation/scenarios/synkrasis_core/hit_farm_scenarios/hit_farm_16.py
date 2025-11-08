from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, Drone, GroundRover, CentralHub, IrrigationSystem, SensorNetwork
)
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.scenarios.utils.registry import register_scenario
from are.simulation.types import EventRegisterer

class CustomScenario(COREScenario):
    """
    scenarios16: Data-driven corn irrigation (MAD trigger) in A2 at MAD=53%.
    """

    prompt: str | None = (
        "A2: MAD=53% (>50%) → irrigate to field capacity; monitor and stop at target; recheck."
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
        irrigation = self.get_typed_app(IrrigationSystem)
        sensors = self.get_typed_app(SensorNetwork)

        with EventRegisterer.capture_mode():
            # Single user message to trigger the entire workflow
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # Get initial MAD reading
            o_mda_before = sensors.get_land_MDA(land_name="A2").oracle().depends_on(e0, delay_seconds=1)

            # Open valve to irrigate (using land_name parameter)
            e_open = irrigation.open_valve(land_name="A2", duration_minutes=60).oracle().depends_on(o_mda_before, delay_seconds=1)

            # Check water depth during irrigation
            o_monitor = sensors.get_water_depth(land_name="A2").oracle().depends_on(e_open, delay_seconds=1)

            # Close valve after irrigation
            e_close = irrigation.close_valve(land_name="A2").oracle().depends_on(o_monitor, delay_seconds=1)

            # Recheck after 4 h: update cache to reflect refill
            e_recheck = sensors.update_cache(sensor_id="A2_moisture_post", data_dict={"MAD": 0.0}).oracle().depends_on(e_close, delay_seconds=1)

            # Get final MAD reading to confirm
            o_mda_after = sensors.get_land_MDA(land_name="A2").oracle().depends_on(e_recheck, delay_seconds=1)

            self.events = [e0,o_mda_before, e_open, o_monitor, e_close, e_recheck, o_mda_after]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate
    run_and_validate(CustomScenario())


