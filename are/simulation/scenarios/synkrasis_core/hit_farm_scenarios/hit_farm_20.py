from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, GroundRover, CentralHub, SensorNetwork, Plant
)
from are.simulation.types import EventRegisterer
from are.simulation.scenarios.core_scenario import COREScenario


class CustomScenario(COREScenario):
    """
    scenarios20: Multi-land fertilization based on growth stage
    - Land A1: Check if corn is in V12 stage, if so apply 30kg fertilizer
    - Land D2: Check if wheat is in heading stage, if so apply 50kg fertilizer
    - Land C1: Check if soybean is in R2 stage, if so apply 40kg fertilizer
    """

    prompt: str | None = ("execute following tasks in sequence: "
                          "Land A1: Check if the corn is in the V12 growth stage, if so, apply 30kg of fertilizer. "
                          "Land D2: Check if the wheat is in the heading growth stage, if so, apply 50kg of fertilizer. "
                          "Land C1: Check if the soybean is in the R2 growth stage, if so, apply 40kg of fertilizer."
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

        # Plant corn in A1 at V12 stage
        land_a1 = state.lands["A1"]
        for x in range(10):
            for y in range(10):
                land_a1.grid[x][y].plant = Plant(species="corn", growth_stage="V12", planting_date=state.time)

        # Plant wheat in D2 at heading stage
        land_d2 = state.lands["D2"]
        for x in range(10):
            for y in range(10):
                land_d2.grid[x][y].plant = Plant(species="wheat", growth_stage="heading", planting_date=state.time)

        # Plant soybean in C1 at R2 stage
        land_c1 = state.lands["C1"]
        for x in range(10):
            for y in range(10):
                land_c1.grid[x][y].plant = Plant(species="soybean", growth_stage="R2", planting_date=state.time)

        self.apps = [agui, state, rover, hub, sensors]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        rover = self.get_typed_app(GroundRover)
        hub = self.get_typed_app(CentralHub)
        sensors = self.get_typed_app(SensorNetwork)

        with EventRegisterer.capture_mode():
            # Single user message to trigger the entire workflow
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # --- Land A1: Corn V12 stage - 30kg fertilizer ---
            info_a1 = state.get_coordinates(land_name="A1").oracle().depends_on(e0, delay_seconds=1)
            (x_a1, y_a1) = state.lands["A1"].origin

            o_check_a1 = sensors.get_plant_status(x=x_a1, y=y_a1).oracle().depends_on(info_a1, delay_seconds=1)
            o_refill_a1 = hub.refill_fertilizer(device_id=rover.state.device_id, amount_kg=30.0).oracle().depends_on(
                o_check_a1, delay_seconds=1)
            o_move_a1 = rover.move_to(x=x_a1, y=y_a1).oracle().depends_on([info_a1, o_refill_a1], delay_seconds=1)
            o_apply_a1 = rover.apply_fertilizer(kg=30.0).oracle().depends_on(o_move_a1, delay_seconds=1)

            # --- Land D2: Wheat heading stage - 50kg fertilizer ---
            info_d2 = state.get_coordinates(land_name="D2").oracle().depends_on(e0, delay_seconds=1)
            (x_d2, y_d2) = state.lands["D2"].origin

            o_return_1 = rover.return_to_base().oracle().depends_on(o_apply_a1, delay_seconds=1)
            o_check_d2 = sensors.get_plant_status(x=x_d2, y=y_d2).oracle().depends_on(info_d2, delay_seconds=1)
            o_refill_d2 = hub.refill_fertilizer(device_id=rover.state.device_id, amount_kg=50.0).oracle().depends_on(
                [o_return_1, o_check_d2], delay_seconds=1)
            o_move_d2 = rover.move_to(x=x_d2, y=y_d2).oracle().depends_on([info_d2, o_refill_d2], delay_seconds=1)
            o_apply_d2 = rover.apply_fertilizer(kg=50.0).oracle().depends_on(o_move_d2, delay_seconds=1)

            # --- Land C1: Soybean R2 stage - 40kg fertilizer ---
            info_c1 = state.get_coordinates(land_name="C1").oracle().depends_on(e0, delay_seconds=1)
            (x_c1, y_c1) = state.lands["C1"].origin

            o_return_2 = rover.return_to_base().oracle().depends_on(o_apply_d2, delay_seconds=1)
            o_check_c1 = sensors.get_plant_status(x=x_c1, y=y_c1).oracle().depends_on(info_c1, delay_seconds=1)
            o_refill_c1 = hub.refill_fertilizer(device_id=rover.state.device_id, amount_kg=40.0).oracle().depends_on(
                [o_return_2, o_check_c1], delay_seconds=1)
            o_move_c1 = rover.move_to(x=x_c1, y=y_c1).oracle().depends_on([info_c1, o_refill_c1], delay_seconds=1)
            o_apply_c1 = rover.apply_fertilizer(kg=40.0).oracle().depends_on(o_move_c1, delay_seconds=1)

            # Return to base
            o_return_final = rover.return_to_base().oracle().depends_on(o_apply_c1, delay_seconds=1)

        self.events = [e0,
                       info_a1, o_check_a1, o_refill_a1, o_move_a1, o_apply_a1,
                       info_d2, o_return_1, o_check_d2, o_refill_d2, o_move_d2, o_apply_d2,
                       info_c1, o_return_2, o_check_c1, o_refill_c1, o_move_c1, o_apply_c1,
                       o_return_final]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
