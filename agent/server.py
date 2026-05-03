import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uuid
from livekit.api import (
    AccessToken,
    VideoGrants,
    RoomConfiguration,
    RoomAgentDispatch,
)
from dotenv import load_dotenv
from pathlib import Path
import json
from datetime import datetime

load_dotenv(".env.local")

app = FastAPI()

# Allow your local frontend to talk to this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/get-token")
async def get_token(participant_name: str = "patient_user"):
    dynamic_room = f"test-room-{uuid.uuid4().hex[:6]}"

    token = (
        AccessToken(
            os.getenv("LIVEKIT_API_KEY"),
            os.getenv("LIVEKIT_API_SECRET"),
        )
        .with_identity(participant_name)
        .with_grants(
            VideoGrants(
                room_join=True,
                room=dynamic_room,
            )
        )
        .with_room_config(
            RoomConfiguration(
                agents=[
                    RoomAgentDispatch(
                        agent_name="Jenny",
                    )
                ]
            )
        )
        .to_jwt()
    )

    return {"token": token}

# --- NEW DATA ROUTE ---
# Make sure this is at the top: from pathlib import Path

@app.get("/api/intakes")
async def get_intakes():
    # Dynamically locate the intakes folder relative to where server.py lives
    current_dir = Path(__file__).parent
    intakes_dir = current_dir / "intakes"

    logs = []

    if not intakes_dir.exists():
        print(f"Warning: Could not find directory at {intakes_dir}")
        return logs

    for file_path in intakes_dir.glob("*.json"):
        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            # Extract Call Time from the filename (e.g., intake_20260501_103000.json)
            filename = file_path.stem
            time_str = filename.replace("intake_", "")
            try:
                dt = datetime.strptime(time_str, "%Y%m%d_%H%M%S")
                call_time = dt.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                call_time = "Unknown"

            logs.append({
                "id": file_path.name,
                "callTime": call_time,
                "raw_data": data # We send the raw JSON straight to the frontend
            })
        except Exception as e:
            print(f"Error parsing {file_path.name}: {e}")

    # Sort logs so newest calls appear at the top
    logs.sort(key=lambda x: x["callTime"], reverse=True)
    return logs

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
