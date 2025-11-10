from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, Drone, CentralHub
)
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    scenarios37: Drone A3 patrols the plot. If a herd of deer is found during the patrol, run a drive away.
    """

    prompt: str | None = (
        "Use a drone to patrol land A3. If a herd of deer is found during the patrol, run a drive away."
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

        with EventRegisterer.capture_mode():
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # Get coordinates for A3
            info = state.get_coordinates(land_name="A3").oracle().depends_on(e0, delay_seconds=1)
            (x, y) = state.lands["A3"].origin

            # Drone takeoff
            o_takeoff = drone.takeoff().oracle().depends_on(info, delay_seconds=1)

            # Fly to A3 patrol area
            o_fly = drone.fly_to(x=x, y=y).oracle().depends_on(o_takeoff, delay_seconds=1)

            # Detect wildlife during patrol
            o_detect = drone.detect_wildlife(land_name="A3").oracle().depends_on(o_fly, delay_seconds=1)

            deer_x = x + 10
            deer_y = y + 10

            # Drive away wildlife
            o_drive_away = drone.drive_away_wildlife(x=deer_x, y=deer_y).oracle().depends_on(o_detect, delay_seconds=1)

        self.events = [e0, info, o_takeoff, o_fly, o_detect, o_drive_away]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
