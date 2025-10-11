from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.robot_arm import RoboticArmApp
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class RoboticArmScenario3(COREScenario):
    """Sense pose, list objects, pick gear_A, place at packaging pose."""

    prompt: str | None = (
        "Unlock safety. Check pose and list objects in ther order. Move to the pose of 'gear_A' and pick it. "
        "Then place it at (0.80, 0.35, 0.10, yaw=0.0)."
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
            o2 = arm.sense_pose().oracle().depends_on(o1, delay_seconds=1)
            o3 = arm.list_objects().oracle().depends_on(o2, delay_seconds=1)
            o4 = (
                arm.move_to(x=0.60, y=0.10, z=0.11, yaw=0.0)
                .oracle()
                .depends_on(o3, delay_seconds=1)
            )
            o5 = arm.open_gripper().oracle().depends_on(o4, delay_seconds=1)
            o6 = arm.pick(object_name="gear_A").oracle().depends_on(o5, delay_seconds=1)
            o7 = (
                arm.move_to(x=0.80, y=0.35, z=0.10, yaw=0.0)
                .oracle()
                .depends_on(o6, delay_seconds=1)
            )
            o8 = arm.place().oracle().depends_on(o7, delay_seconds=1)

        self.events = [e0, o1, o2, o3, o4, o5, o6, o7, o8]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(RoboticArmScenario3())
