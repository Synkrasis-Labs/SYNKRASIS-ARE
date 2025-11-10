from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, GroundRover, CentralHub, Plant
)
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.scenarios.utils.registry import register_scenario
from are.simulation.types import EventRegisterer


@register_scenario("hit_farm_33")
class CornHarvestWithCapacityMonitoring(COREScenario):
    """
    scenarios33: Harvest corn in land A1. If the equipment's capacity is full,
    pause harvesting and go to the central hub to unload. After unloading, continue harvesting from where you left off.
    """

    prompt: str | None = (
        "Harvest corn in land A1. If the device's capacity is full, pause harvesting and go to the central hub to unload. "
        "After unloading,  return to the coordinates where the harvest task was aborted and continue harvesting."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        rover = GroundRover(farm_state=state, device_id='rover-1')
        rover.state.hopper_capacity_kg = 1000.0
        hub = CentralHub(farm_state=state)

        state.register_rover(rover)
        state.register_central_hub(hub)

        # Setup A1 with mature corn ready for harvest
        a1_land = state.lands.get('A1')
        if a1_land:
            a1_land.set_default_species('corn')
            for x in range(a1_land.width):
                for y in range(a1_land.height):
                    cell = a1_land.grid[x][y]
                    plant = Plant(species='corn', growth_stage='mature', planting_date=state.time)
                    plant.maturity_index = 0.95
                    plant.mature = True
                    plant.height_cm = 200.0  # High yield corn
                    plant.health = 0.95
                    cell.plant = plant

        self.apps = [agui, state, rover, hub]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        rover = self.get_typed_app(GroundRover)

        with EventRegisterer.capture_mode():
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # Get coordinates for A1
            info = state.get_coordinates(land_name="A1").oracle().depends_on(e0, delay_seconds=1)
            (x, y) = state.lands["A1"].origin

            # Move to A1
            o_move = rover.move_to(x=x, y=y).oracle().depends_on(info, delay_seconds=1)

            o_harvest_1 = rover.harvest(crop_species='corn').oracle().depends_on(
                o_move, delay_seconds=2)

            # Return to base to unload (hopper full)
            o_return_1 = rover.return_to_base().oracle().depends_on(o_harvest_1, delay_seconds=1)

            # Unload hopper
            o_unload = rover.unload_hopper().oracle().depends_on(o_return_1, delay_seconds=1)

            # Return to last harvest position
            o_resume_move = rover.move_to(x=17.0, y=16.0).oracle().depends_on(o_unload, delay_seconds=1)

            # Continue harvesting remaining area
            o_harvest_2 = rover.harvest(crop_species='corn').oracle().depends_on(
                o_resume_move, delay_seconds=2)

            # Final return to base
            o_return_final = rover.return_to_base().oracle().depends_on(o_harvest_2, delay_seconds=1)

        self.events = [e0, info, o_move, o_harvest_1, o_return_1, o_unload, o_resume_move, o_harvest_2, o_return_final]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CornHarvestWithCapacityMonitoring())
