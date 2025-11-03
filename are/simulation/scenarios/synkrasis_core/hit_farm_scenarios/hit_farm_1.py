from datetime import datetime, timezone, timedelta

from dataclasses import field
from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import Drone, Land, HitFarmState
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.scenarios.utils.registry import register_scenario
from are.simulation.types import EventRegisterer

class CustomScenario(COREScenario):
    """
    生长期生长状况监测：每周一次无人机巡检作物生长与健康。
    Growth monitoring during vegetative stage: weekly drone inspections for growth and health.

    流程：
    1) 无人机起飞并按航线覆盖 A1..A5
    2) 在每个地块悬停并进行高分辨率检查
    3) 记录结果并返回基地降落

    Flow:
    1) Drone takeoff and follow route covering plots A1..A5
    2) Hover at each plot and perform high-resolution inspection
    3) Log observations and return to base to land
    """

    prompt: str | None = (
        "growth monitoring: drone takeoff, fly over plots A1..A5, inspect at high resolution, then land."
    )

    plots: dict[str, tuple[float, float, float]] = field(default_factory=lambda: {
        "A1": (15, 15, 10.0),
        "A2": (50, 12, 10.0),
        "A3": (82, 12, 10.0),
        "A4": (20, 42, 10.0),
        "A5": (57, 47, 10.0)
    })

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        state = HitFarmState()
        agui = AgentUserInterface()
        # 无需完整环境，使用 Drone App 工具 / Use drone App tools directly (no full env required)
        drone = Drone(initial_pos=(0.0, 0.0, 20.0), speed_mps=15.0, consumption_rate=0.5,
                      battery_percentage=100.0, pesticide_tank_ml=0.0, camera_status=True)
        self.apps = [agui, state,drone]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        drone = self.get_typed_app(Drone)

        with EventRegisterer.capture_mode():
            # 用户意图触发 / User intent trigger
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=2)

            # 起飞操作 / Takeoff operation
            o_takeoff = drone.takeoff().oracle().depends_on(e0, delay_seconds=1)

            captured = [e0, o_takeoff]
            last = o_takeoff
            # 逐点巡检 A1..A5：飞往每个点并进行高分辨率检查 / Inspect plots A1..A5: fly to each point and inspect at high resolution
            for key in ["A1", "A2", "A3", "A4", "A5"]:
                x, y, z = self.plots[key]
                # 飞行到目标点 / Fly to target point
                o_fly = drone.fly_to(x=x, y=y, z=z).oracle().depends_on(last, delay_seconds=2)
                # 相机巡检（高分辨率） / Camera inspection (high resolution)
                o_inspect = drone.inspect_plot(x=x, y=y, resolution=(1920, 1080)).oracle().depends_on(o_fly, delay_seconds=1)
                captured.extend([o_fly, o_inspect])
                last = o_inspect

            # 巡检结束后降落 / Land after inspections
            o_land = drone.land().oracle().depends_on(last, delay_seconds=2)
            captured.append(o_land)

        # 将事件列表保存供 runner/UI 使用 / Save event list for runner/UI
        self.events = captured


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate
    run_and_validate(CustomScenario())
