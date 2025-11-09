from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, Drone, CentralHub
)
from are.simulation.types import EventRegisterer
from are.simulation.scenarios.core_scenario import COREScenario


class CustomScenario(COREScenario):
    """
    scenarios23: Species-specific weed detection in C4
    - In plot C4, use Drone sampling to estimate weed density.
    - Even if overall weed density is < 2.5 plants/m², confirm high-risk twining weeds
      (e.g., morning glory) via species ID.
    - If detected, remove weeds using pesticide application.
    """

    prompt: str | None = (
        "In plot C4, Use Drone sampling to estimate weed density; "
        "even if overall weed density is < 2.5 plants/m², confirm high-risk twining weeds needed 500ml pesticide"
        "(e.g., morning glory) via species ID; if detected, remove weeds."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        drone = Drone(farm_state=state)
        hub = CentralHub(farm_state=state)
        state.register_drone(drone)
        state.register_central_hub(hub)

        self.apps = [agui, state, drone, hub]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        drone = self.get_typed_app(Drone)
        hub = self.get_typed_app(CentralHub)

        with EventRegisterer.capture_mode():
            # Single user message to trigger the entire workflow
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # Get coordinates for C4
            info = state.get_coordinates(land_name="C4").oracle().depends_on(e0, delay_seconds=1)
            (x, y) = state.lands["C4"].origin

            # Drone takeoff
            o_takeoff = drone.takeoff().oracle().depends_on(e0, delay_seconds=1)

            # Fly to C4
            o_fly = drone.fly_to(x=x, y=y).oracle().depends_on([info, o_takeoff], delay_seconds=2)

            # First, estimate overall weed density
            o_weed_density = drone.estimate_weed_density(land_name="C4").oracle().depends_on(o_fly, delay_seconds=1)

            # Then, identify specific weed species to check for high-risk twining weeds
            o_species_id = drone.identify_weed_species(land_name="C4").oracle().depends_on(
                o_weed_density, delay_seconds=1)

            # If high-risk twining weeds detected, refill pesticide and apply
            # (regardless of overall density)
            o_return_for_refill = drone.drone_return_to_base().oracle().depends_on(o_species_id, delay_seconds=1)

            o_refill = hub.refill_pesticide(device_id=drone.state.device_id, amount_ml=1000.0).oracle().depends_on(
                o_return_for_refill, delay_seconds=1)

            # Fly back to C4
            o_fly_back = drone.fly_to(x=x, y=y).oracle().depends_on(o_refill, delay_seconds=2)

            # Apply pesticide to remove high-risk weeds
            o_apply_pesticide = drone.apply_pesticide(area="C4", amount_ml=800.0).oracle().depends_on(
                o_fly_back, delay_seconds=1)

            # Return to base and land
            o_return_final = drone.drone_return_to_base().oracle().depends_on(o_apply_pesticide, delay_seconds=2)
            o_land = drone.land().oracle().depends_on(o_return_final, delay_seconds=1)

        self.events = [e0, info, o_takeoff, o_fly, o_weed_density, o_species_id,
                      o_return_for_refill, o_refill, o_fly_back, o_apply_pesticide,
                      o_return_final, o_land]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate
    run_and_validate(CustomScenario())

