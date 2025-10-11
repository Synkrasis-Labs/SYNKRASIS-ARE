from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.robot_arm import RobotArmApp
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class RoboticArmScenario8(COREScenario):
    """Pick gear_A, place; then pick box_small, place; finish at home (two endings)."""

    prompt: str | None = (
        "Pick 'gear_A' and then pick 'box_small'. Deliver both to the assembly table and then return home."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        self.apps = [AgentUserInterface(), RobotArmApp()]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        arm = self.get_typed_app(RobotArmApp)

        with EventRegisterer.capture_mode():
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(
                None, delay_seconds=1
            )

            o1 = arm.unlock_safety_mode().oracle().depends_on(e0, delay_seconds=1)

            # gear_A
            o2 = (
                arm.move_to(x=0.60, y=0.10, z=0.11, yaw=0.0)
                .oracle()
                .depends_on(o1, delay_seconds=1)
            )
            o3 = arm.open_gripper().oracle().depends_on(o2, delay_seconds=1)
            o4 = arm.pick(object_name="gear_A").oracle().depends_on(o3, delay_seconds=1)
            o5 = (
                arm.move_to(x=0.95, y=0.20, z=0.10, yaw=0.0)
                .oracle()
                .depends_on(o4, delay_seconds=1)
            )
            o6 = arm.place().oracle().depends_on(o5, delay_seconds=1)

            # box_small
            o7 = (
                arm.move_to(x=0.30, y=0.35, z=0.12, yaw=0.0)
                .oracle()
                .depends_on(o6, delay_seconds=1)
            )
            o8 = arm.open_gripper().oracle().depends_on(o7, delay_seconds=1)
            o9 = (
                arm.pick(object_name="box_small")
                .oracle()
                .depends_on(o8, delay_seconds=1)
            )
            o10 = (
                arm.move_to(x=0.95, y=0.20, z=0.10, yaw=0.0)
                .oracle()
                .depends_on(o9, delay_seconds=1)
            )
            o11 = arm.place().oracle().depends_on(o10, delay_seconds=1)

            # Branch A: explicit home
            o12a = (
                arm.move_to(x=0.50, y=0.00, z=0.40, yaw=0.00)
                .oracle()
                .depends_on(o11, delay_seconds=1)
            )
            # Branch B: move_home()
            o12b = arm.move_home().oracle().depends_on(o11, delay_seconds=1)

        self.events = [e0, o1, o2, o3, o4, o5, o6, o7, o8, o9, o10, o11, o12a, o12b]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(RoboticArmScenario8())
