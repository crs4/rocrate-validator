# Copyright (c) 2024-2025 CRS4
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import enum
from abc import ABC, abstractmethod
from functools import total_ordering
from typing import Optional, Union

import enum_tools

import rocrate_validator.log as logging

# Set up logging
logger = logging.getLogger(__name__)


@enum.unique
@enum_tools.documentation.document_enum
@total_ordering
class EventType(enum.Enum):
    """ Event types """

    #: Validation start
    VALIDATION_START = 0
    #: Validation end
    VALIDATION_END = 1
    #: Profile validation start
    PROFILE_VALIDATION_START = 2
    #: Profile validation end
    PROFILE_VALIDATION_END = 3
    #: Requirement validation start
    REQUIREMENT_VALIDATION_START = 4
    #: Requirement validation end
    REQUIREMENT_VALIDATION_END = 5
    #: Requirement check validation start
    REQUIREMENT_CHECK_VALIDATION_START = 6
    #: Requirement check validation end
    REQUIREMENT_CHECK_VALIDATION_END = 7

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented


class Event:
    """
    Base class for representing events
    """

    def __init__(self, event_type: EventType, message: Optional[str] = None):
        """
        Initialize the event.

        :param event_type: the event type
        :type event_type: EventType

        :param message: the message
        :type message: Optional[str]
        """
        self.event_type = event_type
        self.message = message

    def __str__(self):
        """
        String representation of the event.

        :return: the string representation
        :rtype: str
        """
        return f"{self.event_type.name}: {self.message}" if self.message else self.event_type.name

    def __repr__(self):
        """
        String representation of the event.

        :return: the string representation
        :rtype: str
        """
        return f"{self.event_type.name}: {self.message}" if self.message else self.event_type.name

    def __eq__(self, other):
        """
        Compare two events.

        :param other: the other event
        :type other: Event

        :return: True if the events are equal, False otherwise
        :rtype: bool
        """
        if self.__class__ is other.__class__:
            return self.event_type == other.event_type and self.message == other.message
        return NotImplemented

    def __hash__(self):
        """
        Hash the event.

        :return: the hash
        :rtype: int
        """
        return hash((self.event_type, self.message))

    def __ne__(self, other):
        """
        Compare two events.
        :param other: the other event
        :type other: Event
        :return: True if the events are not equal, False otherwise
        :rtype: bool
        """
        if self.__class__ is other.__class__:
            return not self.__eq__(other)
        return NotImplemented


class Subscriber(ABC):

    """
    Subscriber interface.
    Objects that want to be notified of events generated during the validation process
    should implement this interface.
    """

    def __init__(self, name):
        self.name = name

    @abstractmethod
    def update(self, event: Event):
        """
        Update the subscriber with the event

        :param event: the event
        :type event: Event
        """
        pass


class Publisher:
    def __init__(self, avoid_duplicate_notifications: bool = False):
        self.__subscribers = set()
        self.__notified_events = set()
        self.__avoid_duplicate_notifications = avoid_duplicate_notifications

    @property
    def subscribers(self):
        return self.__subscribers

    def add_subscriber(self, subscriber):
        self.subscribers.add(subscriber)

    def remove_subscriber(self, subscriber):
        self.subscribers.remove(subscriber)

    def notify(self, event: Union[Event, EventType]):
        if isinstance(event, EventType):
            event = Event(event)
        # Check if the event has already been notified
        # This is to avoid notifying the same event multiple times
        if self.__avoid_duplicate_notifications:
            if event in self.__notified_events:
                logger.warning(f"Event {event} already notified")
                return
        # Add the event to the notified events
        self.__notified_events.add(event)
        logger.debug(f"Notifying event {event}")
        # Notify all subscribers
        for subscriber in self.subscribers:
            subscriber.update(event)
