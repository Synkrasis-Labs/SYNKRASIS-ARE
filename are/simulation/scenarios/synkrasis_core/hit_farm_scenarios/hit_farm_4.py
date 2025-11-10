from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, GroundRover, CentralHub, SensorNetwork, Plant
)
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    Scenario 4: Confirm whether the corn in field A1 is in the new budding growth stage.
    If so, apply starter fertilizer 20kg.
    """

    prompt: str | None = (
        "Confirm whether the corn in field A1 is in the new budding growth stage. "
        "If so, apply starter fertilizer 20kg."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        rover = GroundRover(farm_state=state, device_id='rover-1')
        hub = CentralHub(farm_state=state)
        sensors = SensorNetwork(farm_state=state)

        state.register_rover(rover)
        state.register_central_hub(hub)
        state.register_sensor_network(sensors)

        # Setup A1 with corn in new budding (early vegetative) stage
        a1_land = state.lands.get('A1')
        if a1_land:
            a1_land.set_default_species('corn')
            for x in range(min(10, a1_land.width)):
                for y in range(min(10, a1_land.height)):
                    cell = a1_land.grid[x][y]
                    plant = Plant(species='corn', growth_stage='new budding', planting_date=state.time)
                    plant.height_cm = 20.0
                    plant.health = 0.90
                    cell.plant = plant

        self.apps = [agui, state, rover, hub, sensors]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        rover = self.get_typed_app(GroundRover)
        hub = self.get_typed_app(CentralHub)
        sensors = self.get_typed_app(SensorNetwork)

        with EventRegisterer.capture_mode():
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # Get A1 coordinates
            info = state.get_coordinates(land_name="A1").oracle().depends_on(e0, delay_seconds=1)
            (x, y) = state.lands["A1"].origin

            # Check plant growth stage
            o_check = sensors.get_plant_status(x=x, y=y).oracle().depends_on(info, delay_seconds=1)

            # If in early growth stage (V2, V3 = new budding), apply starter fertilizer
            # Load fertilizer
            o_load = hub.refill_fertilizer(device_id=rover.state.device_id, amount_kg=20.0).oracle().depends_on(
                o_check, delay_seconds=1)

            # Move to A1
            o_move = rover.move_to(x=x, y=y).oracle().depends_on([info, o_load], delay_seconds=1)

            # Apply starter fertilizer (20kg)
            o_apply = rover.apply_fertilizer(kg=20.0).oracle().depends_on(o_move, delay_seconds=1)

            # Return to base
            o_return = rover.return_to_base().oracle().depends_on(o_apply, delay_seconds=1)

        self.events = [e0, info, o_check, o_load, o_move, o_apply, o_return]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
