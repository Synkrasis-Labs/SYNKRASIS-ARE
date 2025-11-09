from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, Drone, CentralHub, IrrigationSystem, SensorNetwork
)
from are.simulation.types import EventRegisterer
from are.simulation.scenarios.core_scenario import COREScenario


class CustomScenario(COREScenario):
    """
    scenarios14_2: Soybean stale-seedbed protocol in C1
    - Prepare soil → induce weed flush → remove weeds
    """

    prompt: str | None = (
        "C1: stale-seedbed - till/firm, keep moist for weed flush(soil moisture>=0.6) , remove weeds by pesticide."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        drone = Drone(farm_state=state)
        hub = CentralHub(farm_state=state)
        irrigation = IrrigationSystem(farm_state=state)
        sensors = SensorNetwork(farm_state=state)
        state.register_drone(drone)
        state.register_central_hub(hub)
        state.register_irrigation_system(irrigation)
        state.register_sensor_network(sensors)

        self.apps = [agui, state, drone, hub, irrigation, sensors]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        hub = self.get_typed_app(CentralHub)
        drone = self.get_typed_app(Drone)
        sensors = self.get_typed_app(SensorNetwork)

        with EventRegisterer.capture_mode():
            # Single user message to trigger the entire workflow
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # Get coordinates for C1
            info = state.get_coordinates(land_name="C1").oracle().depends_on(e0, delay_seconds=1)
            (x, y) = state.lands["C1"].origin
            # Set initial moisture for seedbed preparation
            e_moist = sensors.get_soil_moisture(x,y).oracle().depends_on(info, delay_seconds=1)

            # Refill pesticide at hub first
            o_pesticide = hub.refill_pesticide(device_id=drone.state.device_id, amount_ml=500.0).oracle().depends_on(
                e_moist, delay_seconds=1)

            # Weed removal using drone spray
            e_takeoff = drone.takeoff().oracle().depends_on(e_moist, delay_seconds=1)

            e_fly = drone.fly_to(x=x, y=y).oracle().depends_on(o_pesticide, delay_seconds=1)
            e_apply = drone.apply_pesticide(area="C1", amount_ml=500.0).oracle().depends_on(e_fly, delay_seconds=1)
            e_return = drone.drone_return_to_base().oracle().depends_on(e_apply, delay_seconds=1)
            e_land = drone.land().oracle().depends_on(e_return, delay_seconds=1)

        self.events = [e0, info, e_moist, e_takeoff, o_pesticide, e_fly, e_apply, e_return, e_land]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate
    run_and_validate(CustomScenario())


