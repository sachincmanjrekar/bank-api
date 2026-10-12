"""The Lambda entry point, called the way a Lambda Function URL calls it."""

import json

from app.lambda_handler import handler


def function_url_event(method: str, path: str) -> dict:
    """A minimal Lambda Function URL event (same format as API Gateway HTTP API v2)."""
    return {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": path,
        "rawQueryString": "",
        "headers": {"host": "example.lambda-url.ap-southeast-2.on.aws"},
        "requestContext": {
            "http": {
                "method": method,
                "path": path,
                "protocol": "HTTP/1.1",
                "sourceIp": "203.0.113.1",
                "userAgent": "pytest",
            },
            "domainName": "example.lambda-url.ap-southeast-2.on.aws",
            "requestId": "test-request",
            "routeKey": "$default",
            "stage": "$default",
        },
        "isBase64Encoded": False,
    }


def test_health_through_lambda_handler():
    response = handler(function_url_event("GET", "/health"), context={})
    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {"status": "ok"}


def test_unknown_path_through_lambda_handler():
    response = handler(function_url_event("GET", "/nope"), context={})
    assert response["statusCode"] == 404
