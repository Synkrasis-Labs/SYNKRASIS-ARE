from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, Drone, CentralHub
)
from are.simulation.types import EventRegisterer
from are.simulation.scenarios.core_scenario import COREScenario


class CustomScenario(COREScenario):
    """
    scenarios22: Weed density monitoring in C2
    - Use Drone sampling in plot C2 to estimate weed density.
    - When density exceeds 2.5 plants/m², remove weeds using pesticide application.
    """

    prompt: str | None = (
        "Use Drone sampling in plot C2 to estimate weed density; "
        "when density exceeds 2.5 plants/m², remove weeds."
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

            # Get coordinates for C2
            info = state.get_coordinates(land_name="C2").oracle().depends_on(e0, delay_seconds=1)
            (x, y) = state.lands["C2"].origin

            # Drone takeoff
            o_takeoff = drone.takeoff().oracle().depends_on(e0, delay_seconds=1)

            # Fly to C2
            o_fly = drone.fly_to(x=x, y=y).oracle().depends_on([info, o_takeoff], delay_seconds=2)

            # Estimate weed density using aerial imaging
            o_weed_density = drone.estimate_weed_density(land_name="C2").oracle().depends_on(o_fly, delay_seconds=1)

            # If weed density > 2.5 plants/m², refill pesticide and apply
            o_return_for_refill = drone.drone_return_to_base().oracle().depends_on(o_weed_density, delay_seconds=1)

            o_refill = hub.refill_pesticide(device_id=drone.state.device_id, amount_ml=1000.0).oracle().depends_on(
                o_return_for_refill, delay_seconds=1)
            # Fly back to C2
            o_fly_back = drone.fly_to(x=x, y=y).oracle().depends_on(o_refill, delay_seconds=2)

            # Apply pesticide to remove weeds
            o_apply_pesticide = drone.apply_pesticide(area="C2", amount_ml=800.0).oracle().depends_on(
                o_fly_back, delay_seconds=1)

            # Return to base and land
            o_return_final = drone.drone_return_to_base().oracle().depends_on(o_apply_pesticide, delay_seconds=2)
            o_land = drone.land().oracle().depends_on(o_return_final, delay_seconds=1)

        self.events = [e0, info, o_takeoff, o_fly, o_weed_density, o_return_for_refill,
                       o_refill, o_fly_back, o_apply_pesticide, o_return_final, o_land]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
