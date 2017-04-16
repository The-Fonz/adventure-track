#
# Put all JSON schemas here.
# This is data that gets passed between different microservices.
#

# Using JSON schemas to specify format metadata
JSON_SCHEMA_LOCATION_GPS_POINT = {
    "$schema": "http://json-schema.org/draft-04/schema",
    "title": "GPS point",
    "description": "A GPS point from a user",
    "type": "object",
    "properties": {
        "user_id": {
            "description": "The unique identifier for the user",
            "type": "integer"
        },
        "timestamp": {
            "description": "The GPS timestamp",
            "type": "string",
            "format": "date-time"
        },
        "received": {
            "description": "When this point was received by server",
            "type": "string",
            "format": "date-time"
        },
        "ptz": {
            "description": "Lat/lon and height MSL",
            "type": "object",
            "properties": {
                "latitude": {"type": "number"},
                "longitude": {"type": "number"},
                "height_m_msl": {"type": "number"}
            },
            "required": ["latitude", "longitude", "height_m_msl"]
        },

    },
    "required": ["user_id", "ptz", "received"]
}
