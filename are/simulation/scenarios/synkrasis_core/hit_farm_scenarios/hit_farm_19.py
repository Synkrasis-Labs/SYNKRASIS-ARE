from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import HitFarmState
from are.simulation.apps.synkrasis_core.hit_farm import IrrigationSystem, SensorNetwork, WeatherApp
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer

class CustomScenario(COREScenario):
    """
    scenarios19: Irrigation vs. rain forecast conflict (corn field MAD=52%).
    """

    prompt: str | None = (
        "Plot A1, MAD = 52%, requires irrigation; "
        "if the probability of rainfall in the next 1 hour is ≥70%; Do not start  the irrigation task. "
        "Re-evaluate  weather after 2 hours. If there is still no rainfall  and MAD>50%, begin irrigate until MAD<=30% stop irrigation task."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        weather = WeatherApp()
        weather.generate_forecast(forecast_entry=[{"time": 0, "precipitation_probability": 70},
                                                  {"time": 0, "precipitation_probability": 70},
                                                  {"time": 0, "precipitation_probability": 70}])
        state = HitFarmState()
        irrigation = IrrigationSystem(farm_state = state)
        sensors = SensorNetwork(farm_state = state)
        self.apps = [agui, state, weather, irrigation, sensors]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        weather = self.get_typed_app(WeatherApp)
        irrigation = self.get_typed_app(IrrigationSystem)
        sensor = self.get_typed_app(SensorNetwork)
        with EventRegisterer.capture_mode():
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            weather_forecast = weather.get_forecast(hours=1).oracle().depends_on(e0, delay_seconds=1)

            schedule = state.schedule_in("2 hours").oracle().depends_on(weather_forecast, delay_seconds=1)
            weather_current = weather.get_current_weather().oracle().depends_on(schedule, delay_seconds=2)
            sensor_mad = sensor.get_land_MAD(land_name="A1").oracle().depends_on(weather_current, delay_seconds=1)
            e_open = irrigation.open_valve(land_name="A1",MAD=0.3).oracle().depends_on(sensor_mad, delay_seconds=1)
            sensor_mad_2 = sensor.get_land_MAD(land_name="A1").oracle().depends_on(weather_current, delay_seconds=1)
            e_close = irrigation.close_valve(land_name="A1").oracle().depends_on(e_open, delay_seconds=1)

        self.events = [e0, weather_forecast,schedule, weather_current, sensor_mad, e_open,sensor_mad_2, e_close]




if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate
    run_and_validate(CustomScenario())


