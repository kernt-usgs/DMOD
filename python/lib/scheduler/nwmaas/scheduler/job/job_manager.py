from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from uuid import uuid4 as random_uuid
from .job import Job, RequestedJob
from ..resources.resource_allocation import ResourceAllocation
from ..rsa_key_pair import RsaKeyPair

from nwmaas.communication import MaaSRequest, NWMRequest, SchedulerRequestMessage
from nwmaas.redis import KeyNameHelper, RedisBacked


class JobManagerFactory:
    """
    A basic concrete implementation of a factory for obtaining ::class:`JobManager` instances.

    The intent is for this to be exposed, along with interface class, but have implementations of ::class:`JobManager`
    be essentially obscured.  To support externally created implementations, this factory class can itself be extended.

    This default implementation is only aware of one particular concrete type that uses a Redis backend, so it will
    always return an instance of that type.  The supported keyword args are documented in the method.
    """

    @classmethod
    def factory_create(cls, **kwargs):
        """
        Create and return a new instance of a ::class:`JobManager` object.

        In this default method implementation, only a single, Redis-backed type is available.  The method supports
        receiving keyword args to provide non-default values for the host, port, and password parameters for the Redis
        server connection.

        Keyword Args
        ----------
        host : str
            The Redis service host name.
        port : int
            The Redis service port.
        password : str
            The Redis service auth password.

        Returns
        -------
        JobManager
            A newly created ::class:`JobManager` object.
        """
        host = None
        port = None
        pword = None
        for key, value in kwargs.items():
            if key == 'host':
                host = value
            elif key == 'port':
                port = int(value)
            elif key == 'password':
                pword = value
        return RedisBackedJobManager(redis_host=host, redis_port=port, redis_pass=pword)


class JobManager(ABC):

    @abstractmethod
    def create_job(self, **kwargs) -> Job:
        """
        Create and return a new job object.

        Implementations will vary, but they should all directly or indirectly (i.e., nested as attributes of some other
        object) provide the following parameters within keyword args.

            ``cpu_count`` - A count of CPUs for the job (``int``).
            ``memory_size`` - A size of memory needed for the job (``int``).
            ``parameters`` - A dictionary of job config parameters (``dict``).

        Parameters
        ----------
        kwargs
            Other appropriate, implementation-specific keyed parameters supported for creating the job object.

        Returns
        -------
        Job
            The newly created job object.
        """
        pass

    @abstractmethod
    def delete_job(self, job_id) -> bool:
        """
        Delete the job record for the job with the given id value.

        Parameters
        ----------
        job_id
            The unique id for a job of interest to delete.

        Returns
        -------
        bool
            ``True`` if a record was successfully deleted, otherwise ``False``.
        """
        pass

    @abstractmethod
    def does_job_exist(self, job_id) -> bool:
        """
        Test whether a job with the given job id exists.

        Parameters
        ----------
        job_id
            The job id of interest.

        Returns
        -------
        bool
            ``True`` if a job exists with the provided job id, or ``False`` otherwise.
        """
        pass

    @abstractmethod
    def retrieve_job(self, job_id) -> Job:
        """
        Get the particular job with the given unique id.

        Method will raise a ::class:`ValueError` if called using a job id that does not correspond to an existing job.
        Users of the method should either catch this error or test job ids for existence first with the
        ::method:`does_job_exist` method.

        Parameters
        ----------
        job_id
            The unique id of the desired job.

        Returns
        -------
        Job
            The particular job with the given unique id.

        Raises
        -------
        ValueError
            If no job exists with given job id.
        """
        pass

    @abstractmethod
    def save_job(self, job: Job):
        """
        Add or update the given job object in this manager's backend data store of job record data.

        Parameters
        ----------
        job
            The job to be updated or added.
        """
        pass


# TODO: properly account upstream for allocations for finished jobs (or any jobs being deleted) getting cleaned up,
#   since this type isn't responsible for that.
class RedisBackedJobManager(JobManager, RedisBacked):
    """
    An implementation of ::class:`JobManager` that uses Redis as a backend and works with ::class:`RequestedJob` job
    objects.
    """

    # TODO: look at either deprecating this or applying it appropriately to all managed objects
    @classmethod
    def get_key_prefix(cls):
        return 'job_mgr'

    def __init__(self, redis_host: Optional[str] = None, redis_port: Optional[int] = None,
                 redis_pass: Optional[str] = None, **kwargs):
        super(RedisBacked).__init__(redis_host=redis_host, redis_port=redis_port, redis_pass=redis_pass, **kwargs)

    def _deserialize_allocations(self, allocations_key_list: List[str],
                                 allocation_hashes: Dict[str, dict]) -> List[ResourceAllocation]:
        allocation_hashes_list = list()
        for key in allocations_key_list:
            allocation_hashes_list.append(allocation_hashes[key])
        allocations = list()
        for alloc_hash in allocation_hashes_list:
            allocations.append(ResourceAllocation.factory_init_from_dict(alloc_hash))
        return allocations

    def _deserialize_job(self, job_hash: dict, allocations_key_list: Optional[List[str]],
                         allocations_hashes: Optional[dict], originating_request_hash: dict, model_request_hash: dict,
                         parameters_hash: dict) -> RequestedJob:
        """
        Deserialized the serialized data for a requested job, in the form of Redis hashes/mappings, into a
        ::class:`RequestedJob` object.

        Essentially, this performs the reverse of ::method:`serialize_job`.

        Parameters
        ----------
        job_hash : dict
            The top-level hash value for the job to deserialize, containing simple members and reference keys to
            serialized records of the job's nested objects.

        allocations_key_list : Optional[List[str]]
            An optional list of the string keys for the resource allocation objects for this job.

        allocations_hashes : Optional[dict]
            An optional dictionary of serialized allocation hash value for the job's resource allocations.

        originating_request_hash : dict
            The Redis hash value for the scheduler request to deserialize, containing simple members and the
            reference keys to serialized records of the request's nested objects.

        model_request_hash : dict
            The Redis hash value for the inner ::class:`MaaSRequest` object of the scheduler request.

        parameters_hash : dict
            The ``parameters`` of the inner ::class:`MaaSRequest` object of the request.

        Returns
        -------
        RequestedJob
            The deserialize requested job object.
        """
        scheduler_request = self._deserialize_scheduler_request(scheduler_request_hash=originating_request_hash,
                                                                model_request_hash=model_request_hash,
                                                                parameters_hash=parameters_hash)
        job = RequestedJob(scheduler_request)
        if 'allocations_list_key' in job_hash and allocations_hashes is not None:
            job.allocation = self._deserialize_allocations(allocations_key_list, allocations_hashes)
        if 'rsa_key_directory' in job_hash:
            job.rsa_key_pair = RsaKeyPair(directory=job_hash['rsa_key_directory'], name=job_hash['rsa_key_name'])
        return job

    def _deserialize_model_request(self, model_request_hash: dict, parameters_hash: dict, **kwargs) -> MaaSRequest:
        """
        Deserialized the serialized data for a model request, in the form of Redis hashes/mappings, into a
        ::class:`MaaSRequest` object.

        Essentially, this performs the reverse of ::method:`serialize_model_request`.

        The method supports optional keyword arguments.  In particular, these are intended to provide future support for
        controlling the specific subtype of ::class:`MaaSRequest` that is created.  For now, only ::class:`NWMRequest`
        objects are supported.

        Parameters
        ----------
        model_request_hash : dict
            The Redis hash value for the inner ::class:`MaaSRequest` object of the scheduler request.

        parameters_hash : dict
            The ``parameters`` of the inner ::class:`MaaSRequest` object of the request.

        kwargs
            Optional keyword arguments.

        Returns
        -------
        MaaSRequest
            The deserialize model request object.
        """
        # TODO: consider whether there needs to be any conversion done to values (e.g., integer string to actual int)
        parameters = parameters_hash

        return NWMRequest(session_secret=model_request_hash['session_secret'],
                          version=float(model_request_hash['version']),
                          output=model_request_hash['output'],
                          parameters=parameters)

    def _deserialize_scheduler_request(self, scheduler_request_hash: dict, model_request_hash: dict, parameters_hash: dict) -> SchedulerRequestMessage:
        """
        Deserialized the serialized data for a job request, in the form of Redis hashes/mappings, into a
        ::class:`SchedulerRequestMessage` object.

        Essentially, this performs the reverse of ::method:`serialize_scheduler_request`.

        Parameters
        ----------
        scheduler_request_hash : dict
            The top-level Redis hash value for the scheduler request to deserialize, containing simple members and the
            reference keys to serialized records of nested objects

        model_request_hash : dict
            The Redis hash value for the inner ::class:`MaaSRequest` object of the scheduler request.

        parameters_hash : dict
            The ``parameters`` of the inner ::class:`MaaSRequest` object of the request.

        Returns
        -------
        SchedulerRequestMessage
            The deserialize scheduler request object.
        """
        model_request = self._deserialize_model_request(model_request_hash = model_request_hash,
                                                        parameters_hash=parameters_hash,
                                                        model_request_type=scheduler_request_hash['model_request_type'])
        return SchedulerRequestMessage(model_request=model_request,
                                       user_id=scheduler_request_hash['user_id'],
                                       cpus=scheduler_request_hash['cpus'],
                                       mem=scheduler_request_hash['memory'])

    def _dev_setup(self):
        self._clean_keys()
        self.keynamehelper = 'dev' + KeyNameHelper.get_default_separator() + self.get_key_prefix()

    def _does_redis_key_exist(self, redis_key: str) -> bool:
        """
        Test whether a record with the given Redis key exists.

        Works by making an ``EXISTS`` API call for the appropriate key, and seeing if the result of the call is ``1``,
        per the API spec.

        Parameters
        ----------
        redis_key
            The Redis key of interest.

        Returns
        -------
        bool
            ``True`` if a record exists with the provided key, or ``False`` otherwise.
        """
        return self.redis.exists(redis_key) == 1

    def _get_job_key_for_id(self, job_id) -> str:
        """
        Get the appropriate Redis key for accessing the manager's record of the job with the given id.

        Parameters
        ----------
        job_id
            The id of the job of interest.

        Returns
        -------
        str
            The appropriate Redis key for accessing the manager's record of the job with the given id.
        """
        return self.create_key_name('job', str(job_id))

    def _retrieve_serialized_data_for_job(self, job_hash_key) -> Optional[dict]:
        """
        Query for the serialized data structures in Redis that contain the data necessary to re-inflate a job object.

        The returned dictionary will contain the serialized ``job_hash``, ``allocation_hash``,
        ``originating_request_hash``, ``model_request_hash``, and ``parameters_hash`` hashes, all keyed by their
        associated Redis keys.

        This method is convenient in that it returns everything needed to deserialize or clean up a job record in an
        easy-to-use format.

        Parameters
        ----------
        job_hash_key : str
            The key value for the top-level ``job_hash`` serialized record for the job's data.

        Returns
        -------
        dict
            A dictionary of keyed Redis hashes with the serialized data for the related job, or ``None`` if there is no
            top-level job hash record with the provided key (implying the job's data has not been serialized and saved).
        """
        if not self._does_redis_key_exist(job_hash_key):
            return None

        retrieved_mappings = dict()

        job_hash = self.redis.hgetall(job_hash_key)
        retrieved_mappings[job_hash_key] = job_hash

        if 'allocations_list_key' in job_hash:
            allocation_list_key = job_hash['allocations_list_key']
            allocation_list = list(self.redis.lrange(allocation_list_key, 0, -1))
            retrieved_mappings[allocation_list_key] = allocation_list
            for alloc_key in allocation_list:
                retrieved_mappings[alloc_key] = self.redis.hgetall(alloc_key)

        originating_request_key = job_hash['originating_request_key']
        originating_request_hash = self.redis.hgetall(originating_request_key)
        retrieved_mappings[originating_request_key] = originating_request_hash

        model_request_key = originating_request_hash['model_request_key']
        model_request_hash = self.redis.hgetall(model_request_key)
        retrieved_mappings[model_request_key] = model_request_hash

        parameters_key = model_request_hash['parameters_key']
        parameters_hash = self.redis.hgetall(parameters_key)
        retrieved_mappings[parameters_key] = parameters_hash

        return retrieved_mappings

    def _serialize_allocations(self, allocations: List[ResourceAllocation], allocations_list_key: str) -> dict:
        # TODO: should we assume that ResourceAllocations are managed by the ResourceManager (i.e., the Redis-backed one)
        #   and do not need to be saved by this manager.
        # Thus, when serializing
        redis_keyed_hashes = dict()
        allocations_list = list()
        redis_keyed_hashes[allocations_list_key] = allocations_list
        for allocation in allocations:
            allocation.unique_id_separator = self.keynamehelper.separator
            allocations_list.append(allocation.unique_id)
            redis_keyed_hashes[allocation.unique_id] = allocation.to_dict()
        return redis_keyed_hashes

    def _serialize_job(self, job: RequestedJob, job_key: str) -> dict:
        """
        Serialize the given ::class:`RequestedJob` into a collection of Redis-persistable data structures (mostly
        hashes), and return a dictionary of all those structures that should be persisted to save the serialized object
        state in Redis, keyed by the Redis key that should be used for each.

        In particular, for allocations there is a list object that will correspond to a list of allocation hashes in
        Redis for a job record.  Other values of the returned dictionary are themselves dictionaries.

        Note that the method explicitly requires a ``job_key`` parameter, even though this could be derived directly
        from the id of the job object in the current implementation.  This is because it is left to other methods to
        account for the job object having everything it needs to create a unique key identifier, so the key must be
        explicitly provided before calling this method.

        Parameters
        ----------
        job : RequestedJob
            The job to be serialized.

        job_key : str
            The Redis key for the job's serialized record.

        Returns
        -------
        dict
            A mapping of values that correspond to Redis data structures (most, but not all, being hashes), which
            represent serialized state of the requested job, with each value keyed by its Redis key.
        """
        redis_keyed_structures = dict()
        allocations_list_key = self.create_derived_key(job_key, 'allocations_list')
        originating_request_key = self.create_derived_key(job_key, 'originating_request')

        job_hash = dict()
        if job.allocations is not None:
            job_hash['allocations_list_key'] = allocations_list_key
        if job.rsa_key_pair is not None:
            job_hash['rsa_key_directory'] = str(job.rsa_key_pair.directory)
            job_hash['rsa_key_name'] = job.rsa_key_pair.name
        job_hash['originating_request_key'] = originating_request_key

        redis_keyed_structures[job_key] = job_hash

        if job.allocations is not None:
            allocation_mappings = self._serialize_allocations(allocations=job.allocations,
                                                              allocations_list_key=allocations_list_key)
            for key in allocation_mappings:
                redis_keyed_structures[key] = allocation_mappings[key]

        request_mappings = self._serialize_scheduler_request(request=job.originating_request,
                                                             scheduler_request_key=originating_request_key)
        for key in request_mappings:
            redis_keyed_structures[key] = request_mappings[key]

        return redis_keyed_structures

    def _serialize_model_request(self, model_request: MaaSRequest, model_request_key: str):
        """
        Serialize the given ::class:`MaaSRequest` into a collection of Redis-persistable hashes, and return a dictionary
        of all hashes that need to be persisted to save the serialized object state in Redis, keyed by the Redis key
        that should be used for each.

        Parameters
        ----------
        model_request : MaaSRequest
            A model request to be serialized to a number of hashes/dictionaries.

        model_request_key : str
            The key to use for the top-level hash for the model request, and from which keys for related hashes of
            nested objects are derived.

        Returns
        -------
        dict
            A mapping of dictionary values representing hashes that need to be persisted in Redis to save the state of
            the model request, each keyed by its Redis key.
        """
        redis_keyed_hashes = dict()
        model_request_hash = dict()

        model_request_hash['version'] = model_request.version
        model_request_hash['output'] = model_request.output
        model_request_hash['session_secret'] = model_request.session_secret
        # Then a separate params hash, but this can be handled here since the value is already a mapped dict
        params_hash_key = self.create_derived_key(model_request_key, 'parameters')
        model_request_hash['parameters_key'] = params_hash_key

        redis_keyed_hashes[model_request_key] = model_request_hash
        redis_keyed_hashes[params_hash_key] = model_request.parameters

        return redis_keyed_hashes

    def _serialize_scheduler_request(self, request: SchedulerRequestMessage, scheduler_request_key: str) -> dict:
        """
        Serialize the given ::class:`SchedulerRequestMessage` into a collection of Redis-persistable hashes, and return
        a dictionary of all hashes that need to be persisted to save the serialized object state in Redis, keyed by the
        Redis key that should be used for each.

        Parameters
        ----------
        request : SchedulerRequestMessage
            The request message to convert to a serialized format.

        scheduler_request_key : str
            The key that should be used for the top-level Redis Hash for the serialized request, and from which keys for
            related hashes are derived.

        Returns
        -------
        dict
            A mapping of dictionary values representing hashes that need to be persisted in Redis to save the state of
            the scheduler request, each keyed by its Redis key.
        """
        redis_keyed_hashes = dict()

        # Construct the hash for the scheduler request object
        scheduler_request_hash = dict()
        scheduler_request_hash['user_id'] = request.user_id
        scheduler_request_hash['cpus'] = request.cpus
        scheduler_request_hash['memory'] = request.memory
        # Create a derived key for the to-be-created model_request hash, and for reference in the scheduler request hash
        model_request_key = self.create_derived_key(scheduler_request_key, 'model_request')
        scheduler_request_hash['model_request_key'] = model_request_key
        # TODO: might have to consider doing something with types of different names
        scheduler_request_hash['model_request_type'] = request.model_request.__class__.__name__

        # Add the scheduler request hash to the returned container dictionary
        redis_keyed_hashes[scheduler_request_key] = scheduler_request_hash

        # Call method to get hashes for persisting the inner model_request
        # Remember, this is a dictionary of the hashes/mappings to save, not the mapping itself
        model_request_hashes_container = self._serialize_model_request(request.model_request, model_request_key)

        # Transfer the contained keys and hashes to the container dictionary that this method will return
        for key in model_request_hashes_container:
            redis_keyed_hashes[key] = model_request_hashes_container[key]

        return redis_keyed_hashes

    def create_job(self, **kwargs) -> RequestedJob:
        """
        Create and return a new job object that has been saved to the backend store.

        Since this class works with ::class:`RequestedJob` objects, a new object must receive a
        ::class:`SchedulerRequestMessage` as a parameter.  This is in the ``request`` keyword arg.

        Parameters
        ----------
        kwargs
            Implementation-specific keyed parameters for creating appropriate job objects (see *Keyword Args* section).

        Keyword Args
        ------------
        request : SchedulerRequestMessage
            The originating request for the job.

        Returns
        -------
        RequestedJob
            The newly created job object.
        """
        job_obj = RequestedJob(job_request=kwargs['request'])
        #if allocation is not None:
        #    job_obj.allocation = allocation
        #if key_pair is not None:
        #    job_obj.rsa_key_pair = key_pair
        job_obj.job_id = random_uuid()
        self.save_job(job_obj)
        return job_obj

    def delete_job(self, job_id) -> bool:
        """
        Delete the job record for the job with the given id value.

        Note that this deletes all the serialized records for the job in Redis, except for the resource allocations,
        which are handled separately by a resource manager.  This method assumes that gets handled appropriately on its
        own.

        Parameters
        ----------
        job_id
            The unique id for a job of interest to delete.

        Returns
        -------
        bool
            ``True`` if a record was successfully deleted, otherwise ``False``.
        """
        job_hash_key = self._get_job_key_for_id(job_id)
        # Retrieve serialized data from Redis for this, which gives us a dictionary of Redis hashes keyed by Redis keys,
        # most of which (but not all) we will want to delete.
        serialized_data_hashes = self._retrieve_serialized_data_for_job(job_hash_key=job_hash_key)
        # If this is None, there was no job hash key did not exist, so there is nothing to delete
        if serialized_data_hashes is None:
            return False

        # We will need this in a couple places, so go ahead and grab ...
        job_hash = serialized_data_hashes[job_hash_key]

        # TODO: this probably still needs improvement (in particular, making sure changes are managed separately too).
        # The returned 'serialized_data_hashes' includes the keys for the resource allocations.
        # We want to avoid deleting the allocations here (they are managed elsewhere), so separate the other things out.
        managed_data_hash_keys = list()
        allocation_list_key = job_hash['allocations_list_key']
        allocation_list = serialized_data_hashes[allocation_list_key]
        for key in serialized_data_hashes:
            if key not in allocation_list:
                managed_data_hash_keys.append(key)

        # We do need to do something a little extra to get the RsaKeyPair in preparation for cleaning it up
        # Though wait until the other deletions are done
        key_pair = RsaKeyPair(directory=job_hash['rsa_key_directory'], name=job_hash['rsa_key_name'])

        # At this point, we don't really care about the rest of the specific data.
        # We now have a dictionary whose keys are all the Redis keys we need to delete.
        i = 0
        while i < 5:
            i += 1
            with self.redis.pipeline() as pipeline:
                pipeline.watch(*serialized_data_hashes.keys())
                try:
                    pipeline.delete(*managed_data_hash_keys)
                    # If successful, clean up the key pair files and return
                    key_pair.delete_key_files()
                    return True
                except:
                    pass
        # If we get here, it means we failed 5 times, so bail
        return False

    def does_job_exist(self, job_id) -> bool:
        """
        Test whether a job with the given job id exists.

        Parameters
        ----------
        job_id
            The job id of interest.

        Returns
        -------
        bool
            ``True`` if a job exists with the provided job id, or ``False`` otherwise.
        """
        return self._does_redis_key_exist(self._get_job_key_for_id(job_id))

    def retrieve_job(self, job_id) -> RequestedJob:
        """
        Get the particular job with the given unique id.

        Method will raise a ::class:`ValueError` if called using a job id that does not correspond to an existing job.
        Users of the method should either catch this error or test job ids for existence first with the
        ::method:`does_job_exist` method.

        Parameters
        ----------
        job_id
            The unique id of the desired job.

        Returns
        -------
        RequestedJob
            The particular job with the given unique id.

        Raises
        -------
        ValueError
            If no job exists with given job id.
        """
        job_hash_key = self._get_job_key_for_id(job_id)
        # Retrieve serialized data from Redis for this, which gives us a dictionary of Redis hashes keyed by Redis keys
        serialized_data_hashes = self._retrieve_serialized_data_for_job(job_hash_key=job_hash_key)
        # If this is None, there was no job hash key did not exist, so a ValueError needs to be raised
        if serialized_data_hashes is None:
            raise ValueError('No job record found for job with id {} and key {}'.format(job_id, job_hash_key))

        job_hash = serialized_data_hashes[job_hash_key]

        if 'allocations_list_key' in job_hash:
            allocation_list_key = job_hash['allocations_list_key']
            allocation_list = serialized_data_hashes[allocation_list_key]
            allocation_hashes = dict()
            for alloc_hash_key in allocation_list:
                allocation_hashes[alloc_hash_key] = serialized_data_hashes[alloc_hash_key]
        else:
            allocation_list = None
            allocation_hashes = None

        originating_request_key = job_hash['originating_request_key']
        originating_request_hash = serialized_data_hashes[originating_request_key]

        model_request_key = originating_request_hash['model_request_key']
        model_request_hash = serialized_data_hashes[model_request_key]

        parameters_key = model_request_hash['parameters_key']
        parameters_hash = serialized_data_hashes[parameters_key]

        return self._deserialize_job(job_hash=job_hash,
                                     allocations_key_list=allocation_list,
                                     allocations_hashes=allocation_hashes,
                                     originating_request_hash=originating_request_hash,
                                     model_request_hash=model_request_hash,
                                     parameters_hash=parameters_hash)

    def save_job(self, job: RequestedJob):
        """
        Add or update the given job object in this manager's backend data store of job record data.

        Parameters
        ----------
        job : RequestedJob
            The job to be updated or added.
        """
        job_key = self._get_job_key_for_id(job.job_id)
        mappings = self._serialize_job(job=job, job_key=job_key)

        pipeline = self.redis.pipeline()
        try:
            for key in mappings:
                pipeline.hmset(key, mappings[key])
            pipeline.execute()
        finally:
            pipeline.reset()
