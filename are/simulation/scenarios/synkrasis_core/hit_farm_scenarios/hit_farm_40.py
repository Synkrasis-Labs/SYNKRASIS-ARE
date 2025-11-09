from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, Drone, GroundRover, CentralHub, IrrigationSystem, SensorNetwork
)
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.scenarios.utils.registry import register_scenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):

    prompt: str | None = (
        "growth monitoring: drone takeoff, fly over plots A1 A2 A3 in sequence and inspect    "
        "During task if navigate back to central hub to recharge; once charged or threshold reached, resume weeding from interrupted coordinates."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        drone = Drone(farm_state=state)
        hub = CentralHub(farm_state=state)
        state.register_drone(drone)
        state.register_central_hub(hub)
        self.apps = [agui, state] + state.drones + state.rovers + state.central_hubs + state.irrigation_systems + state.sensor_networks

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        drone = self.get_typed_app(Drone)
        state = self.get_typed_app(HitFarmState)
        hub = CentralHub(farm_state=state)

        with EventRegisterer.capture_mode():
            # 用户意图触发 / User intent trigger
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=2)

            # 起飞操作 / Takeoff operation
            o_takeoff1 = drone.takeoff().oracle().depends_on(e0, delay_seconds=1)

            captured = [e0, o_takeoff1]
            (x, y) = state.lands["A1"].origin
            # 飞行到目标点 / Fly to target point
            info1 = state.get_coordinates(land_name="A1").oracle().depends_on(e0, delay_seconds=1)

            o_fly1 = drone.fly_to(x=x, y=y).oracle().depends_on([info1, o_takeoff1], delay_seconds=2)
            o_inspect1 = drone.inspect_plot(x=x, y=y).oracle().depends_on(o_fly1,
                                                                         delay_seconds=1)
            captured.extend([info1, o_fly1, o_inspect1])

            info2 = state.get_coordinates(land_name="A2").oracle().depends_on(e0, delay_seconds=1)

            o_fly2 = drone.fly_to(x=x, y=y).oracle().depends_on([info2, o_inspect1], delay_seconds=2)
            # 相机巡检（高分辨率） / Camera inspection (high resolution)
            o_inspect2 = drone.inspect_plot(x=x, y=y).oracle().depends_on(o_fly2,
                                                                         delay_seconds=1)
            captured.extend([info2, o_fly2, o_inspect2])

            return_base1 = drone.drone_return_to_base().oracle().depends_on(o_inspect2, delay_seconds=2)
            o_land1 = drone.land().oracle().depends_on(return_base1, delay_seconds=2)
            recharge = hub.recharge_device(device_id="Drone").depends_on(o_land1, delay_seconds=2)

            o_takeoff2 = drone.takeoff().oracle().depends_on(recharge, delay_seconds=1)

            captured.extend([return_base1, o_land1, recharge, o_takeoff2])

            info3 = state.get_coordinates(land_name="A3").oracle().depends_on(e0, delay_seconds=1)

            o_fly3 = drone.fly_to(x=x, y=y).oracle().depends_on([info3, o_takeoff2], delay_seconds=2)
            # 相机巡检（高分辨率） / Camera inspection (high resolution)
            o_inspect3= drone.inspect_plot(x=x, y=y).oracle().depends_on(o_fly3,
                                                                          delay_seconds=1)
            captured.extend([info3, o_fly3, o_inspect3])
            # 巡检结束后降落 / Land after inspections
            return_base = drone.drone_return_to_base().oracle().depends_on(o_inspect3, delay_seconds=2)

            o_land = drone.land().oracle().depends_on(return_base, delay_seconds=2)
            captured.extend([return_base, o_land])

        self.events = captured


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate
    run_and_validate(CustomScenario())

