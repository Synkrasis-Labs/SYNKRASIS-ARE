from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, Drone, GroundRover, CentralHub, Plant
)
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.scenarios.utils.registry import register_scenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    scenarios48: In plot A1, use Drone sampling to estimate corn density;
    the target density is 5 plants per m²; compare to measured density;
    if <90% of target, restore the stand to target.
    """

    prompt: str | None = (
        "In plot A1, use Drone sampling to estimate corn density;  "
        "the target density is 5 plants per m² ； compare to measured density; "
        "if <90% of target, restore the stand to target."
        "return to the base after all is completed."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        drone = Drone(farm_state=state)
        rover = GroundRover(farm_state=state, device_id='rover-1')
        hub = CentralHub(farm_state=state)

        state.register_drone(drone)
        state.register_rover(rover)
        state.register_central_hub(hub)

        # Setup A1 with sparse corn (below 90% of target)
        # Target: 5 plants/m², 90% threshold: 4.5 plants/m²
        # Set current density to 4.0 plants/m² (below threshold)
        a1_land = state.lands.get('A1')
        if a1_land:
            a1_land.set_default_species('corn')
            a1_land.density_per_m2 = 4.0  # Below 90% of target (4.5)
            # Plant sparse corn
            plant_count = 0
            target_count = int(a1_land.width * a1_land.height * 0.6)  # 60% planted
            for x in range(a1_land.width):
                for y in range(a1_land.height):
                    if plant_count >= target_count:
                        break
                    if (x + y) % 2 == 0:  # Sparse planting pattern
                        cell = a1_land.grid[x][y]
                        plant = Plant(species='corn', growth_stage='V3', planting_date=state.time)
                        plant.height_cm = 30.0
                        plant.health = 0.90
                        cell.plant = plant
                        plant_count += 1

        self.apps = [agui, state, drone, rover, hub]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        drone = self.get_typed_app(Drone)
        rover = self.get_typed_app(GroundRover)
        hub = self.get_typed_app(CentralHub)

        with EventRegisterer.capture_mode():
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # Get A1 coordinates
            info = state.get_coordinates(land_name="A1").oracle().depends_on(e0, delay_seconds=1)
            (x, y) = state.lands["A1"].origin

            # Drone estimates corn density
            o_takeoff = drone.takeoff().oracle().depends_on(info, delay_seconds=1)
            o_fly = drone.fly_to(x=x, y=y).oracle().depends_on(o_takeoff, delay_seconds=1)
            o_estimate = drone.estimate_plant_density(crop_species='corn', land_name='A1',
                                                      sampling_density='medium').oracle().depends_on(
                o_fly, delay_seconds=2)

            # Return drone to base
            o_return_drone = drone.drone_return_to_base().oracle().depends_on(o_estimate, delay_seconds=1)
            o_land = drone.land().oracle().depends_on(o_return_drone, delay_seconds=1)

            # If density < 90% of target (4.5), restore to target (5.0)
            # Load corn seeds for replanting
            o_load = hub.refill_seeds(device_id=rover.state.device_id, seed_type="corn", count=300).oracle().depends_on(
                o_land, delay_seconds=1)

            # Move rover to A1
            o_move = rover.move_to(x=x, y=y).oracle().depends_on(o_load, delay_seconds=1)

            # Replant to fill gaps
            o_replant = rover.plant_seed(seed_type='corn', row_spacing_cm=75.0, depth_cm=5.0,
                                         in_row_spacing_cm=25.0).oracle().depends_on(
                o_move, delay_seconds=1)

            # Return to base
            o_return = rover.return_to_base().oracle().depends_on(o_replant, delay_seconds=1)

        self.events = [e0, info, o_takeoff, o_fly, o_estimate, o_return_drone, o_land,
                       o_load, o_move, o_move, o_replant, o_return]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
