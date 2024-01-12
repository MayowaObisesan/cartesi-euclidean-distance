from os import environ
import logging
import requests
import math
import json
import traceback

logging.basicConfig(level="INFO")
logger = logging.getLogger(__name__)

rollup_server = environ["ROLLUP_HTTP_SERVER_URL"]
logger.info(f"HTTP rollup_server url is {rollup_server}")


def hex2str(hex):
    """
    Decodes a hex string into a regular string
    """
    return bytes.fromhex(hex[2:]).decode("utf-8")


def str2hex(str):
    """
    Encodes a string as a hex string
    """
    return "0x" + str.encode("utf-8").hex()


def euclidean_distance(point1, point2):
    if len(point1) != len(point2):
        raise ValueError("Both points must have the same number of dimensions")
    return math.sqrt(sum((p1 - p2) ** 2 for p1, p2 in zip(point1, point2)))


def handle_advance(data):
    # Writing a calculator function that calculates euclidean distance of two points
    # I will extend the current calculator app from the cartesi rollup-example
    logger.info(f"Received advance request data {data}")
    status = "accept"

    try:
        input = hex2str(data["payload"])
        logger.info(f"Received input: {input}")

        # Get points1 and points2
        parsed_input = json.loads(json.loads(input))
        point1: list = parsed_input.get("point1")
        point2: list = parsed_input.get("point2")

        # Evaluate expression
        output = euclidean_distance(point1, point2)

        # Emit notice with result of calculation
        logger.info(f"Adding notice with payload: '{output}'")
        response = requests.post(
            f"{rollup_server}/notice", json={"payload": str2hex(str(output))}
        )
        logger.info(
            f"Received notice status {response.status_code} body {response.content}"
        )
    except Exception as e:
        status = "reject"
        msg = f"Error processing data {data}\n{traceback.format_exc()}"
        logger.error(msg)

        response = requests.post(
            f"{rollup_server}/report", json={"payload": str2hex(msg)}
        )
        logger.info(
            f"Received report status {response.status_code} body {response.content}"
        )

    return status


def handle_inspect(data):
    logger.info(f"Received inspect request data {data}")
    logger.info("Adding report")
    response = requests.post(
        f"{rollup_server}/report", json={"payload": data["payload"]}
    )
    logger.info(f"Received report status {response.status_code}")
    return "accept"


handlers = {
    "advance_state": handle_advance,
    "inspect_state": handle_inspect,
}

finish = {"status": "accept"}

while True:
    logger.info("Sending finish")
    response = requests.post(rollup_server + "/finish", json=finish)
    logger.info(f"Received finish status {response.status_code}")
    if response.status_code == 202:
        logger.info("No pending rollup request, trying again")
    else:
        rollup_request = response.json()
        data = rollup_request["data"]
        handler = handlers[rollup_request["request_type"]]
        finish["status"] = handler(rollup_request["data"])
