from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, IrrigationSystem, SensorNetwork, WeatherApp
)
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    Scenario 6: Maintain 5 cm of floodwater in B3; receive a frost warning (≤6 h).
    Temporarily raise water layer in B3 to 7 cm (±0.5 cm) to buffer against cold temperatures;
    reassess 6 h later to restore 5 cm of floodwater.
    """

    prompt: str | None = (
        "Maintain 5 cm of floodwater in B3; receive a weather alert frost warning (≤6 h). "
        "Temporarily raise water layer in B3 to 7 cm to buffer against cold temperatures; "
        "reassess 6 h later to restore 5 cm of floodwater."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        irrigation = IrrigationSystem(farm_state=state)
        sensors = SensorNetwork(farm_state=state)
        weather = WeatherApp()

        state.register_irrigation_system(irrigation)
        state.register_sensor_network(sensors)

        # Set B3 current water depth to 5 cm
        b3_land = state.lands.get('B3')
        if b3_land:
            b3_land.water_depth = 5.0

        # Add frost warning (within 6 hours)
        weather.add_weather_alert(
            alert_type="frost",
            severity="high",
            message="Frost warning - expected within 6 hours. Temperature may drop to -2°C.",
            duration_hours=6
        )

        self.apps = [agui, state, irrigation, sensors, weather]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        irrigation = self.get_typed_app(IrrigationSystem)
        sensors = self.get_typed_app(SensorNetwork)
        weather = self.get_typed_app(WeatherApp)

        with EventRegisterer.capture_mode():
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # Check current water depth in B3
            o_depth_before = sensors.get_water_depth(land_name="B3").oracle().depends_on(e0, delay_seconds=1)

            # Check weather alerts for frost warning
            o_alerts = weather.get_weather_alerts().oracle().depends_on(e0, delay_seconds=1)

            # Raise water level to 7 cm (to buffer against frost)
            o_raise_water = irrigation.open_valve(land_name="B3", water_depth_cm=7.0).oracle().depends_on(
                o_alerts, delay_seconds=1)

            # Close valve after reaching target depth
            o_close_1 = irrigation.close_valve(land_name="B3").oracle().depends_on(o_raise_water, delay_seconds=1)

            # Verify water depth raised to 7 cm
            o_verify_raised = sensors.get_water_depth(land_name="B3").oracle().depends_on(o_close_1, delay_seconds=1)

            # Wait 6 hours (21600 seconds) for frost period to pass
            o_schedule = state.schedule_in(time="6 hours").oracle().depends_on(o_verify_raised, delay_seconds=21600)

            # Restore water depth to 5 cm after frost period
            o_restore_water = irrigation.open_valve(land_name="B3", water_depth_cm=5.0).oracle().depends_on(
                o_schedule, delay_seconds=1)

            # Close valve
            o_close_2 = irrigation.close_valve(land_name="B3").oracle().depends_on(o_restore_water, delay_seconds=1)

            # Verify water depth restored to 5 cm
            o_verify_restored = sensors.get_water_depth(land_name="B3").oracle().depends_on(o_close_2, delay_seconds=1)

        self.events = [e0, o_depth_before, o_alerts, o_raise_water, o_close_1, o_verify_raised,
                       o_schedule, o_restore_water, o_close_2, o_verify_restored]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
