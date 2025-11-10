from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, Drone, GroundRover, CentralHub, IrrigationSystem, SensorNetwork
)
from are.simulation.types import EventRegisterer
from are.simulation.scenarios.core_scenario import COREScenario


class CustomScenario(COREScenario):
    """
    scenarios14: Soybean stale-seedbed protocol in C1
    - Prepare soil → induce weed flush → remove weeds → then plant soybeans set 38 cm rows, 5 cm depth, 10 cm spacing.
    """

    prompt: str | None = (
        "C1: stale-seedbed - till/firm, keep moist for weed flush(soil moisture>=0.6) , remove weeds by pesticide, then plant soybeans set 38 cm rows, 5 cm depth, 10 cm spacing"
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        drone = Drone(farm_state=state)
        rover = GroundRover(farm_state=state, device_id='rover-1')
        hub = CentralHub(farm_state=state)
        irrigation = IrrigationSystem(farm_state=state)
        sensors = SensorNetwork(farm_state=state)
        state.register_drone(drone)
        state.register_rover(rover)
        state.register_central_hub(hub)
        state.register_irrigation_system(irrigation)
        state.register_sensor_network(sensors)

        self.apps = [agui, state, drone, rover, hub, irrigation, sensors]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        rover = self.get_typed_app(GroundRover)
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
            e_moist = sensors.get_soil_moisture(x, y).oracle().depends_on(info, delay_seconds=1)

            # Refill pesticide at hub first
            o_pesticide = hub.refill_pesticide(device_id=drone.state.device_id, amount_ml=500.0).oracle().depends_on(
                e_moist, delay_seconds=1)

            # Weed removal using drone spray
            e_takeoff = drone.takeoff().oracle().depends_on(e_moist, delay_seconds=1)

            e_fly = drone.fly_to(x=x, y=y).oracle().depends_on(o_pesticide, delay_seconds=1)
            e_apply = drone.apply_pesticide(area="C1", amount_ml=500.0).oracle().depends_on(e_fly, delay_seconds=1)
            e_return = drone.drone_return_to_base().oracle().depends_on(e_apply, delay_seconds=1)
            e_land = drone.land().oracle().depends_on(e_return, delay_seconds=1)

            # Load seeds and plant soybeans 38 cm rows, 5 cm depth, 10 cm spacing
            e_load_hub = hub.refill_seeds(device_id=rover.state.device_id, seed_type="soybean",
                                          count=1200).oracle().depends_on(e_land, delay_seconds=1)

            o_move = rover.move_to(x=x, y=y).oracle().depends_on([info, e_load_hub], delay_seconds=1)
            o_plant = rover.plant_seed(seed_type="soybean", row_spacing_cm=38.0, depth_cm=5.0,
                                       in_row_spacing_cm=10.0).oracle().depends_on(o_move, delay_seconds=0)
            o_return = rover.return_to_base().oracle().depends_on(o_plant, delay_seconds=1)

        self.events = [e0, info, e_moist, e_takeoff, o_pesticide, e_fly, e_apply, e_return, e_land, e_load_hub, o_move,
                       o_plant, o_return]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
