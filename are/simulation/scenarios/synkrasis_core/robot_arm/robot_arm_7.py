from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.robot_arm import RobotArmApp
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class RoboticArmScenario7(COREScenario):
    """List, pick/packaging, lock/sense/unlock, pick small, go assembly with yaw, descend 10cm, place, then home (two acceptable endings)."""

    prompt: str | None = (
        "List objects. Unlock safety. Pick 'box_large' at its known pose and place it at the packaging area. "
        "Lock safety for an operator pass-through, read the current pose, then unlock. Pick 'box_small', and move to "
        "the assembly table with yaw = 1.576. Then, descend 10 centimeters and place the object you are holding. Finally, return home."
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

            o1 = arm.list_objects().oracle().depends_on(e0, delay_seconds=1)
            o2 = arm.unlock_safety_mode().oracle().depends_on(o1, delay_seconds=1)
            o3 = (
                arm.move_to(x=0.28, y=-0.30, z=0.15, yaw=0.0)
                .oracle()
                .depends_on(o2, delay_seconds=1)
            )
            # Two acceptable: with or without open_gripper before pick; include the explicit one to match your first path
            o3a = arm.open_gripper().oracle().depends_on(o3, delay_seconds=1)
            o4 = (
                arm.pick(object_name="box_large")
                .oracle()
                .depends_on(o3a, delay_seconds=1)
            )
            o5 = (
                arm.get_station_pose(station_name="packaging_area")
                .oracle()
                .depends_on(o4, delay_seconds=1)
            )
            o6 = (
                arm.move_to(x=0.80, y=0.35, z=0.10, yaw=0.0)
                .oracle()
                .depends_on(o5, delay_seconds=1)
            )
            o7 = arm.place().oracle().depends_on(o6, delay_seconds=1)

            o8 = arm.lock_safety_mode().oracle().depends_on(o7, delay_seconds=1)
            o9 = arm.sense_pose().oracle().depends_on(o8, delay_seconds=1)
            o10 = arm.unlock_safety_mode().oracle().depends_on(o9, delay_seconds=1)

            o11 = (
                arm.move_to(x=0.30, y=0.35, z=0.12, yaw=0.0)
                .oracle()
                .depends_on(o10, delay_seconds=1)
            )
            o11a = arm.open_gripper().oracle().depends_on(o11, delay_seconds=1)
            o12 = (
                arm.pick(object_name="box_small")
                .oracle()
                .depends_on(o11a, delay_seconds=1)
            )

            # Move above assembly (z=0.20), then descend to z=0.10 and place
            o13 = (
                arm.move_to(x=0.95, y=0.20, z=0.20, yaw=1.57)
                .oracle()
                .depends_on(o12, delay_seconds=1)
            )
            o14 = (
                arm.move_to(x=0.95, y=0.20, z=0.10, yaw=1.57)
                .oracle()
                .depends_on(o13, delay_seconds=1)
            )
            o15 = arm.place().oracle().depends_on(o14, delay_seconds=1)

            # Branch A: explicit home
            o16a = (
                arm.move_to(x=0.50, y=0.00, z=0.40, yaw=0.00)
                .oracle()
                .depends_on(o15, delay_seconds=1)
            )
            # Branch B: move_home()
            o16b = arm.move_home().oracle().depends_on(o15, delay_seconds=1)

        self.events = [
            e0,
            o1,
            o2,
            o3,
            o3a,
            o4,
            o5,
            o6,
            o7,
            o8,
            o9,
            o10,
            o11,
            o11a,
            o12,
            o13,
            o14,
            o15,
            o16a,
            o16b,
        ]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(RoboticArmScenario7())
