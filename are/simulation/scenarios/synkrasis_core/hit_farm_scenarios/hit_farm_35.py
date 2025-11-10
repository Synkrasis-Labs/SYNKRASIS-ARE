from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    GroundRover, CentralHub, HitFarmState
)
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.scenarios.utils.registry import register_scenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    scenarios35: During apply_fertilizer in plot A4, GroundRover reports a "engine failure"
    The unit performs an emergency stop, is marked unavailable, and awaits service.
    """

    prompt: str | None = (
        "apply fertilizer 50.0 kg in land A4. "

    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        rover = GroundRover(device_id="GroundRover", farm_state=state)
        rover.state.fault_message = "engine failure"
        hub = CentralHub(farm_state=state)

        state.register_rover(rover)
        state.register_central_hub(hub)

        self.apps = [agui, state, rover, hub]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        rover = self.get_typed_app(GroundRover)
        hub = self.get_typed_app(CentralHub)

        with EventRegisterer.capture_mode():
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # Get A4 coordinates
            (x, y) = state.lands["A4"].origin
            o_1 = hub.refill_fertilizer(device_id="GroundRover", amount_kg=50.0).oracle().depends_on(e0,
                                                                                                     delay_seconds=1)
            info = state.get_coordinates(land_name="A4").oracle().depends_on(e0, delay_seconds=1)
            # Move to A4
            e1 = rover.move_to(x=x, y=y).oracle().depends_on([info, o_1], delay_seconds=1)
            e2 = rover.apply_fertilizer(kg=50.0).oracle().depends_on(e1, delay_seconds=2)

            e2 = rover.report_emergency_stop().oracle().depends_on(e1, delay_seconds=2)

        self.events = [e0, o_1, info, e1, e2]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
