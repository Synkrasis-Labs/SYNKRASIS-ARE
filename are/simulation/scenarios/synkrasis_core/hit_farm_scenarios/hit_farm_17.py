from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, IrrigationSystem, SensorNetwork, Plant
)
from are.simulation.types import EventRegisterer
from are.simulation.scenarios.core_scenario import COREScenario


class CustomScenario(COREScenario):
    """
    scenarios17: Rice flood establishment at 3–4-leaf in B2
    - Maintain continuous 5 cm water; 2-hour inspections.
    """

    prompt: str | None = (
        "B2:Rice flood establishment .  "
        "Check if the rice in Area B2 has grown to the 3-4 leaf stage. "
        "If so, fill water up to 5 cm and then stop fill."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        land = state.lands["B2"]
        land.plant_land(plant=Plant(species="rice", growth_stage="3-4 leaf", mature=False))
        irrigation = IrrigationSystem(farm_state=state)
        sensors = SensorNetwork(farm_state=state)

        state.register_irrigation_system(irrigation)
        state.register_sensor_network(sensors)
        self.apps = [agui, state, irrigation, sensors]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        irrigation = self.get_typed_app(IrrigationSystem)
        sensors = self.get_typed_app(SensorNetwork)

        with EventRegisterer.capture_mode():
            # Single user message to trigger the entire workflow
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)
            # Get coordinates for B2
            o1 = state.get_coordinates(land_name="B2").oracle().depends_on(e0, delay_seconds=1)
            (x, y) = state.lands["B2"].origin
            o2 = sensors.get_plant_status(x=x, y=y).oracle().depends_on(o1, delay_seconds=1)

            o3 = sensors.get_water_depth(land_name="B2").oracle().depends_on(o2, delay_seconds=1)

            # Open valve to fill to 5 cm (using land_name parameter)
            o4 = irrigation.open_valve(land_name="B2", water_depth_cm=5.0).oracle().depends_on(o3, delay_seconds=1)

            o5 = sensors.get_water_depth(land_name="B2").oracle().depends_on(o4, delay_seconds=1)

            # Close valve after reaching target
            o7 = irrigation.close_valve(land_name="B2").oracle().depends_on(o5, delay_seconds=1)

        self.events = [e0, o1, o2, o3, o4, o5, o7]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
