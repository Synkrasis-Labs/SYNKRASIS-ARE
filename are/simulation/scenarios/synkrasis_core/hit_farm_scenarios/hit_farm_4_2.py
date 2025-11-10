from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, GroundRover, CentralHub, SensorNetwork, Plant
)
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    Scenario 4-2: Confirm whether the corn in field A1 is in the new budding growth stage.
    If so, apply starter fertilizer 20kg.
    """

    prompt: str | None = (
        "Confirm whether the corn in field A1 is in the new budding growth stage. "
        "If so, apply starter fertilizer 20kg."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        sensors = SensorNetwork(farm_state=state)

        state.register_sensor_network(sensors)

        # Setup A1 with corn in new budding (early vegetative) stage
        a1_land = state.lands.get('A1')
        if a1_land:
            a1_land.set_default_species('corn')
            for x in range(min(10, a1_land.width)):
                for y in range(min(10, a1_land.height)):
                    cell = a1_land.grid[x][y]
                    plant = Plant(species='corn', growth_stage='seeding', planting_date=state.time)
                    plant.height_cm = 20.0
                    plant.health = 0.90
                    cell.plant = plant

        self.apps = [agui, state, sensors]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        sensors = self.get_typed_app(SensorNetwork)

        with EventRegisterer.capture_mode():
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # Get A1 coordinates
            info = state.get_coordinates(land_name="A1").oracle().depends_on(e0, delay_seconds=1)
            (x, y) = state.lands["A1"].origin

            # Check plant growth stage
            o_check = sensors.get_plant_status(x=x, y=y).oracle().depends_on(info, delay_seconds=1)

        self.events = [e0, info, o_check]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
