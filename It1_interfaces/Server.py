import asyncio
import websockets
import json
import os

clients = {}  # websocket -> color ("white" או "black")
board_state = {}  # ייצוג פשוט של הלוח (לדוגמה)

async def notify_all():
    if clients:
        msg = json.dumps({"type": "update", "board": board_state})
        await asyncio.gather(*[ws.send(msg) for ws in clients])

async def handle_client(websocket):
    global clients

    # הקצאת צבע ללקוח החדש
    if "white" not in clients.values():
        clients[websocket] = "white"
        await websocket.send(json.dumps({"type": "assign_color", "color": "white"}))
        print("לקוח לבן התחבר")
    elif "black" not in clients.values():
        clients[websocket] = "black"
        await websocket.send(json.dumps({"type": "assign_color", "color": "black"}))
        print("לקוח שחור התחבר")
    else:
        await websocket.send(json.dumps({"type": "error", "message": "כבר יש 2 שחקנים"}))
        await websocket.close()
        return

    try:
        async for message in websocket:
            data = json.loads(message)

            if data["action"] == "move":
                # העברת המהלך לכל הלקוחות האחרים
                from_pos = data["from"]
                to_pos = data["to"]
                piece = data.get("piece", "P")
                player_color = data.get("player_color", "unknown")

                print(f"📥 קיבלתי מהלך מ-{player_color}: {piece} מ-{from_pos} ל-{to_pos}")

                # לעדכן את מצב הלוח
                board_state[from_pos] = None
                board_state[to_pos] = piece

                # שליחת המהלך לכל הלקוחות אחרים
                move_msg = json.dumps({
                    "type": "move",
                    "action": "move",
                    "from": from_pos,
                    "to": to_pos,
                    "piece": piece,
                    "player_color": player_color
                })
                
                for other_ws in clients:
                    if other_ws != websocket:  # לא לשלוח לשולח המקורי
                        try:
                            await other_ws.send(move_msg)
                        except:
                            pass  # התעלמות משגיאות שליחה

            elif data["action"] == "jump":
                # טיפול בקפיצה
                piece = data.get("piece", "P")
                position = data.get("position")
                player_color = data.get("player_color", "unknown")

                print(f"🦘 קיבלתי קפיצה מ-{player_color}: {piece} ב-{position}")

                # שליחת הקפיצה לכל הלקוחות אחרים
                jump_msg = json.dumps({
                    "type": "move",
                    "action": "jump",
                    "piece": piece,
                    "position": position,
                    "player_color": player_color
                })
                
                for other_ws in clients:
                    if other_ws != websocket:  # לא לשלוח לשולח המקורי
                        try:
                            await other_ws.send(jump_msg)
                        except:
                            pass  # התעלמות משגיאות שליחה

                # עדכון כללי של הלוח לכל הלקוחות
                await notify_all()

    except websockets.exceptions.ConnectionClosed:
        print(f"לקוח {clients.get(websocket)} התנתק")
    finally:
        if websocket in clients:
            del clients[websocket]

async def main():
    port = int(os.environ.get("PORT", 8765))
    async with websockets.serve(handle_client, "0.0.0.0", port):
        print(f"שרת רץ על ws://0.0.0.0:{port}")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())