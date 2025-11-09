from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, Drone, GroundRover, CentralHub, IrrigationSystem, SensorNetwork
)
from are.simulation.types import EventRegisterer
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.scenarios.utils.registry import register_scenario


@register_scenario("hit_farm_31")
class MaizeNitrogenCheck(COREScenario):
    """
    scenarios31: 玉米氮素检查与纠偏 | Maize N check & corrective
    - Read nitrogen index in A1; if index < 0.8, apply corrective urea at 50 kg/ha
    - Recheck N index after application
    """

    prompt: str | None = (
        "A1: Read nitrogen ; if < 0.8, apply corrective topdressing with urea at 50 kg/ha; "
        "recheck nitrogen  after application."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        state.lands["A1"].grid[0][0].nutrient_level = {'nitrogen': 0.75}
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
        self.apps = [agui,
                     state] + state.drones + state.rovers + state.central_hubs + state.irrigation_systems + state.sensor_networks

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        rover = self.get_typed_app(GroundRover)
        hub = self.get_typed_app(CentralHub)
        sensors = self.get_typed_app(SensorNetwork)

        with EventRegisterer.capture_mode():
            # Single user message to trigger the entire workflow
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # Get coordinates for A1
            info = state.get_coordinates(land_name="A1").oracle().depends_on(e0, delay_seconds=1)

            # Get nutrient level to confirm low nitrogen
            (x, y) = state.lands["A1"].origin
            o_nutrient = sensors.get_nutrient_level(x=x, y=y).oracle().depends_on(info, delay_seconds=1)

            # Refill fertilizer (urea) at hub - 50 kg/ha
            o_refill = hub.refill_fertilizer(device_id=rover.state.device_id, amount_kg=50.0).oracle().depends_on(
                o_nutrient, delay_seconds=1)

            # Move to A1
            o_move = rover.move_to(x=x, y=y).oracle().depends_on([info, o_refill], delay_seconds=1)

            # Apply corrective fertilizer (urea topdressing)
            o_apply = rover.apply_fertilizer(kg=50.0).oracle().depends_on(o_move, delay_seconds=0)

            # Return to base
            o_return = rover.return_to_base().oracle().depends_on(o_apply, delay_seconds=1)

            # Get nutrient level again to confirm improvement
            o_nutrient_after = sensors.get_nutrient_level(x=x, y=y).oracle().depends_on(o_apply, delay_seconds=1)

        self.events = [e0, info, o_nutrient, o_refill, o_move, o_apply, o_return,
                       o_nutrient_after]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(MaizeNitrogenCheck())
