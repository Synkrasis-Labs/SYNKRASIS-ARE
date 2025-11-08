from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import HitFarmState
from are.simulation.apps.synkrasis_core.hit_farm import Drone, GroundRover, CentralHub, IrrigationSystem, SensorNetwork, WeatherApp
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.scenarios.utils.registry import register_scenario
from are.simulation.types import EventRegisterer

class CustomScenario(COREScenario):
    """
    scenarios19: Irrigation vs. rain forecast conflict (corn field MAD=52%).
    """

    prompt: str | None = (
        "Plot A1, MAD = 52%, requires irrigation; "
        "if the probability of rainfall in the next 60 minutes is ≥70%; Do not start  the irrigation task. "
        "Re-evaluate after 2 hours. If there is still no rainfall after 2 hours and MAD>50%, begin irrigate until MAD<30% stop irrigation task."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        weather = WeatherApp()
        weather.generate_forecast(hours=1, forecast_entry={"time": 0, "precipitation_probability": 70})
        state = HitFarmState()
        irrigation = IrrigationSystem(farm_state = state)
        sensors = SensorNetwork(farm_state = state)
        self.apps = [agui, state, weather, irrigation, sensors]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        weather = self.get_typed_app(WeatherApp)
        irrigation = self.get_typed_app(IrrigationSystem)
        sensor = self.get_typed_app(SensorNetwork)
        with EventRegisterer.capture_mode():
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            weather_forecast = weather.get_forecast(hours=1).oracle().depends_on(e0, delay_seconds=1)
            weather_current = weather.get_current_weather().oracle().depends_on(weather_forecast, delay_seconds=2*60*60)
            sensor_mad = sensor.get_land_MDA(land_name="A1").oracle().depends_on(weather_current, delay_seconds=1)
            e_open = irrigation.open_valve(land_name="A1").oracle().depends_on(sensor_mad, delay_seconds=1)
            sensor_mad_2 = sensor.get_land_MDA(land_name="A1").oracle().depends_on(weather_current, delay_seconds=1)
            e_close = irrigation.close_valve(land_name="A1").oracle().depends_on(e_open, delay_seconds=1)

            self.events = [e0, weather_forecast, weather_current, sensor_mad, e_open,sensor_mad_2, e_close]




if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate
    run_and_validate(CustomScenario())


