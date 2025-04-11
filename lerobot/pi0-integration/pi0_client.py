from openpi_client import websocket_client_policy


def create_pi0_client(host="localhost", port=9000):
    """Create a client connection to the Pi0 model server.
    
    Args:
        host: Hostname of the Pi0 server
        port: Port number of the Pi0 server
        
    Returns:
        WebsocketClientPolicy: Connected client instance
    """
    print(f"Connecting to Pi0 model at {host}:{port}...")
    client = websocket_client_policy.WebsocketClientPolicy(host=host, port=port)
    return client


def send_to_pi0(client, observation):
    """Send observation to Pi0 model and get response.
    
    Args:
        client: Pi0 client instance
        observation: Observation dictionary
        
    Returns:
        dict: Response from Pi0 model including actions
    """
    print("Sending observation to Pi0 model...")
    response = client.infer(observation)
    print("Pi0 model response:", response)
    return response 