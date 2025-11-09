from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, Drone, CentralHub
)
from are.simulation.types import EventRegisterer
from are.simulation.scenarios.core_scenario import COREScenario


class CustomScenario(COREScenario):
    """
    scenarios25: Drone grid patrol to assess brown planthopper activity in B3
    - Conduct drone grid patrols in land B3
    - Assess brown planthopper activity levels
    """

    prompt: str | None = (
        "In Land B3, conduct drone grid patrols to assess brown_planthopper activity."
        "After completing patrol, return to central hub."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        state.lands["B3"].grid[0][0].pests['brown_planthopper'] = 0.6
        drone = Drone(farm_state=state)
        state.register_drone(drone)

        self.apps = [agui, state, drone]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        drone = self.get_typed_app(Drone)

        with EventRegisterer.capture_mode():
            # Single user message to trigger the entire workflow
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # Get coordinates for B3
            info = state.get_coordinates(land_name="B3").oracle().depends_on(e0, delay_seconds=1)
            (x, y) = state.lands["B3"].origin

            # Drone takeoff
            o_takeoff = drone.takeoff().oracle().depends_on(e0, delay_seconds=1)

            # Fly to B3
            o_fly = drone.fly_to(x=x, y=y).oracle().depends_on([info, o_takeoff], delay_seconds=2)

            # Assess brown planthopper activity with medium density grid patrol
            o_assess = drone.assess_pest_activity(
                land_name="B3",
                pest_type="brown_planthopper",
                sampling_density='medium'
            ).oracle().depends_on(o_fly, delay_seconds=1)

            # Return to base and land
            o_return = drone.drone_return_to_base().oracle().depends_on(o_assess, delay_seconds=2)
            o_land = drone.land().oracle().depends_on(o_return, delay_seconds=1)

        self.events = [e0, info, o_takeoff, o_fly, o_assess, o_return, o_land]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
