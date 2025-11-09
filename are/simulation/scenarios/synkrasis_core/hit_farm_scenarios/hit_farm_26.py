from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, Drone, CentralHub, Plant
)
from are.simulation.types import EventRegisterer
from are.simulation.scenarios.core_scenario import COREScenario


class CustomScenario(COREScenario):
    """
    scenarios26: Disease detection using multispectral/NIR imaging in D1
    - Use multispectral/NIR and close-up leaf imaging
    - Detect early hotspots of rust and powdery mildew
    """

    prompt: str | None = (
        "Use drone leaf imaging in plot D1 to detect  "
        "hot spots of rust and powdery mildew."
        "After completing patrol, return to central hub."
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

            # Get coordinates for D1
            info = state.get_coordinates(land_name="D1").oracle().depends_on(e0, delay_seconds=1)
            (x, y) = state.lands["D1"].origin

            # Drone takeoff
            o_takeoff = drone.takeoff().oracle().depends_on(e0, delay_seconds=1)

            # Fly to D1
            o_fly = drone.fly_to(x=x, y=y).oracle().depends_on([info, o_takeoff], delay_seconds=2)

            o_detect_closeup = drone.detect_disease_hotspots(
                land_name="D1",
                sampling_density='high'
            ).oracle().depends_on(o_fly, delay_seconds=1)

            # Return to base and land
            o_return = drone.drone_return_to_base().oracle().depends_on(o_detect_closeup, delay_seconds=2)
            o_land = drone.land().oracle().depends_on(o_return, delay_seconds=1)

        self.events = [e0, info, o_takeoff, o_fly,
                       o_detect_closeup, o_return, o_land]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
