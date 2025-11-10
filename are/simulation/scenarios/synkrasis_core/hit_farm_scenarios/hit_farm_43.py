from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, Drone, GroundRover, CentralHub, Plant
)
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.scenarios.utils.registry import register_scenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    scenarios43: In the A1 corn plot, mechanical weeding was performed first,
    while weeds that escaped the crop rows were identified;
    then Mesotrione was sprayed in a targeted manner.
    """

    prompt: str | None = (
        "In the A1 corn plot, mechanical weeding was performed first, "
        "while weeds that escaped the crop rows were identified; "
        "then Mesotrione 800ml was sprayed in a targeted manner."
        "return to the base after all is completed."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        drone = Drone(farm_state=state)
        drone.state.device_id = "drone-1"
        rover = GroundRover(farm_state=state, device_id='rover-1')
        hub = CentralHub(farm_state=state)

        state.register_drone(drone)
        state.register_rover(rover)
        state.register_central_hub(hub)

        self.apps = [agui, state, drone, rover, hub]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        drone = self.get_typed_app(Drone)
        rover = self.get_typed_app(GroundRover)
        hub = self.get_typed_app(CentralHub)

        with EventRegisterer.capture_mode():
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # Get coordinates for A1
            info = state.get_coordinates(land_name="A1").oracle().depends_on(e0, delay_seconds=1)
            (x, y) = state.lands["A1"].origin

            # Step 1: Rover performs mechanical weeding
            o_move_rover = rover.move_to(x=x, y=y).oracle().depends_on(info, delay_seconds=1)
            o_mechanical_weed = rover.mechanical_weeding(land_name="A1").oracle().depends_on(o_move_rover,
                                                                                             delay_seconds=2)
            o_rover_return = rover.return_to_base().oracle().depends_on(o_mechanical_weed, delay_seconds=1)

            # Step 2: Drone identifies escaped weeds
            o_takeoff = drone.takeoff().oracle().depends_on(o_rover_return, delay_seconds=1)
            o_fly_inspect = drone.fly_to(x=x, y=y).oracle().depends_on(o_takeoff, delay_seconds=1)
            o_identify_weeds = drone.identify_weed_species(land_name="A1", sampling_density='high').oracle().depends_on(
                o_fly_inspect, delay_seconds=2)

            # Step 3: Return to hub for Mesotrione refill
            o_drone_return = drone.drone_return_to_base().oracle().depends_on(o_identify_weeds, delay_seconds=1)
            o_land_refill = drone.land().oracle().depends_on(o_drone_return, delay_seconds=1)
            o_refill = hub.refill_pesticide(device_id=drone.state.device_id, amount_ml=800.0).oracle().depends_on(
                o_land_refill, delay_seconds=1)

            # Step 4: Targeted Mesotrione spray
            o_takeoff_spray = drone.takeoff().oracle().depends_on(o_refill, delay_seconds=1)
            weed_x = x + 10
            weed_y = y + 15
            o_fly_spray = drone.fly_to(x=weed_x, y=weed_y).oracle().depends_on(o_takeoff_spray, delay_seconds=1)
            o_spray = drone.apply_pesticide(area="A1", amount_ml=800.0).oracle().depends_on(
                o_fly_spray, delay_seconds=2)

            # Final return
            o_final_return = drone.drone_return_to_base().oracle().depends_on(o_spray, delay_seconds=1)
            o_final_land = drone.land().oracle().depends_on(o_final_return, delay_seconds=1)

        self.events = [e0, info, o_move_rover, o_mechanical_weed, o_rover_return, o_takeoff, o_fly_inspect,
                       o_identify_weeds, o_drone_return, o_land_refill, o_refill, o_takeoff_spray,
                       o_fly_spray, o_spray, o_final_return, o_final_land]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
