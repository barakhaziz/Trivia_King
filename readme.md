# Trivia Client-Server Application

## Overview
This Trivia Client-Server application is a multi-player trivia game where players connect to a central server to answer trivia questions. The server manages game sessions, player connections, and trivia question delivery, while clients connect to the server to participate in the game rounds.

## Server Workflow
- **Start-Up**: Upon start-up, the server initializes and listens for incoming client connections over TCP after broadcasting its presence over UDP.
- **Connection Handling**: The server accepts client connections, assigning each client to a separate thread to handle communication.
- **Game Management**: Once the minimum number of players is connected, the server starts the trivia game, sending questions to all clients and managing their responses.
- **End of Game**: After a set number of rounds or when a termination condition is met (e.g., only one player left), the server concludes the game and prepares for a new session.

## Client Workflow
- **Listening for Server Broadcasts**: Clients listen for UDP broadcasts from the server to discover available game sessions.
- **Connecting**: Once a broadcast is received, clients attempt to establish a TCP connection to the server using the details provided in the broadcast.
- **Game Participation**: Clients receive questions from the server and send their answers back within a given timeframe.

## Key Mechanisms

### 1. Server Disconnect Handling
- **Timeout**: If there is no communication from the server within a specified timeout period (`SERVER_NO_RESPONSE_TIMEOUT`), the client assumes the server has disconnected.
- **Action**: The client stops sending data, closes its current connection, and may attempt to reconnect or exit based on the situation.

### 2. Handling Insufficient Players
- **Wait Time**: If only one player is connected, the server waits for an additional period (`WAIT_FOR_2_CLIENTS_AT_LEAST`) for more players to join.
- **Cancellation**: If no additional players join within this period, the server cancels the game session and informs the connected player before closing the connection.

### 3. Post-Game Broadcast
- **Game Conclusion**: When a game session ends, the server sends a broadcast message to all clients indicating the game has ended.
- **Readiness for New Game**: Simultaneously, the server resets its state to be ready to start a new game, allowing it to handle new connections and start a new session immediately.

### 4. Client Disconnect Handling
- **Non-response**: If a player does not respond during a round (i.e., does not answer a trivia question), their session is considered inactive.
- **Session Termination**: The server then attempts to close the inactive session to free up resources and maintain game integrity. This ensures that only active players are retained in the game.

## Getting Started
To participate in the game, clients should run the client application which will automatically detect available servers and connect. Ensure that the server application is running and accessible over the network the clients are on.

## Technologies Used
- **Programming Language**: Python 3
- **Networking**: TCP for reliable data transmission and UDP for service discovery.

## Conclusion
This Trivia Client-Server application demonstrates basic network programming concepts along with handling real-time client-server interactions in a trivia game context. It emphasizes robust handling of network issues such as disconnects and non-responsive clients, ensuring a smooth gameplay experience.
