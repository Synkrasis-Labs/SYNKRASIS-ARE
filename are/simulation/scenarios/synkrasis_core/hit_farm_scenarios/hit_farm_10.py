from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, Drone, GroundRover, CentralHub
)
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    Scenario 10: All devices return to Central Hub, and recharge.
    """

    prompt: str | None = (
        "All devices return to Central Hub, and recharge."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()

        # Register multiple devices with low battery
        drone1 = Drone(farm_state=state)
        drone1.state.device_id = "drone-1"
        drone1.state.battery_percentage = 45.0
        drone1.state.position = (50.0, 50.0, 0.0)

        drone2 = Drone(farm_state=state)
        drone2.state.device_id = "drone-2"
        drone2.state.battery_percentage = 38.0
        drone2.state.position = (80.0, 80.0, 0.0)

        rover1 = GroundRover(farm_state=state, device_id='rover-1')
        rover1.state.battery_percentage = 52.0
        rover1.state.position = (60.0, 70.0)

        rover2 = GroundRover(farm_state=state, device_id='rover-2')
        rover2.state.battery_percentage = 41.0
        rover2.state.position = (100.0, 90.0)

        hub = CentralHub(farm_state=state)

        state.register_drone(drone1)
        state.register_drone(drone2)
        state.register_rover(rover1)
        state.register_rover(rover2)
        state.register_central_hub(hub)

        self.apps = [agui, state, drone1, drone2, rover1, rover2, hub]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        hub = self.get_typed_app(CentralHub)

        # Get all drones and rovers
        drones = state.drones
        rovers = state.rovers

        with EventRegisterer.capture_mode():
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # All devices return to base
            return_events = []

            # Drones return to base
            for drone in drones:
                o_return = drone.drone_return_to_base().oracle().depends_on(e0, delay_seconds=1)
                return_events.append(o_return)

            # Rovers return to base
            for rover in rovers:
                o_return = rover.return_to_base().oracle().depends_on(e0, delay_seconds=1)
                return_events.append(o_return)

            # All devices recharge after returning
            recharge_events = []
            for drone in drones:
                o_recharge = hub.recharge_device(device_id=drone.state.device_id, amount=None).oracle().depends_on(
                    return_events, delay_seconds=1)
                recharge_events.append(o_recharge)

            for rover in rovers:
                o_recharge = hub.recharge_device(device_id=rover.state.device_id, amount=None).oracle().depends_on(
                    return_events, delay_seconds=1)
                recharge_events.append(o_recharge)

        self.events = [e0] + return_events + recharge_events


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
