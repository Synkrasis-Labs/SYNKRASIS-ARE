from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, Drone, GroundRover, CentralHub, Plant
)
from are.simulation.types import EventRegisterer
from are.simulation.scenarios.core_scenario import COREScenario


class CustomScenario(COREScenario):
    """
    scenarios24: Corn density estimation and thinning in A1
    - In plot A1, use Drone sampling to estimate corn density.
    - Compute the target stand from planned row/in-row spacing (75 cm rows, 25 cm spacing).
    - Compare measured density to target; if >120% of target, thin plants to restore target stand.
    """

    prompt: str | None = (
        "In plot A1, use Drone sampling to estimate corn density; "
        "the target density is 5 plants per m² "
        "compare to measured density; if >120% of target, restore the stand to target."
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

        land_a1 = state.lands["A1"]
        land_a1.density_per_m2 = 8.0

        self.apps = [agui, state, drone, rover, hub]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        drone = self.get_typed_app(Drone)
        rover = self.get_typed_app(GroundRover)
        self.get_typed_app(CentralHub)

        with EventRegisterer.capture_mode():
            # Single user message to trigger the entire workflow
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # Get coordinates for A1
            info = state.get_coordinates(land_name="A1").oracle().depends_on(e0, delay_seconds=1)
            (x, y) = state.lands["A1"].origin

            # Drone takeoff and fly to A1
            o_takeoff = drone.takeoff().oracle().depends_on(e0, delay_seconds=1)
            o_fly = drone.fly_to(x=x, y=y).oracle().depends_on([info, o_takeoff], delay_seconds=2)

            # Estimate corn plant density using aerial imaging
            o_plant_density = drone.estimate_plant_density(land_name="A1", crop_species="corn").oracle().depends_on(
                o_fly, delay_seconds=1)

            # Drone returns and lands (survey complete)
            o_return_drone = drone.drone_return_to_base().oracle().depends_on(o_plant_density, delay_seconds=2)
            o_land = drone.land().oracle().depends_on(o_return_drone, delay_seconds=1)

            # Move rover to A1
            o_move = rover.move_to(x=x, y=y).oracle().depends_on([info, o_plant_density], delay_seconds=1)

            o_thin = rover.thin_plants(land_name="A1", target_density=5.0).oracle().depends_on(o_move, delay_seconds=1)

            o_return_rover = rover.return_to_base().oracle().depends_on(o_thin, delay_seconds=1)

        self.events = [e0, info, o_takeoff, o_fly, o_plant_density, o_return_drone, o_land,
                       o_move, o_thin, o_return_rover]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
