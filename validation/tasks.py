# validation/tasks.py
import json
import logging
from celery import shared_task
from celery.result import AsyncResult
from jsonschema import Draft7Validator, ValidationError
from django.http import JsonResponse
from django.utils import timezone
from django.conf import settings
import redis

from shapely.geometry import shape
from shapely.validation import make_valid

logger = logging.getLogger('validation')

class RedisClientWithExpiry:
    def __init__(self, redis_client, default_expiry=3600):
        self.redis_client = redis_client
        self.default_expiry = default_expiry

    def hset(self, key, field, value):
        """
        Set the value of a hash field.
        """
        self.redis_client.hset(key, field, value)

    def hincrby(self, key, field, increment):
        """
        Increment the integer value of a hash field by a given amount.
        """
        self.redis_client.hincrby(key, field, increment)

    def hgetall(self, key):
        """
        Get all fields and values in a hash.
        """
        return self.redis_client.hgetall(key)

    def rpush(self, key, value, expiry=None):
        """
        Append a value to the end of a list.
        """
        self.redis_client.rpush(key, value)
        if expiry:
            self.redis_client.expire(key, expiry)
        else:
            self.redis_client.expire(key, self.default_expiry)

    def lrange(self, key, start, end):
        """
        Get a range of elements from a list.
        """
        return self.redis_client.lrange(key, start, end)

def get_redis_client():
    return redis.StrictRedis.from_url(settings.CELERY_BROKER_URL)

def traverse_path(data, path):
    """
    Traverse the nested data structure according to the given path.
    
    :param data: The nested data structure (dict or list)
    :param path: List or deque of keys/indices to traverse
    :return: The target element or None if path is invalid
    """
    current = data
    for key in path:
        if isinstance(current, dict):
            current = current.get(key, None)
        elif isinstance(current, list):
            if isinstance(key, int) and 0 <= key < len(current):
                current = current[key]
            else:
                return None
        else:
            return None
    return current

def fix_feature(featureCollection, e):
    """
    Traverse the featureCollection according to the error_path and attempt fixes.
    """
    fixes = []
    try:
        logger.debug(f'Attempting fix of: {featureCollection}')

        path_list = list(e.absolute_path)
        current_element = traverse_path(featureCollection, path_list[:-1])
        if current_element is None:
            logger.error("Failed to traverse path. The path might be invalid.")
            return featureCollection, fixes

        last_key = path_list[-1]
        invalid_value = e.instance
        feature_id = featureCollection["features"][0].get("@id", "unknown")

        # # Attempt to convert integers to strings where necessary
        # if e.validator == 'type' and e.validator_value == 'string':
        #     if isinstance(invalid_value, int):
        #         current_element[last_key] = str(invalid_value)
        #         fix_description = f"Converted integer '{invalid_value}' to string '{current_element[last_key]}'"
        #         fixes.append({
        #             "feature_id": feature_id,
        #             "path": ".".join(map(str, path_list)),
        #             "description": fix_description
        #         })
        #         logger.debug(fix_description)
        #     else:
        #         logger.debug("Invalid value is not an integer or does not require conversion.")
        # else:
        #     logger.debug(f"Validator or validator_value does not match type check: validator={e.validator}, validator_value={e.validator_value}")
        #
        # # Attempt to fix missing timespans
        # if e.validator == 'required' and isinstance(e.validator_value, list):
        #     if any(ref == 'timespans' for ref in e.validator_value):
        #         logger.debug(f'Attempting "timespans" fix... ({current_element})')
        #         when = current_element.get('when', None)
        #         start = when.get('start', None)
        #         end = when.get('end', None)
        #         if start or end:
        #             timespan = {}
        #             if start:
        #                 timespan['start'] = start
        #             if end:
        #                 timespan['end'] = end
        #             when['timespans'] = [timespan]
        #             when.pop('start', None)
        #             when.pop('end', None)
        #             fix_description = f"Created '{current_element['when']}' from start='{start}' and end='{end}'"
        #             fixes.append({
        #                 "feature_id": feature_id,
        #                 "path": ".".join(map(str, path_list)),
        #                 "description": fix_description
        #             })
        #             logger.debug(fix_description)
        #         else:
        #             logger.debug(f"... failed: no appropriate start or end values found.")
        #
        # # Attempt to fix ids/urls by either removal or prepending a dummy namespace
        # if isinstance(invalid_value, str) and isinstance(e.validator_value, list):
        #     ref_list = [ref.get('$ref') for ref in e.validator_value]
        #
        #     if '#/definitions/patterns/definitions/validURL' in ref_list or '#/definitions/patterns/definitions/namespaceTerm' in ref_list:
        #         if invalid_value == "":
        #             # Remove the element if invalid_value is an empty string
        #             del current_element[last_key]
        #             fix_description = f"Removed empty @id field from element"
        #             fixes.append({
        #                 "feature_id": feature_id,
        #                 "path": ".".join(map(str, path_list)),
        #                 "description": fix_description
        #             })
        #             logger.debug(fix_description)
        #         else:
        #             # Prepend a dummy namespace if invalid_value is not empty
        #             new_value = f"custom_namespace:{invalid_value}"
        #             current_element[last_key] = new_value
        #             fix_description = f"Fixed @id value: '{invalid_value}' to '{new_value}'"
        #             fixes.append({
        #                 "feature_id": feature_id,
        #                 "path": ".".join(map(str, path_list)),
        #                 "description": fix_description
        #             })
        #             logger.debug(fix_description)

    except Exception as e:
        raise

    return featureCollection, fixes

def get_task_status(task_id):
    redis_client = get_redis_client()
    status = redis_client.hgetall(task_id)
    if not status:
        return JsonResponse({"status": "not_found", "message": "Task ID not found"}, status=404)
    status = {k.decode('utf-8'): v.decode('utf-8') for k, v in status.items()}
    
    current_time = timezone.now()
    last_update_time_str = status.get('last_update', status.get('start_time'))
    last_update_time = timezone.datetime.fromisoformat(last_update_time_str)
    status['time_since_last_update'] = (current_time - last_update_time).total_seconds()
    
    status['fixes'] = [fix.decode('utf-8') for fix in redis_client.lrange(f"{task_id}_fixes", 0, -1)]
    status['errors'] = [error.decode('utf-8') for error in redis_client.lrange(f"{task_id}_errors", 0, -1)]
    status['task_id'] = task_id
    return JsonResponse({
        "status": "success",
        "task_status": status
    })

def validate_geometry(geometry):
    """
    Validate and fix a single geometry using Shapely.
    Apply buffer(0) first, then make_valid if necessary.

    :param geometry: A dictionary representing a GeoJSON geometry
    :return: Tuple of (geometry, fixed, valid)
    """
    fixed = False
    valid = False
    
    geometry_type = geometry.get('type', None)
    geometry_coordinates = geometry.get('coordinates', None)
    if geometry_type and geometry_coordinates:
        try:
            # Convert GeoJSON to Shapely geometry
            geom = shape({
                'type': geometry.get('type'),
                'coordinates': geometry_coordinates
            })

            # Check if the geometry is valid
            if not geom.is_valid:
                logger.debug(f"Geometry is invalid: {geom}")

                # First Tier Fix: Attempt to fix the geometry using buffer(0)
                fixed_geom = geom.buffer(0)
                if fixed_geom.is_valid:
                    geometry['coordinates'] = fixed_geom.geometry['coordinates']
                    logger.debug(f"Fixed invalid geometry with buffer(0).")
                    fixed = True
                    valid = True
                else:
                    logger.debug("Buffer(0) did not fix the geometry. Attempting make_valid...")

                    # Second Tier Fix: Attempt to fix the geometry using make_valid
                    fixed_geom = make_valid(geom)
                    if fixed_geom.is_valid:
                        geometry['coordinates'] = fixed_geom.geometry['coordinates']
                        logger.debug(f"Fixed invalid geometry with make_valid.")
                        fixed = True
                        valid = True
                    else:
                        logger.error("Failed to fix geometry with make_valid.")
            else:
                logger.debug(f"Geometry passed validation.")
                valid = True

        except Exception as e:
            logger.error(f"Error processing geometry: {e}")
    else:
        logger.error(f"Error: geometry lacks either type or coordinates.")
        valid = False

    return geometry, fixed, valid

def validate_feature_geometry(feature):
    """
    Validate the geometry of a GeoJSON feature using Shapely.
    Fix invalid geometries using a two-tier approach for single geometries or geometries in a GeometryCollection.

    :param feature: A GeoJSON feature with geometry to validate
    :return: Tuple of (feature, fixed, valid), where fixed is a boolean indicating if a fix was applied,
             and valid is a boolean indicating if the geometry is valid after fixing.
    """
    fixed = False
    valid = False
    
    if 'geometry' in feature:
        # Extract geometry from the feature
        geometry = feature.get('geometry', None)
    
        if geometry is None:
            logger.debug("Feature has no geometry (null).")
            valid = True  # null geometries are valid
        elif isinstance(geometry, dict):
            geometry_type = geometry.get('type', None)
    
            if geometry_type == 'GeometryCollection':
                geometries = geometry.get('geometries', [])
                filtered_geometries = []
                all_valid = True  # Assume all geometries are valid initially
    
                for i, geom in enumerate(geometries):
                    if geom is None:
                        logger.debug(f"Skipping null geometry at index {i}.")
                        continue
    
                    logger.debug(f"Validating geometry {i} in GeometryCollection.")
                    geom, geom_fixed, geom_valid = validate_geometry(geom)
                    if geom_fixed:
                        fixed = True
                    if not geom_valid:
                        all_valid = False
                    filtered_geometries.append(geom)  # Collect valid geometries
                
                # Update the feature with filtered geometries
                feature['geometry']['geometries'] = filtered_geometries
                valid = all_valid  # Set valid to True only if all geometries are valid
            elif geometry_type:
                # Handle single geometries
                geometry, fixed, valid = validate_geometry(geometry)
                feature['geometry'] = geometry
            else:
                logger.debug("Feature geometry lacks `type`.")
                
        else:
            logger.error("Invalid geometry format in feature.")
                
    # No need to handle absence of `geometry` or other errors as this will be done by JSON Schema validation
    return feature, fixed, valid

def cancel_all_subtasks(sub_tasks):
    for sub_task_id in sub_tasks:
        try:
            task_result = AsyncResult(sub_task_id)
            task_result.revoke(terminate=True)
            print(f"Sub-task {sub_task_id} has been cancelled.")
        except Exception as e:
            print(f"Failed to cancel sub-task {sub_task_id}: {e}")

@shared_task(bind=True)
def validate_feature_batch(self, feature_batch, schema, task_id):
    """
    Validate a batch of features and manage subtasks.
    
    :param self: The Celery task instance.
    :param feature_batch: List of GeoJSON features to validate.
    :param schema: JSON schema for validation.
    :param task_id: ID of the parent task.
    """
    
    validator = Draft7Validator(schema)    
    redis_client = get_redis_client()
    client_with_expiry = RedisClientWithExpiry(redis_client) # default_expiry=3600 (1 hour)

    # Store the current task ID as a subtask
    sub_task_id = self.request.id
    client_with_expiry.rpush(f"{task_id}_subtasks", sub_task_id)

    for feature in feature_batch:
        stopValidation = False
        fixAttempts = 0
        
        feature, fixed, valid = validate_feature_geometry(feature)
        if not valid:
            client_with_expiry.rpush(f"{task_id}_errors", 'Geometry failed validation and could not be fixed.')
            client_with_expiry.hset(task_id, 'last_update', timezone.now().isoformat())
        if fixed:
            client_with_expiry.rpush(f"{task_id}_fixes", json.dumps({
                "feature_id": feature.get("@id", "unknown"),
                "path": "features.feature.geometry",
                "description": "Geometry fixed."
            }))
            client_with_expiry.hset(task_id, 'last_update', timezone.now().isoformat())
        
        featureCollection = {
            "type": "FeatureCollection",
            "features": [feature]
        }
        
        while not stopValidation:        
            try:
                logger.debug(f'Validating feature: {feature}')
                validator.validate(featureCollection)
                stopValidation = True
                logger.debug(f'Validated feature: {feature}')
            except ValidationError as e:
                error_message = e.message
                error_path = " -> ".join([str(p) for p in e.absolute_path])
                detailed_error = parse_validation_error(e)
                full_error = f"Validation error at {error_path}: {detailed_error}"
                if fixAttempts < settings.VALIDATION_MAXFIXATTEMPTS:
                    try:
                        featureCollection, fixes = fix_feature({
                            "type": "FeatureCollection",
                            "features": [feature]
                        }, e)
                        fixAttempts += 1

                        if fixes:
                            for fix in fixes:  # Iterate over the list of fixes
                                try:
                                    client_with_expiry.rpush(f"{task_id}_fixes", json.dumps(fix))
                                except Exception as e:
                                    logger.error(f"Failed to push fix to Redis: {e}")
                        else:
                            # No fixes applied; no point in revalidating
                            stopValidation = True
                            
                    except Exception as fix_error:
                        logger.error(f"Failed to fix feature: {fix_error}")
                        logger.error(full_error)
                        client_with_expiry.rpush(f"{task_id}_errors", full_error)
                        client_with_expiry.hset(task_id, 'last_update', timezone.now().isoformat())
                        stopValidation = True
                else:
                    logger.error(full_error)
                    client_with_expiry.rpush(f"{task_id}_errors", full_error)
                    client_with_expiry.hset(task_id, 'last_update', timezone.now().isoformat())
                    stopValidation = True
            except Exception as e:
                logger.error(f"Unexpected error during validation: {e}")
                client_with_expiry.rpush(f"{task_id}_errors", str(e))
                client_with_expiry.hset(task_id, 'last_update', timezone.now().isoformat())
                stopValidation = True
                
            if stopValidation:
                try:
                    client_with_expiry.hincrby(task_id, 'queued_features', -1)
                    client_with_expiry.hset(task_id, 'last_update', timezone.now().isoformat())
                except Exception as e:
                    logger.error(f"Error updating Redis status: {e}")

    # Check if all tasks are done
    try:

        task_status = client_with_expiry.hgetall(task_id)
        all_queued = task_status.get(b'all_queued', b'').decode('utf-8')
        total_features = int(task_status.get(b'total_features', 0))
        queued_features = int(task_status.get(b'queued_features', 0))
        errors = [error.decode('utf-8') for error in client_with_expiry.lrange(f"{task_id}_errors", 0, -1)]
        
        start_time_str = task_status.get(b'start_time', b'').decode('utf-8')
        if start_time_str:
            start_time = timezone.datetime.fromisoformat(start_time_str)
        else:
            start_time = timezone.now()
        
        end_time = timezone.now()
        elapsed_time = (end_time - start_time).total_seconds()
             
        if all_queued == 'true' and queued_features == 0:
            client_with_expiry.hset(task_id, mapping={
                'status': 'complete',
                'end_time': end_time.isoformat(),
                'time_taken': elapsed_time,
                'time_remaining': 0
            })
            logger.debug(f'Task {task_id} completed successfully.')
        elif len(errors) > settings.VALIDATION_MAX_ERRORS:
            subtasks = [subtask.decode('utf-8') for subtask in client_with_expiry.lrange(f"{task_id}_subtasks", 0, -1)]
            cancel_all_subtasks(subtasks)
            client_with_expiry.hset(task_id, mapping={
                'status': f'aborted',
                'end_time': end_time.isoformat(),
                'time_taken': elapsed_time,
                'time_remaining': 0
            })   
        else:
            if total_features > queued_features:
                estimated_total_time = (elapsed_time / (total_features - queued_features)) * total_features
                estimated_time_remaining = estimated_total_time - elapsed_time
            else:
                estimated_time_remaining = 0            
            client_with_expiry.hset(task_id, 'time_remaining', estimated_time_remaining)
            logger.debug(f'Task {task_id} not yet complete. Status: {task_status}')
    except Exception as e:
        logger.error(f"Error checking or updating task status: {e}")

def parse_validation_error(error: ValidationError) -> str:
    # Get the part of the schema that failed validation
    schema_path = " -> ".join([str(p) for p in error.schema_path])
    
    # Get the path within the instance (the JSON being validated)
    instance_path = " -> ".join([str(p) for p in error.absolute_path])
    
    # Get the error message and value that caused the error
    error_message = error.message
    error_value = error.instance
    
    # Format the message for better readability
    formatted_error = (
        f"Error Type: {error.validator} ({error.validator_value})\n"
        f"Schema Path: {schema_path}\n"
        f"Instance Path: {instance_path}\n"
        f"Invalid Value: {error_value}\n"
        f"Message: {error_message}"
    )
    
    return formatted_error
