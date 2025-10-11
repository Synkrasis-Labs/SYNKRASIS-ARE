import sys

from are.simulation.scenarios.scenario import Scenario
from are.simulation.scenarios.utils.registry import register_scenario
from are.simulation.scenarios.validation_result import ScenarioValidationResult


class COREScenario(Scenario):
    prompt: str | None = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ensure prompt is set
        if self.prompt is None:
            raise ValueError("Scenario prompt must be set.")

        filename = sys.modules[self.__class__.__module__].__file__
        if not filename:
            raise Exception(
                "Could not determine module file for scenario registration."
            )

        register_scenario(filename)(self.__class__)

    def validate(self, env) -> ScenarioValidationResult:
        """
        Validate that the scenario completed successfully.

        Check that the agent properly interacted with our custom app.
        """
        return ScenarioValidationResult(
            success=False,
            exception=Exception("Validation not implemented yet"),
        )
