from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, GroundRover, CentralHub, SensorNetwork, Plant
)
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.scenarios.utils.registry import register_scenario
from are.simulation.types import EventRegisterer

class CustomScenario(COREScenario):
    """
    scenarios42: Wheat harvesting and straw processing are completed on D4,
    and then soybeans are directly sown in the same plot.
    """

    prompt: str | None = (
        "Wheat harvesting and straw processing are completed on C4, "
        "and then soybeans are directly sown in the same land  set 38 cm rows, 5 cm depth, 10 cm spacing."
        "return to the base after all is completed."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        rover = GroundRover(farm_state=state, device_id='rover-1')
        hub = CentralHub(farm_state=state)
        sensors = SensorNetwork(farm_state=state)

        state.register_rover(rover)
        state.register_central_hub(hub)
        state.register_sensor_network(sensors)

        # Setup D4 with mature wheat
        d4_land = state.lands.get('C4')
        if d4_land:
            d4_land.set_default_species('wheat')
            for x in range(d4_land.width):
                for y in range(d4_land.height):
                    cell = d4_land.grid[x][y]
                    plant = Plant(species='wheat', growth_stage='mature', planting_date=state.time)
                    plant.maturity_index = 0.95
                    plant.mature = True
                    plant.height_cm = 90.0
                    plant.health = 0.95
                    cell.plant = plant

        self.apps = [agui, state, rover, hub, sensors]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        rover = self.get_typed_app(GroundRover)
        hub = self.get_typed_app(CentralHub)
        sensors = self.get_typed_app(SensorNetwork)

        with EventRegisterer.capture_mode():
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # Get coordinates for D4
            info = state.get_coordinates(land_name="C4").oracle().depends_on(e0, delay_seconds=1)
            (x, y) = state.lands["C4"].origin

            # Move to C4
            o_move_harvest = rover.move_to(x=x, y=y).oracle().depends_on(info, delay_seconds=1)

            # Check wheat maturity
            o_check = sensors.get_plant_status(x=x, y=y).oracle().depends_on(info, delay_seconds=1)

            # Harvest wheat (straw processing included)
            o_harvest = rover.harvest(crop_species='wheat').oracle().depends_on([o_check,o_move_harvest], delay_seconds=2)

            # Return to base to unload
            o_return = rover.return_to_base().oracle().depends_on(o_harvest, delay_seconds=1)

            # Load soybean seeds
            o_load_seeds = hub.refill_seeds(device_id=rover.state.device_id, seed_type="soybean", count=1500).oracle().depends_on(
                o_return, delay_seconds=1)

            # Return to D4 for sowing
            o_move_plant = rover.move_to(x=x, y=y).oracle().depends_on(o_load_seeds, delay_seconds=1)

            # Direct-sow soybeans
            o_plant = rover.plant_seed(seed_type="soybean", row_spacing_cm=38.0, depth_cm=5.0, in_row_spacing_cm=10.0).oracle().depends_on(
                o_move_plant, delay_seconds=2)


            # Final return
            o_return_final = rover.return_to_base().oracle().depends_on(o_plant, delay_seconds=1)

        self.events = [e0, info, o_move_harvest, o_check, o_harvest, o_return, o_load_seeds, o_move_plant, o_plant, o_return_final]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate
    run_and_validate(CustomScenario())
