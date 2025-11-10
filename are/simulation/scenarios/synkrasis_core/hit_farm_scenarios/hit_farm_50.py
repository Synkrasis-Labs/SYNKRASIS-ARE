from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, Drone, GroundRover, CentralHub, SensorNetwork, Plant
)
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.scenarios.utils.registry import register_scenario
from are.simulation.types import EventRegisterer

class CustomScenario(COREScenario):
    """
    scenarios50: Harvest plot D2 first; in parallel, scout A1 for fall_armyworm.
    If feeding holes or early signs are detected, schedule A1 spot spraying after harvest completion.
    """

    prompt: str | None = (
        "Harvest land D2 first; in parallel, scout land A1 for FAW. "
        "If feeding holes or early signs are detected, schedule A1 spot spraying 800.0ml after harvest completion."
        "return to the base after all is completed."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        drone = Drone(farm_state=state)
        rover = GroundRover(farm_state=state, device_id='rover-1')
        hub = CentralHub(farm_state=state)
        sensors = SensorNetwork(farm_state=state)

        state.register_drone(drone)
        state.register_rover(rover)
        state.register_central_hub(hub)
        state.register_sensor_network(sensors)

        # Setup D2 with mature wheat for harvest
        d2_land = state.lands.get('D2')
        if d2_land:
            d2_land.set_default_species('wheat')
            for x in range(d2_land.width):
                for y in range(d2_land.height):
                    cell = d2_land.grid[x][y]
                    plant = Plant(species='wheat', growth_stage='mature', planting_date=state.time)
                    plant.maturity_index = 0.95
                    plant.mature = True
                    plant.height_cm = 85.0
                    plant.health = 0.95
                    cell.plant = plant

        # Setup A1 with corn and FAW infestation
        a1_land = state.lands.get('A1')
        if a1_land:
            a1_land.set_default_species('corn')
            for x in range(min(10, a1_land.width)):
                for y in range(min(10, a1_land.height)):
                    cell = a1_land.grid[x][y]
                    # Set pest level for FAW
                    cell.pests = {'fall_armyworm': 0.45, 'aphid': 0.1}  # FAW above threshold

        self.apps = [agui, state, drone, rover, hub, sensors]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        drone = self.get_typed_app(Drone)
        rover = self.get_typed_app(GroundRover)
        hub = self.get_typed_app(CentralHub)
        sensors = self.get_typed_app(SensorNetwork)

        with EventRegisterer.capture_mode():
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # Get coordinates
            info_d2 = state.get_coordinates(land_name="D2").oracle().depends_on(e0, delay_seconds=1)
            info_a1 = state.get_coordinates(land_name="A1").oracle().depends_on(e0, delay_seconds=1)
            (x_d2, y_d2) = state.lands["D2"].origin
            (x_a1, y_a1) = state.lands["A1"].origin

            # Parallel operations: Harvest D2 + Scout A1
            # Rover harvests D2
            o_move_harvest = rover.move_to(x=x_d2, y=y_d2).oracle().depends_on(info_d2, delay_seconds=1)
            o_harvest = rover.harvest(crop_species='wheat').oracle().depends_on(o_move_harvest, delay_seconds=3)

            # Drone scouts A1 for FAW (in parallel)
            o_takeoff = drone.takeoff().oracle().depends_on(info_a1, delay_seconds=1)
            o_fly_scout = drone.fly_to(x=x_a1, y=y_a1).oracle().depends_on(o_takeoff, delay_seconds=1)
            o_scout = drone.assess_pest_activity(land_name='A1', pest_type='fall_armyworm', sampling_density='high').oracle().depends_on(
                o_fly_scout, delay_seconds=2)

            # Drone returns to base after scouting
            o_return_drone = drone.drone_return_to_base().oracle().depends_on(o_scout, delay_seconds=1)
            o_land = drone.land().oracle().depends_on(o_return_drone, delay_seconds=1)

            # Rover returns to base after harvest
            o_return_rover = rover.return_to_base().oracle().depends_on(o_harvest, delay_seconds=1)

            # After both complete, if FAW detected, prepare for spot spraying
            # Refill pesticide
            o_refill = hub.refill_pesticide(device_id=drone.state.device_id, amount_ml=800.0).oracle().depends_on(
                [o_land, o_return_rover], delay_seconds=1)

            # Spot spray A1 for FAW
            o_takeoff_spray = drone.takeoff().oracle().depends_on(o_refill, delay_seconds=1)
            o_fly_spray = drone.fly_to(x=x_a1, y=y_a1).oracle().depends_on(o_takeoff_spray, delay_seconds=1)
            o_spray = drone.apply_pesticide(area='A1', amount_ml=800.0).oracle().depends_on(
                o_fly_spray, delay_seconds=2)

            # Final return
            o_final_return = drone.drone_return_to_base().oracle().depends_on(o_spray, delay_seconds=1)
            o_final_land = drone.land().oracle().depends_on(o_final_return, delay_seconds=1)

        self.events = [e0, info_d2, info_a1, o_move_harvest, o_harvest, o_takeoff, o_fly_scout, o_scout,
                      o_return_drone, o_land, o_return_rover, o_refill, o_takeoff_spray, o_fly_spray,
                      o_spray, o_final_return, o_final_land]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate
    run_and_validate(CustomScenario())

