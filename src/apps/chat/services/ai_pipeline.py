import asyncio
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
import httpx  # Changed from aiohttp
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class MLRequest(BaseModel):
    context: List[Dict[str, Any]]
    session_id: str
    user_id: Optional[str] = None
    request_id: str
    model_name: str
    parameters: Dict[str, Any] = {}
    timestamp: float


class MLResponse(BaseModel):
    text: str
    session_id: str
    request_id: str
    model_used: str
    processing_time: float
    timestamp: float
    metadata: Dict[str, Any] = {}


class MLPipeline:
    def __init__(
        self,
        model_endpoint: str,
        cache_enabled: bool = True,
        cache_ttl_seconds: int = 300,
        max_retries: int = 3,
        timeout_seconds: float = 15.0,
        batch_enabled: bool = False,
    ):
        self.model_endpoint = model_endpoint
        self.cache_enabled = cache_enabled
        self.cache_ttl_seconds = cache_ttl_seconds
        self.cache = {}  # Simple in-memory cache
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.batch_enabled = batch_enabled
        self.batch_queue = asyncio.Queue()
        self.batch_task = None

    async def initialize(self):
        """Initialize the ML pipeline including batch processor if enabled"""
        if self.batch_enabled:
            self.batch_task = asyncio.create_task(self._batch_processor())

    async def _batch_processor(self):
        """Process batches of ML requests for more efficient inference"""
        while True:
            try:
                # Collect requests for batch processing
                batch = []
                # Get the first item with a timeout
                try:
                    first_item = await asyncio.wait_for(
                        self.batch_queue.get(),
                        timeout=0.1,  # 100ms timeout to wait for first item
                    )
                    batch.append(first_item)
                    self.batch_queue.task_done()
                except asyncio.TimeoutError:
                    # No items in queue, continue loop
                    await asyncio.sleep(0.01)
                    continue

                # Try to get more items without blocking
                max_batch_size = 16  # Prevent too large batches
                while len(batch) < max_batch_size:
                    try:
                        item = self.batch_queue.get_nowait()
                        batch.append(item)
                        self.batch_queue.task_done()
                    except asyncio.QueueEmpty:
                        break

                if not batch:
                    continue

                # Process the batch
                batch_requests = [item[0] for item in batch]  # Extract requests
                futures = [item[1] for item in batch]  # Extract futures

                # Send batch request
                try:
                    batch_results = await self._send_batch_request(batch_requests)

                    # Set results for each future
                    for i, future in enumerate(futures):
                        if i < len(batch_results):
                            future.set_result(batch_results[i])
                        else:
                            future.set_exception(
                                Exception("Batch processing failed for this item")
                            )
                except Exception as e:
                    # Set exception for all futures in batch
                    for future in futures:
                        if not future.done():
                            future.set_exception(e)
            except Exception as e:
                logger.error(f"Error in batch processor: {str(e)}")
                await asyncio.sleep(1)  # Avoid tight loop on persistent errors

    async def process_request(self, ml_request: MLRequest) -> MLResponse:
        """Process an ML request, optionally using cache"""
        start_time = asyncio.get_event_loop().time()

        # Check cache if enabled
        if self.cache_enabled:
            cache_key = self._generate_cache_key(ml_request)
            cached_response = self._get_from_cache(cache_key)
            if cached_response:
                return cached_response

        # Prepare for retries
        retries_left = self.max_retries
        last_error = None

        while retries_left > 0:
            try:
                if self.batch_enabled:
                    # Use batch processing
                    loop = asyncio.get_running_loop()
                    future = loop.create_future()
                    await self.batch_queue.put((ml_request, future))
                    # Wait for result with timeout
                    response = await asyncio.wait_for(
                        future, timeout=self.timeout_seconds
                    )
                    break
                else:
                    # Direct request
                    response = await self._send_request(ml_request)
                    break
            except asyncio.TimeoutError:
                last_error = "Request timed out"
                retries_left -= 1
            except Exception as e:
                last_error = str(e)
                retries_left -= 1

            if retries_left > 0:
                # Exponential backoff
                await asyncio.sleep(0.1 * (2 ** (self.max_retries - retries_left)))

        if retries_left == 0 and last_error:
            logger.error(
                f"ML request failed after {self.max_retries} retries: {last_error}"
            )
            raise Exception(f"Failed to process ML request: {last_error}")

        # Calculate processing time
        end_time = asyncio.get_event_loop().time()
        processing_time = end_time - start_time

        # Add processing time and timestamp to response
        response_dict = response.dict() if hasattr(response, "dict") else response
        response_dict["processing_time"] = processing_time
        response_dict["timestamp"] = end_time

        ml_response = MLResponse(**response_dict)

        # Cache the result if enabled
        if self.cache_enabled:
            self._add_to_cache(cache_key, ml_response)

        return ml_response

    async def _send_request(self, ml_request: MLRequest) -> Dict:
        """Send a single request to the ML service"""
        payload = ml_request.dict()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.model_endpoint, json=payload, timeout=self.timeout_seconds
            )

            if response.status_code == 200:  # Changed from response.status
                return response.json()  # Changed from await response.json()
            else:
                error_text = response.text  # Changed from await response.text()
                logger.error(f"ML service error: {response.status_code}, {error_text}")
                raise Exception(f"ML service error: {response.status_code}")

    async def _send_batch_request(self, requests: List[MLRequest]) -> List[Dict]:
        """Send a batch request to the ML service"""
        # Convert all requests to dicts
        payload = {"batch": [request.dict() for request in requests]}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.model_endpoint}/batch",
                json=payload,
                timeout=self.timeout_seconds * 2,  # Longer timeout for batches
            )

            if response.status_code == 200:  # Changed from response.status
                return response.json()  # Changed from await response.json()
            else:
                error_text = response.text  # Changed from await response.text()
                logger.error(
                    f"ML batch service error: {response.status_code}, {error_text}"
                )
                raise Exception(f"ML batch service error: {response.status_code}")

    def _generate_cache_key(self, ml_request: MLRequest) -> str:
        """Generate a unique cache key for the request"""
        # Use deterministic parts of the request for the cache key
        key_parts = [
            ml_request.model_name,
            json.dumps(ml_request.context),
            json.dumps(ml_request.parameters),
        ]
        return ":".join(key_parts)

    def _get_from_cache(self, cache_key: str) -> Optional[MLResponse]:
        """Try to get a response from cache"""
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            # Check if entry is still valid
            if (
                datetime.utcnow().timestamp() - entry["timestamp"]
            ) < self.cache_ttl_seconds:
                return entry["response"]
            else:
                # Remove expired entry
                del self.cache[cache_key]
        return None

    def _add_to_cache(self, cache_key: str, response: MLResponse):
        """Add a response to the cache"""
        self.cache[cache_key] = {
            "response": response,
            "timestamp": datetime.utcnow().timestamp(),
        }

        # Simple cache cleanup - remove oldest entries if too many
        if len(self.cache) > 1000:  # Arbitrary limit
            # Remove entries that are older than 20% of TTL
            current_time = datetime.utcnow().timestamp()
            to_remove = []
            for key, entry in self.cache.items():
                if (current_time - entry["timestamp"]) > (self.cache_ttl_seconds * 0.8):
                    to_remove.append(key)

            # Remove identified entries
            for key in to_remove:
                del self.cache[key]
