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
    def __init__(self):
        self.__subscribers = set()

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
        for subscriber in self.subscribers:
            subscriber.update(event)
