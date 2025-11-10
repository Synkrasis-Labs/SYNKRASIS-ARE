from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, GroundRover, SensorNetwork, Plant
)
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    Scenario 7: Start harvesting when the moisture content of D3 grains is ≤14%;
    """

    prompt: str | None = (
        "in land D3 ,Start harvesting when the moisture content of grains is ≤14%; "
        "then back to central hub."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        rover = GroundRover(farm_state=state, device_id='rover-1')
        sensors = SensorNetwork(farm_state=state)

        state.register_rover(rover)
        state.register_sensor_network(sensors)

        # Setup D3 with mature wheat ready for harvest
        d3_land = state.lands.get('D3')
        if d3_land:
            d3_land.set_default_species('wheat')
            for x in range(d3_land.width):
                for y in range(d3_land.height):
                    cell = d3_land.grid[x][y]
                    plant = Plant(species='wheat', growth_stage='mature', planting_date=state.time)
                    plant.maturity_index = 0.95
                    plant.mature = True
                    plant.height_cm = 85.0
                    plant.health = 0.95
                    plant.moisture_content = 0.1
                    cell.plant = plant

        self.apps = [agui, state, rover,  sensors]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        rover = self.get_typed_app(GroundRover)
        sensors = self.get_typed_app(SensorNetwork)

        with EventRegisterer.capture_mode():
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # Get D3 coordinates
            info = state.get_coordinates(land_name="D3").oracle().depends_on(e0, delay_seconds=1)
            (x, y) = state.lands["D3"].origin

            # Check grain moisture content
            o_moisture = sensors.get_plant_status(x=x,y=y).oracle().depends_on(info, delay_seconds=1)

            # Moisture ≤14%, start harvesting
            # Move to D3
            o_move = rover.move_to(x=x, y=y).oracle().depends_on(o_moisture, delay_seconds=1)

            # Start harvest
            o_harvest_start = rover.harvest(crop_species='wheat').oracle().depends_on(o_move, delay_seconds=1)

            return_base = rover.return_to_base().oracle().depends_on(o_harvest_start, delay_seconds=1)

        self.events = [e0, info, o_moisture, o_move, o_harvest_start, return_base]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
