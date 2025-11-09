from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, SensorNetwork, IrrigationSystem, Plant
)
from are.simulation.types import EventRegisterer
from are.simulation.scenarios.core_scenario import COREScenario


class CustomScenario(COREScenario):
    """
    scenarios27: Verify maturity index and drain field at B1
    - Check maturity index of rice in B1
    - If maturity index ≥ 0.85, drain the field
    """

    prompt: str | None = (
        "At B1 verify a maturity index; if ≥0.85, drain the field."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        sensors = SensorNetwork(farm_state=state)
        irrigation = IrrigationSystem(farm_state=state)
        state.register_sensor_network(sensors)
        state.register_irrigation_system(irrigation)

        # Plant rice in B1 with high maturity index (≥0.85)
        land_b1 = state.lands["B1"]
        land_b1.water_depth = 5.0  # Initially flooded
        for x in range(20):
            for y in range(20):
                plant = Plant(species="rice", growth_stage="mature", planting_date=state.time)
                plant.maturity_index = 0.90  # Set maturity index ≥ 0.85
                land_b1.grid[x][y].plant = plant

        self.apps = [agui, state, sensors, irrigation]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        sensors = self.get_typed_app(SensorNetwork)
        irrigation = self.get_typed_app(IrrigationSystem)

        with EventRegisterer.capture_mode():
            # Single user message to trigger the entire workflow
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # Get coordinates for B1
            info = state.get_coordinates(land_name="B1").oracle().depends_on(e0, delay_seconds=1)
            (x, y) = state.lands["B1"].origin
            # Check maturity index
            o_check_maturity = sensors.get_plant_status(x, y).oracle().depends_on(
                info, delay_seconds=1)

            # If maturity index ≥ 0.85, drain the field
            o_drain = irrigation.drain_field(land_name="B1").oracle().depends_on(o_check_maturity, delay_seconds=1)

            # Verify drainage (check water depth)
            o_verify = sensors.get_water_depth(land_name="B1").oracle().depends_on(o_drain, delay_seconds=1)

        self.events = [e0, info, o_check_maturity, o_drain, o_verify]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
