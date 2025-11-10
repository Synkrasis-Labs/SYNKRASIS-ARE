from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, GroundRover, CentralHub
)
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    scenarios41: 机器人自动回充（施肥补液） | Robot auto refill (fertilizer/UAN)
    - While applying UAN in A1, if remaining volume <5%, pause, return to base to refill
    - Resume application from interruption point
    """

    prompt: str | None = (
        "Refill the device with 50KG of fertilizer at a time, "
        "and then go to plots A1 and B1 to fertilize, using 50KG for each plot."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        rover = GroundRover(farm_state=state, device_id='GroundRover')
        rover.state.fertilizer_bin_kg = 0.0
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
            # Single user message to trigger the entire workflow
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # Get coordinates for A1
            info = state.get_coordinates(land_name="A1").oracle().depends_on(e0, delay_seconds=1)
            info2 = state.get_coordinates(land_name="B1").oracle().depends_on(e0, delay_seconds=1)

            # Initial refill of fertilizer
            o_initial_fill = hub.refill_fertilizer(device_id=rover.state.device_id, amount_kg=50.0).oracle().depends_on(
                info, delay_seconds=1)

            # Move to A1 and start fertilizer application
            (x, y) = state.lands["A1"].origin
            (xb, yb) = state.lands["B1"].origin
            o_move_start = rover.move_to(x=x, y=y).oracle().depends_on([info, o_initial_fill], delay_seconds=1)

            # Start applying fertilizer
            o_apply_a1 = rover.apply_fertilizer(kg=50.0).oracle().depends_on(o_move_start, delay_seconds=0)

            o_return_refill = rover.return_to_base().oracle().depends_on(o_move_start, delay_seconds=1)

            # Refill fertilizer at hub to target level
            o_refill = hub.refill_fertilizer(device_id=rover.state.device_id, amount_kg=50.0).oracle().depends_on(
                o_return_refill, delay_seconds=1)

            o_resume_move = rover.move_to(x=xb, y=yb).oracle().depends_on([info2, o_refill], delay_seconds=1)

            # Continue fertilizer application
            o_apply_resume = rover.apply_fertilizer(kg=50.0).oracle().depends_on(o_resume_move, delay_seconds=0)

            # Final return to base after completing application
            o_return_final = rover.return_to_base().oracle().depends_on(o_apply_resume, delay_seconds=1)

        self.events = [e0, info, o_initial_fill, o_move_start, o_apply_a1,
                       o_return_refill, o_refill, o_resume_move, o_apply_resume, o_return_final]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
