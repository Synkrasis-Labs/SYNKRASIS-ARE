from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, Drone, CentralHub, SensorNetwork, Plant
)
from are.simulation.types import EventRegisterer
from are.simulation.scenarios.core_scenario import COREScenario


class CustomScenario(COREScenario):
    """
    scenarios28: Re-check wheat aphid infestation in D3 and spray if needed
    - Re-check for D3 wheat aphid infestation
    - If re-check result is still higher than threshold, spray pesticides on wheat
    """

    prompt: str | None = (
        "check for D3 wheat aphid infestation with sensor; if the check result is  higher "
        "than the threshold(0.2), spray pesticides on the wheat. "
        "After completing spray pesticides, return to central hub."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        drone = Drone(farm_state=state)
        hub = CentralHub(farm_state=state)
        sensors = SensorNetwork(farm_state=state)
        state.register_drone(drone)
        state.register_central_hub(hub)
        state.register_sensor_network(sensors)

        self.apps = [agui, state, drone, hub, sensors]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        drone = self.get_typed_app(Drone)
        hub = self.get_typed_app(CentralHub)
        sensors = self.get_typed_app(SensorNetwork)

        with EventRegisterer.capture_mode():
            # Single user message to trigger the entire workflow
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # Get coordinates for D3
            info = state.get_coordinates(land_name="D3").oracle().depends_on(e0, delay_seconds=1)
            (x, y) = state.lands["D3"].origin

            # First check for aphid infestation
            o_check_1 = sensors.check_pest_infestation(land_name="D3", pest_type="aphid").oracle().depends_on(
                info, delay_seconds=1)

            # Refill pesticide at hub
            o_refill = hub.refill_pesticide(device_id=drone.state.device_id, amount_ml=1000.0).oracle().depends_on(
                o_check_1, delay_seconds=1)
            # If still above threshold, prepare drone for pesticide application
            o_takeoff = drone.takeoff().oracle().depends_on(o_refill, delay_seconds=1)

            # Fly to D3
            o_fly = drone.fly_to(x=x, y=y).oracle().depends_on([info, o_refill], delay_seconds=2)

            # Apply pesticide to control aphids
            o_spray = drone.apply_pesticide(area="D3", amount_ml=800.0).oracle().depends_on(o_fly, delay_seconds=1)

            # Return to base and land
            o_return = drone.drone_return_to_base().oracle().depends_on(o_spray, delay_seconds=2)
            o_land = drone.land().oracle().depends_on(o_return, delay_seconds=1)

            # Final verification check
            o_verify = sensors.check_pest_infestation(land_name="D3", pest_type="aphid").oracle().depends_on(
                o_land, delay_seconds=2)

        self.events = [e0, info, o_check_1, o_refill, o_takeoff, o_fly,
                       o_spray, o_return, o_land, o_verify]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
