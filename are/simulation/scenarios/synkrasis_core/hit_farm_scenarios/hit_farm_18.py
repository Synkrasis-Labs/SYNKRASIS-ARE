from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import HitFarmState, IrrigationSystem, SensorNetwork
from are.simulation.types import EventRegisterer
from are.simulation.scenarios.core_scenario import COREScenario


class CustomScenario(COREScenario):
    """
    scenarios18: If B2 water level ≤3 cm, restore to 5 cm and log.
    """

    prompt: str | None = (
        "If the B2 water level is ≤3 cm, restore it to 5 cm."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        irrigation = IrrigationSystem(farm_state=state)
        sensors = SensorNetwork(farm_state=state)

        state.register_irrigation_system(irrigation)
        state.register_sensor_network(sensors)
        self.apps = [agui, irrigation, sensors]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        irrigation = self.get_typed_app(IrrigationSystem)
        sensors = self.get_typed_app(SensorNetwork)

        with EventRegisterer.capture_mode():
            # Single user message to trigger the entire workflow
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # Check initial water depth
            o1 = sensors.get_water_depth(land_name="B2").oracle().depends_on(e0, delay_seconds=1)

            # Open valve to fill to 5 cm (using land_name parameter)
            o2 = irrigation.open_valve(land_name="B2", water_depth_cm=5.0).oracle().depends_on(
                o1, delay_seconds=1)

            # Check initial water depth
            o3 = sensors.get_water_depth(land_name="B2").oracle().depends_on(o2, delay_seconds=1)

            # Close valve after reaching target
            o4 = irrigation.close_valve(land_name="B2").oracle().depends_on(o3, delay_seconds=1)

        self.events = [e0, o1, o2, o3, o4]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
