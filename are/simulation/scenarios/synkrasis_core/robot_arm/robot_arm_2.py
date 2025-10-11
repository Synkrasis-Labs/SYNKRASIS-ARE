from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.robot_arm import RoboticArmApp
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class RoboticArmScenario2(COREScenario):
    """Pick box_large → quality_control → return home (two acceptable endings)."""

    prompt: str | None = (
        "Pick 'box_large' at its known pose, bring it to quality control station, then return home."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        self.apps = [AgentUserInterface(), RoboticArmApp()]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        arm = self.get_typed_app(RoboticArmApp)

        with EventRegisterer.capture_mode():
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(
                None, delay_seconds=1
            )

            o1 = arm.unlock_safety_mode().oracle().depends_on(e0, delay_seconds=1)
            o2 = (
                arm.move_to(x=0.28, y=-0.30, z=0.15, yaw=0.0)
                .oracle()
                .depends_on(o1, delay_seconds=1)
            )
            o3 = arm.open_gripper().oracle().depends_on(o2, delay_seconds=1)
            o4 = (
                arm.pick(object_name="box_large")
                .oracle()
                .depends_on(o3, delay_seconds=1)
            )
            o5 = (
                arm.move_to(x=1.05, y=-0.20, z=0.10, yaw=0.0)
                .oracle()
                .depends_on(o4, delay_seconds=1)
            )
            o6 = arm.place().oracle().depends_on(o5, delay_seconds=1)

            # Branch A: move_home()
            o7a = arm.move_home().oracle().depends_on(o6, delay_seconds=1)
            # Branch B: explicit home pose
            o7b = (
                arm.move_to(x=0.50, y=0.00, z=0.40, yaw=0.00)
                .oracle()
                .depends_on(o6, delay_seconds=1)
            )

        self.events = [e0, o1, o2, o3, o4, o5, o6, o7a, o7b]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(RoboticArmScenario2())
