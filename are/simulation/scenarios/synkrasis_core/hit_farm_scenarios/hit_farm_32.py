from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    GroundRover, CentralHub, SensorNetwork, HitFarmState, Plant
)
from are.simulation.types import EventRegisterer
from are.simulation.scenarios.core_scenario import COREScenario


class CustomScenario(COREScenario):
    """
    scenarios32: Check if soybean maturity index of C4 land is ≥ 0.95; if so, then harvest.
    """

    prompt: str | None = (
        "Check if the soybean maturity index of C4 land is greater than or equal to 0.95. "
        "If the maturity index meets this threshold, then harvest the soybeans."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        rover = GroundRover(farm_state=state, device_id='rover-01')
        hub = CentralHub(farm_state=state)
        sensor = SensorNetwork(farm_state=state)

        state.register_rover(rover)
        state.register_central_hub(hub)

        # Setup C4 with mature soybean plants (maturity index ≥ 0.95)
        c4_land = state.lands.get('C4')
        if c4_land:
            for x in range(c4_land.width):
                for y in range(c4_land.height):
                    cell = c4_land.grid[x][y]
                    plant = Plant(species='soybean', growth_stage='R8')
                    plant.maturity_index = 0.96
                    plant.mature = True
                    plant.height_cm = 80.0
                    plant.health = 0.95
                    cell.plant = plant

        self.apps = [agui, state, rover, hub, sensor]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        rover = self.get_typed_app(GroundRover)
        sensor = self.get_typed_app(SensorNetwork)

        with EventRegisterer.capture_mode():
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)
            # Get coordinates for A1
            info = state.get_coordinates(land_name="A1").oracle().depends_on(e0, delay_seconds=1)
            # Get C4 coordinates
            (x, y) = state.lands["C4"].origin
            # Check maturity index in C4
            e1 = sensor.get_plant_status(x, y).oracle().depends_on(info, delay_seconds=1)

            # Move to C4 and harvest
            e2 = rover.move_to(x=x, y=y).oracle().depends_on(e1, delay_seconds=1)
            e3 = rover.harvest(crop_species='soybean').oracle().depends_on(e2, delay_seconds=1)

            # Return to base
            e4 = rover.return_to_base().oracle().depends_on(e3, delay_seconds=1)

        self.events = [e0, info, e1, e2, e3, e4]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
