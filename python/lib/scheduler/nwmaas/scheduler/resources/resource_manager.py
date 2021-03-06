#!/usr/bin/env python3
from typing import Iterable, Mapping, Union
from abc import ABC, abstractmethod
import logging

# As a pure ABC probably don't need logging
logging.basicConfig(
    filename='ResourceManager.log',
    level=logging.DEBUG,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S")


class ResourceManager(ABC):
    """
        Abstract class for defining the API for Resource Managing
    """

    @abstractmethod
    def set_resources(self, resources: Iterable[Mapping[str, Union[str, int]]]):
        """
            Set the provided resources into the manager's resource tracker.

            Parameters
            ----------
            resources
                An iterable of maps defining each resource to set.
                One map per resource with the following metadata.
                 { 'node_id': "Node-0001",
                   'Hostname': "my-host",
                   'Availability': "active",
                   'State': "ready",
                   'CPUs': 18,
                   'MemoryBytes': 33548128256
                  }

            Returns
            -------
            None


        """
        pass

    @abstractmethod
    def get_resources(self) -> Union[Iterable[str], Iterable[Mapping[str, Union[str, int]]]]:
        """
            Get metadata of all managed resoures.

            Returns
            -------
            resources
                An iterable of maps defining each managed resource.
                One map per resource with the following metadata.
                 { 'node_id': "Node-0001",
                   'Hostname': "my-host",
                   'Availability': "active",
                   'State': "ready",
                   'CPUs': 18,
                   'MemoryBytes': 33548128256
                  }

        """
        pass

    @abstractmethod
    def get_resource_ids(self) -> Iterable[Union[str, int]]:
        """
            Get the identifiers for all managed resources

            Returns
            -------
            list of resource id's

        """
        pass

    @abstractmethod
    def allocate_resource(self, resource_id: str, requested_cpus: int,
                          requested_memory: int = 0, partial: bool = False) -> Mapping[str, Union[str, int]]:
        """
        Attempt to allocate the requested resources.  Successful allocation will return
        a non empty map.

        Parameters
        ----------
        resource_id
            Unique ID string of the resource referenceable by the manager

        requested_cpus
            integer numbre of cpus to attempt to allocate

        requested_memory
            integer number of bytes to allocate.  currently optional

        partial
            whether to partially fulfill the requested allocation and return
            an allocation map with less than the requested allocation


        """
        pass

    @abstractmethod
    def release_resources(self, allocated_resources: Iterable[Mapping[str, Union[str, int]]]):
        """
            Give back any allocated resources to the manager.

            Parameters
            ----------
            allocated_resources
                An iterable of maps containing the metadata returned by allocate_resources
        """
        pass

    @abstractmethod
    def get_available_cpu_count(self) -> int:
        """
            Returns a count of all available CPU's summed across all resources
            at the time of calling.  Not guaranteed avaialable until allocated.

            Returns
            -------
            total available CPUs
        """
        pass
