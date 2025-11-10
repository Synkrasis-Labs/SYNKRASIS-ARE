from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    Drone, CentralHub, HitFarmState
)
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    scenarios34: drone-01 receives A1 patrol command; preflight fails with "Motor #3 speed deviation."
    Abort mission, mark drone-01 unavailable, and auto-reassign the task to drone-02.
    """

    prompt: str | None = (
        "growth monitoring: drone takeoff, fly over plots A1,and inspect at sampling density medium"
        "then back to central hub."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        drone_01 = Drone(farm_state=state)
        drone_01.state.device_id = 'drone-01'
        drone_01.name = "drone-01"
        drone_01.state.fault_message = " Motor #3 speed deviation"

        drone_02 = Drone(farm_state=state)
        drone_02.state.device_id = 'drone-02'
        drone_02.name = "drone-02"

        hub = CentralHub(farm_state=state)

        state.register_drone(drone_01)
        state.register_drone(drone_02)
        state.register_central_hub(hub)

        self.apps = [agui, state, drone_01, drone_02, hub]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        drone_01 = self.get_typed_app(Drone, "drone-01")
        drone_02 = self.get_typed_app(Drone, "drone-02")

        with EventRegisterer.capture_mode():
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # Get A1 coordinates
            (x, y) = state.lands["A1"].origin
            info = state.get_coordinates(land_name='A1').oracle().depends_on(e0, delay_seconds=1)
            # drone-01: Pre-flight check with simulated Motor #3 fault
            e1 = drone_01.takeoff().oracle().depends_on(e0, delay_seconds=1)

            # drone-02: Execute patrol mission
            e4 = drone_02.takeoff().oracle().depends_on(e1, delay_seconds=1)
            e5 = drone_02.fly_to(x=x, y=y).oracle().depends_on([info, e4], delay_seconds=1)
            e6 = drone_02.inspect_plot(x=x, y=y, sampling_density='medium').oracle().depends_on(e5, delay_seconds=1)

            # Return to base
            e7 = drone_02.drone_return_to_base().oracle().depends_on(e6, delay_seconds=1)
            e8 = drone_02.land().oracle().depends_on(e7, delay_seconds=1)

        self.events = [e0, info, e1, e4, e5, e6, e7, e8]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
