from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, GroundRover, Drone, CentralHub
)
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.scenarios.utils.registry import register_scenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    scenarios44: Plant soybeans in C2 land. 48 hours later, apply a pre-emergent herbicide.
    """

    prompt: str | None = (
        "Plant about 1200 soybeans in C2 land set 38 cm rows, 5 cm depth, 10 cm spacing . "
        "48 hours later , apply a pre-emergent herbicide 1000ml."
        "return to the base after all is completed."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        rover = GroundRover(farm_state=state, device_id='rover-1')
        drone = Drone(farm_state=state)
        hub = CentralHub(farm_state=state)

        state.register_rover(rover)
        state.register_drone(drone)
        state.register_central_hub(hub)

        self.apps = [agui, state, rover, drone, hub]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        rover = self.get_typed_app(GroundRover)
        drone = self.get_typed_app(Drone)
        hub = self.get_typed_app(CentralHub)

        with EventRegisterer.capture_mode():
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # Get C2 coordinates
            info = state.get_coordinates(land_name="C2").oracle().depends_on(e0, delay_seconds=1)
            (x, y) = state.lands["C2"].origin

            # Load soybean seeds
            o_load = hub.refill_seeds(device_id=rover.state.device_id, seed_type="soybean",
                                      count=1200).oracle().depends_on(
                info, delay_seconds=1)

            # Move to C2
            o_move = rover.move_to(x=x, y=y).oracle().depends_on(o_load, delay_seconds=1)

            # Plant soybeans
            o_plant = rover.plant_seed(seed_type="soybean", row_spacing_cm=38.0, depth_cm=5.0,
                                       in_row_spacing_cm=10.0).oracle().depends_on(
                o_move, delay_seconds=2)

            # Return to base after planting
            o_return_1 = rover.return_to_base().oracle().depends_on(o_plant, delay_seconds=1)

            # Schedule herbicide application 48 hours later (2880 minutes)
            o_schedule = state.schedule_in(time="48 hours").oracle().depends_on(o_return_1, delay_seconds=1)

            # Refill drone with pre-emergent herbicide
            o_refill = hub.refill_pesticide(device_id=drone.state.device_id, amount_ml=1000.0).oracle().depends_on(
                o_schedule, delay_seconds=1)

            # Drone applies pre-emergent herbicide
            o_takeoff = drone.takeoff().oracle().depends_on(o_refill, delay_seconds=1)
            o_fly = drone.fly_to(x=x, y=y).oracle().depends_on(o_takeoff, delay_seconds=1)
            o_spray = drone.apply_pesticide(area="C2_preemergent", amount_ml=1000.0).oracle().depends_on(
                o_fly, delay_seconds=2)

            # Return to base
            o_return_2 = drone.drone_return_to_base().oracle().depends_on(o_spray, delay_seconds=1)
            o_land = drone.land().oracle().depends_on(o_return_2, delay_seconds=1)

        self.events = [e0, info, o_load, o_move, o_plant, o_return_1, o_schedule, o_refill,
                       o_takeoff, o_fly, o_spray, o_return_2, o_land]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
