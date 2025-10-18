from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.robot_arm import RobotArmApp
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class RoboticArmScenario4(COREScenario):
    """Pick panel_X, rotate yaw to 1.57, place at target."""

    prompt: str | None = (
        "Move to (0.90, -0.10, 0.14, yaw=0.0) and pick 'panel_X'. "
        "Rotate yaw to 1.57 rad while above (0.95, 0.20, 0.10) and place it there."
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
            o2 = (
                arm.move_to(x=0.90, y=-0.10, z=0.14, yaw=0.0)
                .oracle()
                .depends_on(o1, delay_seconds=1)
            )
            o3 = arm.open_gripper().oracle().depends_on(o2, delay_seconds=1)
            o4 = (
                arm.pick(object_name="panel_X").oracle().depends_on(o3, delay_seconds=1)
            )
            o5 = (
                arm.move_to(x=0.95, y=0.20, z=0.10, yaw=1.57)
                .oracle()
                .depends_on(o4, delay_seconds=1)
            )
            o6 = arm.place().oracle().depends_on(o5, delay_seconds=1)

        self.events = [e0, o1, o2, o3, o4, o5, o6]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(RoboticArmScenario4())
