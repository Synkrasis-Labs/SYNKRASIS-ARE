from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, Drone, CentralHub
)
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    scenarios38: Drone A3 patrols the area. If the identified size of bird flock B3 reaches the threshold,
    initiate sound dispersal and re-verify after 10-15 minutes.
    """

    prompt: str | None = (
        "Use a drone to patrol the land A3. If the identified size of bird flock B3 reaches the threshold, "
        "initiate sound dispersal and re-verify after 12 minutes."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        drone = Drone(farm_state=state)
        drone.state.device_id = "Drone"
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

            # Get coordinates for B3
            info = state.get_coordinates(land_name="B3").oracle().depends_on(e0, delay_seconds=1)
            (x, y) = state.lands["B3"].origin

            # Drone takeoff
            o_takeoff = drone.takeoff().oracle().depends_on(e0, delay_seconds=1)

            # Fly to B3
            o_fly = drone.fly_to(x=x, y=y).oracle().depends_on([info, o_takeoff], delay_seconds=1)

            # Detect bird flock and assess size
            o_detect = drone.detect_bird_flock(land_name="B3").oracle().depends_on(o_fly, delay_seconds=1)

            # Fly to flock location
            flock_x = x + 5
            flock_y = y + 5
            # Activate sound dispersal (threshold exceeded)
            o_sound = drone.sound_dispersal(area="B3").oracle().depends_on(o_detect, delay_seconds=2)

            # Schedule re-verification after 12 minutes
            o_schedule = state.schedule_in(time="12 minutes").oracle().depends_on(o_sound, delay_seconds=720)

            o_fly_2 = drone.fly_to(x=flock_x, y=flock_y).oracle().depends_on(o_schedule, delay_seconds=1)

            # Re-detect to verify dispersal success
            o_reverify = drone.detect_bird_flock(land_name="B3").oracle().depends_on(o_fly_2, delay_seconds=1)

        self.events = [e0, info, o_takeoff, o_fly, o_detect, o_sound,
                       o_schedule, o_fly_2, o_reverify]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
