from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    Drone, GroundRover, CentralHub, SensorNetwork, HitFarmState
)
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    scenarios36: During patrol of plot D3, if temperature >150°C and smoke sensor triggers,
    initiate emergency response: report, deploy onboard water suppression, continuous monitoring,
    and recall all devices operating in the zone.
    """

    prompt: str | None = (
        "Drone  patrol  D3;  detects temperature spike to 165°C and smoke sensor triggers in D3. "
        " attempt onboard water suppression if equipped, "
        "recall all agricultural devices from D3 zone "
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        drone = Drone(farm_state=state)
        rover = GroundRover(farm_state=state, device_id='rover-01')
        hub = CentralHub(farm_state=state)
        sensor = SensorNetwork(farm_state=state)

        state.register_drone(drone)
        state.register_rover(rover)
        state.register_central_hub(hub)

        # Simulate fire conditions in D3
        d4_land = state.lands.get('D3')
        cell = d4_land.grid[0][0]
        cell.temperature_celsius = 165.0
        cell.smoke_level = 0.85

        self.apps = [agui, state, drone, rover, hub, sensor]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        drone = self.get_typed_app(Drone)
        rover = self.get_typed_app(GroundRover)
        sensor = self.get_typed_app(SensorNetwork)

        with EventRegisterer.capture_mode():
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # Get D3 coordinates
            (x, y) = state.lands["D3"].origin

            # Drone patrol D3
            e2 = drone.takeoff().oracle().depends_on(e0, delay_seconds=1)
            e3 = drone.fly_to(x=x, y=y).oracle().depends_on(e2, delay_seconds=1)

            # Check temperature and smoke
            e4 = sensor.get_temperature(x=x, y=y).oracle().depends_on(e0, delay_seconds=1)
            e5 = sensor.get_smoke_level(x=x, y=y).oracle().depends_on(e4, delay_seconds=1)

            # Recall drone
            e7 = drone.drone_return_to_base().oracle().depends_on(e5, delay_seconds=1)
            e8 = drone.land().oracle().depends_on(e7, delay_seconds=1)

        self.events = [e0, e2, e3, e4, e5, e7, e8]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
