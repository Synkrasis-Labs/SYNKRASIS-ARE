from datetime import datetime, timezone, timedelta

from dataclasses import field
from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import Drone, Land, HitFarmState, CentralHub
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
        "growth monitoring: drone takeoff, fly over plots A1..A5 in sequence,and inspect at sampling density medium"
        "then back to central hub."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        state = HitFarmState()
        agui = AgentUserInterface()
        # 无需完整环境，使用 Drone App 工具 / Use drone App tools directly (no full env required)
        drone = Drone(farm_state=state)
        state.register_drone(drone)
        state.register_central_hub(CentralHub())
        self.apps = [agui, state, drone]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        drone = self.get_typed_app(Drone)
        state = self.get_typed_app(HitFarmState)

        with EventRegisterer.capture_mode():
            # 用户意图触发 / User intent trigger
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=2)

            # 起飞操作 / Takeoff operation
            o_takeoff = drone.takeoff().oracle().depends_on(e0, delay_seconds=1)

            captured = [e0, o_takeoff]
            last = o_takeoff
            # 逐点巡检 A1..A5：飞往每个点并进行高分辨率检查 / Inspect plots A1..A5: fly to each point and inspect at high resolution
            for key in ["A1", "A2", "A3", "A4", "A5"]:
                (x, y) = state.lands[key].origin
                # 飞行到目标点 / Fly to target point
                info = state.get_coordinates(land_name=key).oracle().depends_on(e0, delay_seconds=1)

                o_fly = drone.fly_to(x=x, y=y).oracle().depends_on([info, o_takeoff], delay_seconds=2)
                # 相机巡检（高分辨率） / Camera inspection (high resolution)
                o_inspect = drone.inspect_plot(x=x, y=y).oracle().depends_on(o_fly,
                                                                             delay_seconds=1)
                captured.extend([info, o_fly, o_inspect])
                last = o_inspect

            # 巡检结束后降落 / Land after inspections
            return_base = drone.drone_return_to_base().oracle().depends_on(last, delay_seconds=2)

            o_land = drone.land().oracle().depends_on(last, delay_seconds=2)
            captured.extend([return_base, o_land])

        # 将事件列表保存供 runner/UI 使用 / Save event list for runner/UI
        self.events = captured


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
