# @TODO: Update copyright for SYNKRASIS-LABS
#
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import random
from dataclasses import dataclass

from are.simulation.apps.core_app import COREApp
from are.simulation.tool_utils import OperationType, app_tool, data_tool
from are.simulation.types import event_registered
from are.simulation.utils import type_check


@dataclass
class WritingState:
    """
    State of the writing system.
    """

    sentence: str
    word_pools: dict[str, list[str]]


initState = WritingState(
    sentence="",
    word_pools={
        "nouns": ["dog", "cat", "car", "house", "tree", "bird"],
        "verbs": ["runs", "jumps", "drives", "flies", "sleeps"],
        "adjectives": ["fast", "blue", "big", "small", "happy"],
        "articles": ["a", "the"],
        "prepositions": ["on", "under", "beside", "near", "above"],
    },
)


class WritingApp(COREApp[WritingState]):
    """
    @TODO: Update docstring

    A custom writing app demonstrating core app implementation patterns.

    Key Features Demonstrated:
    - Data storage and management
    - Tool method registration with decorators
    - State persistence and loading
    - Type checking and validation
    - Event registration for environment integration

    This app manages a collection of tasks with basic CRUD operations.
    """

    init_state: WritingState = initState

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_article(self, article: str) -> str:
        """
        Adds an article (e.g., 'a', 'the') to the sentence.

        :param article: The article to add (if None, selects randomly).
        :returns: Confirmation message.
        """
        if article:
            word = article
        else:
            word = random.choice(self.state.word_pools["articles"])
        self.state.sentence += word + " "
        return f"Added article: '{word}'"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_noun(self, noun: str) -> str:
        """
        Adds a noun to the sentence.

        :param noun: The noun to add (if None, selects randomly).
        :returns: Confirmation message.
        """
        if noun:
            word = noun
        else:
            word = random.choice(self.state.word_pools["nouns"])
        self.state.sentence += word + " "
        return f"Added noun: '{word}'"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_verb(self, verb: str) -> str:
        """
        Adds a verb to the sentence.

        :param verb: The verb to add (if None, selects randomly).
        :returns: Confirmation message.
        """
        if verb:
            word = verb
        else:
            word = random.choice(self.state.word_pools["verbs"])
        self.state.sentence += word + " "
        return f"Added verb: '{verb}'"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_adjective(self, adjective: str) -> str:
        """
        Adds an adjective to the sentence.

        :param adjective: The adjective to add (if None, selects randomly).
        :returns: Confirmation message.
        """
        if adjective:
            word = adjective
        else:
            word = random.choice(self.state.word_pools["adjectives"])
        self.state.sentence += word + " "
        return f"Added adjective: '{word}'"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_preposition(self, preposition: str) -> str:
        """
        Adds a preposition to the sentence.

        :param preposition: The preposition to add (if None, selects randomly).
        :returns: Confirmation message.
        """
        if preposition:
            word = preposition
        else:
            word = random.choice(self.state.word_pools["prepositions"])
        self.state.sentence += word + " "
        return f"Added preposition: '{word}'"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def complete_sentence(self) -> str:
        """
        Completes the sentence and returns it.

        :returns: The final sentence.
        """
        sentence = self.state.sentence.strip() + "."
        self.state.sentence = ""  # Reset for next sentence
        return f"Completed sentence: '{sentence}'"
