from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, GroundRover, CentralHub, WeatherApp, Plant, Drone
)
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.scenarios.utils.registry import register_scenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    scenarios49: Check if hail has occurred. After hail, in plot D1,
   Replant to fill gaps where stand loss >15% to stabilize the population.
    """

    prompt: str | None = (
        "Check weather alerts to see if hail has occurred. if hail has occurred, in plot D1, use Drone sampling to estimate wheat density"
        "re-seed  where density per m2 <5.0  to stabilize the population."
        "return to the base after all is completed."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        rover = GroundRover(farm_state=state, device_id='rover-1')
        hub = CentralHub(farm_state=state)
        weather = WeatherApp()
        drone = Drone(farm_state=state)

        state.register_rover(rover)
        state.register_central_hub(hub)
        state.register_drone(drone)

        # Add hail weather alert
        weather.add_weather_alert(
            alert_type="hail",
            severity="high",
            message="Severe hail event occurred. Crop damage expected.",
            duration_hours=6
        )

        d1_land = state.lands.get('D1')
        d1_land.density_per_m2 = 4.0

        self.apps = [agui, state, rover, hub, weather, drone]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        rover = self.get_typed_app(GroundRover)
        hub = self.get_typed_app(CentralHub)
        weather = self.get_typed_app(WeatherApp)
        drone = self.get_typed_app(Drone)

        with EventRegisterer.capture_mode():
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)
            # Get D1 coordinates
            info = state.get_coordinates(land_name="D1").oracle().depends_on(e0, delay_seconds=1)
            (x, y) = state.lands["D1"].origin
            # Check for hail event
            o_check_hail = weather.get_weather_alerts().oracle().depends_on(e0, delay_seconds=1)
            # Drone estimates corn density
            o_takeoff = drone.takeoff().oracle().depends_on(o_check_hail, delay_seconds=1)
            o_fly = drone.fly_to(x=x, y=y).oracle().depends_on(o_takeoff, delay_seconds=1)
            o_estimate = drone.estimate_plant_density(crop_species='corn', land_name='D1',
                                                      sampling_density='medium').oracle().depends_on(
                o_fly, delay_seconds=2)

            # Return drone to base
            o_return_drone = drone.drone_return_to_base().oracle().depends_on(o_estimate, delay_seconds=1)
            o_land = drone.land().oracle().depends_on(o_return_drone, delay_seconds=1)
            # Get D1 coordinates

            # Load wheat seeds for replanting
            o_load = hub.refill_seeds(device_id=rover.state.device_id, seed_type="wheat",
                                      count=500).oracle().depends_on(
                o_estimate, delay_seconds=1)

            # Move to D1
            o_move = rover.move_to(x=x, y=y).oracle().depends_on(o_load, delay_seconds=1)

            # Replant strips to restore stand (target density 5.0 plants/m²)
            o_replant = rover.plant_seed(land_name='D1', seed_type='wheat').oracle().depends_on(
                o_move, delay_seconds=3)

            # Return to base
            o_return = rover.return_to_base().oracle().depends_on(o_replant, delay_seconds=1)

        self.events = [e0, o_check_hail, info, o_load, o_move, o_replant, o_return,
                       o_takeoff, o_fly, o_estimate, o_return_drone, o_land]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
