from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    Drone, CentralHub, SensorNetwork, HitFarmState, Plant
)
from are.simulation.types import EventRegisterer
from are.simulation.scenarios.core_scenario import COREScenario


class CustomScenario(COREScenario):
    """
    scenarios30: Check if soybeans in C1 are in R3 flowering growth stage.
    If so, conduct drone inspection. If diseases detected, immediately initiate protective spraying treatment.
    """

    prompt: str | None = (
        "Check if the soybeans in C1 land are in the R3 flowering growth stage. "
        "If so, conduct a drone inspection using multispectral imaging. "
        "If any diseases are detected, immediately initiate protective spraying treatment 300ml."
        "After completing spray pesticides, return to central hub."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        drone = Drone(farm_state=state)
        hub = CentralHub(farm_state=state)
        sensor = SensorNetwork(farm_state=state)

        state.register_drone(drone)
        state.register_central_hub(hub)

        # Setup C1 with soybean plants in R3 growth stage with diseases
        c1_land = state.lands.get('C1')
        if c1_land:
            for x in range(min(5, c1_land.width)):
                for y in range(min(5, c1_land.height)):
                    cell = c1_land.grid[x][y]
                    plant = Plant(species='soybean', growth_stage='R3')
                    # Add diseases for testing
                    cell.diseases = {'rust': 0.5, 'powdery_mildew': 0.4}
                    cell.plant = plant

        self.apps = [agui, state, drone, hub, sensor]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        drone = self.get_typed_app(Drone)
        hub = self.get_typed_app(CentralHub)
        sensor = self.get_typed_app(SensorNetwork)

        with EventRegisterer.capture_mode():
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)
            # Get coordinates for A1
            info = state.get_coordinates(land_name="A1").oracle().depends_on(e0, delay_seconds=1)
            # Get C1 coordinates
            (x, y) = state.lands["C1"].origin
            # Check plant status in C1
            e1 = sensor.get_plant_status(x, y).oracle().depends_on(info, delay_seconds=1)

            # Drone inspection
            e2 = drone.takeoff().oracle().depends_on(e1, delay_seconds=1)
            e3 = drone.fly_to(x=x, y=y).oracle().depends_on(e2, delay_seconds=1)
            e4 = drone.detect_disease_hotspots(land_name='C1',
                                               sampling_density='high').oracle().depends_on(e3, delay_seconds=1)

            # Return to base, refill, spray
            e5 = drone.drone_return_to_base().oracle().depends_on(e4, delay_seconds=1)
            e7 = hub.refill_pesticide(device_id=drone.state.device_id, amount_ml=300.0).oracle().depends_on(e5,
                                                                                                            delay_seconds=1)

            # Apply pesticide
            e8 = drone.takeoff().oracle().depends_on(e7, delay_seconds=1)
            e9 = drone.fly_to(x=x, y=y).oracle().depends_on(e8, delay_seconds=1)
            e10 = drone.apply_pesticide(area='C1', amount_ml=300.0).oracle().depends_on(e9, delay_seconds=1)

            # Return to base
            e11 = drone.drone_return_to_base().oracle().depends_on(e10, delay_seconds=1)
            e12 = drone.land().oracle().depends_on(e11, delay_seconds=1)

        self.events = [e0, info, e1, e2, e3, e4, e5, e7, e8, e9, e10, e11, e12]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
