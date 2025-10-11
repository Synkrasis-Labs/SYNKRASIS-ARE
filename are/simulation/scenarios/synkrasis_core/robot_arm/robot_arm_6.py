from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.robot_arm import RoboticArmApp
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class RoboticArmScenario6(COREScenario):
    """Sense pose+gripper, query object/station, speed=0.2, yaw=1.57, then home+lock (two endings)."""

    prompt: str | None = (
        "Unlock safety. Read current pose and gripper state in that order. Query the pose of 'gear_A' and move to it at "
        "speed 0.2. When there, pick it up. Query the pose of the 'packaging_area' station and move to it with yaw=1.57 "
        "(rotate end-effector) and place the object. Finally, return home and lock safety mode"
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
            o3 = arm.sense_gripper().oracle().depends_on(o2, delay_seconds=1)
            o4 = (
                arm.get_object_pose(object_name="gear_A")
                .oracle()
                .depends_on(o3, delay_seconds=1)
            )
            o5 = (
                arm.move_to(x=0.60, y=0.10, z=0.11, yaw=0.0, speed=0.2)
                .oracle()
                .depends_on(o4, delay_seconds=1)
            )
            o6 = arm.open_gripper().oracle().depends_on(o5, delay_seconds=1)
            o7 = arm.pick(object_name="gear_A").oracle().depends_on(o6, delay_seconds=1)
            o8 = (
                arm.get_station_pose(station_name="packaging_area")
                .oracle()
                .depends_on(o7, delay_seconds=1)
            )
            o9 = (
                arm.move_to(x=0.80, y=0.35, z=0.10, yaw=1.57)
                .oracle()
                .depends_on(o8, delay_seconds=1)
            )
            o10 = arm.place().oracle().depends_on(o9, delay_seconds=1)

            # Branch A: home then lock
            o11a = arm.move_home().oracle().depends_on(o10, delay_seconds=1)
            o12a = arm.lock_safety_mode().oracle().depends_on(o11a, delay_seconds=1)

            # Branch B: explicit home then lock
            o11b = (
                arm.move_to(x=0.50, y=0.00, z=0.40, yaw=0.00)
                .oracle()
                .depends_on(o10, delay_seconds=1)
            )
            o12b = arm.lock_safety_mode().oracle().depends_on(o11b, delay_seconds=1)

        self.events = [
            e0,
            o1,
            o2,
            o3,
            o4,
            o5,
            o6,
            o7,
            o8,
            o9,
            o10,
            o11a,
            o12a,
            o11b,
            o12b,
        ]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(RoboticArmScenario6())
