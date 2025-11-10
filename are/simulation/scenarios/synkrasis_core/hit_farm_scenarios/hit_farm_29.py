from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, Drone, GroundRover, CentralHub, IrrigationSystem, SensorNetwork
)
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.scenarios.utils.registry import register_scenario
from are.simulation.types import EventRegisterer


@register_scenario("hit_farm_29")
class RiceBPHControl(COREScenario):
    """
    scenarios29: 水稻褐飞虱处置 | Rice BPH control
    - Reconfirm BPH counts in B2; if mean ≥22 per hill, apply pymetrozine at 20 L/ha via UAV
    - Maintain 3 cm flood for
    """

    prompt: str | None = (
        "B2: Reconfirm bph density; if ≥0.1 per m² , apply pesticide 1000.0 ml via drone spray volume , "
        "and maintain 3 cm water layer  to stabilize and assess efficacy."
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
        self.apps = [agui, state] + state.drones + state.rovers + state.central_hubs + state.irrigation_systems + state.sensor_networks

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        drone = self.get_typed_app(Drone)
        hub = self.get_typed_app(CentralHub)
        irrigation = self.get_typed_app(IrrigationSystem)
        sensors = self.get_typed_app(SensorNetwork)

        with EventRegisterer.capture_mode():
            # Single user message to trigger the entire workflow
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # Get coordinates for B2
            info = state.get_coordinates(land_name="B2").oracle().depends_on(e0, delay_seconds=1)

            o_bph_check =  sensors.check_pest_infestation(land_name ="B2" , pest_type="bph").oracle().depends_on(e0, delay_seconds=1)

            # Refill pesticide (pymetrozine, 20 L/ha equivalent to 20000 ml/ha, assume ~560 ml for B2 area)
            o_refill = hub.refill_pesticide(device_id=drone.state.device_id, amount_ml=1000.0).oracle().depends_on(
                o_bph_check, delay_seconds=1)
            # Drone pesticide application
            # Takeoff
            o_takeoff = drone.takeoff().oracle().depends_on(o_refill, delay_seconds=1)



            # Fly to B2
            (x, y) = state.lands["B2"].origin
            o_fly = drone.fly_to(x=x, y=y).oracle().depends_on([info, o_refill], delay_seconds=1)

            # Apply pesticide
            o_spray = drone.apply_pesticide(area="B2", amount_ml=1000.0).oracle().depends_on(o_fly, delay_seconds=1)

            # Return to base and land
            o_return = drone.drone_return_to_base().oracle().depends_on(o_spray, delay_seconds=1)
            o_land = drone.land().oracle().depends_on(o_return, delay_seconds=1)

            # Establish 3 cm water layer
            o_water_before = sensors.get_water_depth(land_name="B2").oracle().depends_on(o_land, delay_seconds=1)
            o_open_valve = irrigation.open_valve(land_name="B2",water_depth_cm=3.0).oracle().depends_on(
                o_water_before, delay_seconds=1)

            # Monitor water depth to ensure 3 cm
            o_water_check = sensors.get_water_depth(land_name="B2").oracle().depends_on(o_open_valve, delay_seconds=1)
            o_close_valve = irrigation.close_valve(land_name="B2").oracle().depends_on(o_water_check, delay_seconds=1)

            # Monitor after 24 hours
            o_water_24h = sensors.get_water_depth(land_name="B2").oracle().depends_on(o_close_valve, delay_seconds=1)

        self.events = [e0, info, o_bph_check, o_takeoff, o_refill, o_fly, o_spray, o_return, o_land,
                      o_water_before, o_open_valve, o_water_check, o_close_valve, o_water_24h]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate
    run_and_validate(RiceBPHControl())

