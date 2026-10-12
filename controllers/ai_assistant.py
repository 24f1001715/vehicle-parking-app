import os
import json
import re
import urllib.request
import urllib.error
from datetime import datetime
import math

from flask import Blueprint, request, jsonify, session
from models.models import db, ParkingLot, ParkingSpot, Reservation, User
from utils.api_decorators import api_user_required

ai_assistant_bp = Blueprint('ai_assistant', __name__, url_prefix='/api/ai')


def call_gemini_api(prompt_text, api_key):
    """
    Direct HTTPS call to Google Gemini endpoint using urllib.
    Tries active model versions (gemini-3.5-flash, gemini-2.5-pro, etc.).
    Gracefully returns None if API call fails so system falls back to smart local NLP.
    """
    candidate_models = ["gemini-3.5-flash", "gemini-3-flash-preview", "gemini-2.5-pro", "gemini-flash-latest"]
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": prompt_text}]
        }],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 800
        }
    }
    data_bytes = json.dumps(payload).encode('utf-8')

    for model_name in candidate_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        try:
            req = urllib.request.Request(url, data=data_bytes, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=12) as response:
                result = json.loads(response.read().decode('utf-8'))
                candidates = result.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
        except urllib.error.HTTPError as he:
            # If model deprecated/404 or high demand 503, try next candidate
            continue
        except Exception as e:
            print(f"[AI Assistant] Gemini request exception on {model_name}: {e}")
            continue

    return None


def get_available_lots_context():
    """Gather live parking lot status and availability for prompt context."""
    lots = ParkingLot.query.all()
    lot_summaries = []
    for lot in lots:
        avail = ParkingSpot.query.filter_by(lot_id=lot.id, status='A').count()
        lot_summaries.append({
            "id": lot.id,
            "name": lot.prime_location_name,
            "address": lot.address,
            "pin_code": lot.pin_code,
            "price": lot.price,
            "available_spots": avail,
            "total_spots": lot.max_spots
        })
    return lot_summaries


def get_user_active_bookings_context(user_email):
    """Gather user's active/unreleased bookings."""
    active = Reservation.query.filter_by(user_email=user_email, leaving_timestamp=None).all()
    res_list = []
    for r in active:
        res_list.append({
            "reservation_id": r.id,
            "lot_name": r.lot.prime_location_name if r.lot else "Unknown",
            "spot_number": r.spot.spot_number if r.spot else "N/A",
            "vehicle_number": r.vehicle_number,
            "parking_time": r.parking_timestamp,
            "rate": r.cost_per_hour
        })
    return res_list


def execute_release_reservation(reservation_id, user_email):
    """Helper to release a reservation, calculate charges and free the parking spot."""
    res = Reservation.query.get(reservation_id)
    if not res or res.user_email != user_email:
        return None, "Booking not found or not owned by you."

    if res.leaving_timestamp:
        return None, "This booking has already been released."

    now = datetime.now()
    try:
        start = datetime.strptime(res.parking_timestamp, "%Y-%m-%d %H:%M:%S")
    except Exception:
        start = now

    hours = max(math.ceil((now - start).total_seconds() / 3600), 1)
    rate = res.cost_per_hour or (res.lot.price if res.lot else 0)
    total_cost = round(hours * rate, 2)

    res.leaving_timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    res.total_cost = total_cost

    if res.spot:
        res.spot.status = 'A'

    db.session.commit()
    return {
        "reservation_id": res.id,
        "lot_name": res.lot.prime_location_name if res.lot else "Parking Lot",
        "spot_number": res.spot.spot_number if res.spot else "N/A",
        "vehicle_number": res.vehicle_number,
        "duration_hours": hours,
        "rate": rate,
        "total_cost": total_cost,
        "released_at": res.leaving_timestamp
    }, None


def rule_based_fallback(user_message, user_email):
    """
    Smart local NLP fallback engine that handles natural language queries,
    search, recommendations, bookings, releases, and profile queries.
    """
    msg = user_message.lower().strip()
    lots = ParkingLot.query.all()
    active_reservations = Reservation.query.filter_by(user_email=user_email, leaving_timestamp=None).all()

    # 1. RELEASE / CHECKOUT INTENT: e.g. "release my spot", "checkout", "leave parking", "release reservation #12"
    if any(k in msg for k in ["release", "checkout", "check out", "leave", "end booking", "free spot", "unpark"]):
        if not active_reservations:
            return {
                "reply": "You do not have any active parked vehicles to release.",
                "action": None
            }

        target_res = None
        # Check if user mentioned a reservation ID like #12 or 12
        id_match = re.search(r'#?(\d+)', msg)
        if id_match:
            try:
                candidate_id = int(id_match.group(1))
                for r in active_reservations:
                    if r.id == candidate_id:
                        target_res = r
                        break
            except Exception:
                pass

        # Check if user mentioned vehicle plate or lot name
        if not target_res:
            for r in active_reservations:
                if r.vehicle_number.lower() in msg or (r.lot and r.lot.prime_location_name.lower() in msg):
                    target_res = r
                    break

        # If user only has 1 active reservation, default to releasing it
        if not target_res and len(active_reservations) == 1:
            target_res = active_reservations[0]

        if target_res:
            res_info, err = execute_release_reservation(target_res.id, user_email)
            if err:
                return {"reply": f"⚠️ {err}", "action": None}

            return {
                "reply": (
                    f"✅ **Spot Successfully Released!**\n\n"
                    f"• **Location:** {res_info['lot_name']}\n"
                    f"• **Spot:** Spot #{res_info['spot_number']}\n"
                    f"• **Vehicle:** `{res_info['vehicle_number']}`\n"
                    f"• **Duration:** {res_info['duration_hours']} hr(s)\n"
                    f"• **Final Bill:** **₹{res_info['total_cost']:.2f}**\n\n"
                    f"Thank you for using ParkIN! Your dashboard has been updated."
                ),
                "action": "release_success",
                "details": res_info
            }
        else:
            # Multiple active reservations, ask user which one to release
            reply = "You have **multiple active bookings**. Which one would you like to release?\n\n"
            for r in active_reservations:
                lot_name = r.lot.prime_location_name if r.lot else "Parking Lot"
                reply += f"• **Reservation #{r.id}** — {lot_name} (Vehicle `{r.vehicle_number}`)\n"
            reply += "\nPlease reply with: *\"Release reservation #[ID]\"* or mention your vehicle plate."
            return {"reply": reply, "action": "need_release_choice"}

    # 2. Check for Active Bookings / My Bookings intent
    if any(k in msg for k in ["my booking", "active", "status", "current park", "where did i park", "where is my car"]):
        if not active_reservations:
            return {
                "reply": "You currently have **no active parking bookings**. Would you like me to find a spot for you?",
                "action": None
            }
        
        reply = "Here are your **active bookings**:\n\n"
        for r in active_reservations:
            lot_name = r.lot.prime_location_name if r.lot else "Parking Lot"
            spot_num = r.spot.spot_number if r.spot else "N/A"
            reply += (
                f"• **Reservation #{r.id}** — **{lot_name}** (Spot #{spot_num})\n"
                f"  - Vehicle: `{r.vehicle_number}`\n"
                f"  - Parked since: {r.parking_timestamp}\n"
                f"  - Rate: ₹{r.cost_per_hour}/hr\n\n"
            )
        reply += "👉 Say *\"Release reservation #[ID]\"* to check out anytime directly from here!"
        return {"reply": reply, "action": None}

    # 3. Check for Booking Intent: e.g. "book a spot in Express Avenue for TN-01-AB-1234"
    if "book" in msg or "reserve" in msg:
        matched_lot = None
        for lot in lots:
            if lot.prime_location_name.lower() in msg:
                matched_lot = lot
                break

        plate_match = re.search(r'\b([A-Z]{2}[-\s]?[0-9]{1,2}[-\s]?[A-Z]{1,3}[-\s]?[0-9]{3,4})\b', user_message, re.IGNORECASE)
        vehicle_num = plate_match.group(1).upper().replace(" ", "-") if plate_match else None

        if matched_lot and vehicle_num:
            avail_spot = ParkingSpot.query.filter_by(lot_id=matched_lot.id, status='A').order_by(ParkingSpot.spot_number).first()
            if not avail_spot:
                return {
                    "reply": f"Unfortunately, **{matched_lot.prime_location_name}** is currently fully occupied with 0 available spots. Would you like an alternative nearby?",
                    "action": None
                }
            
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            res = Reservation(
                spot_id=avail_spot.id,
                lot_id=matched_lot.id,
                user_email=user_email,
                parking_timestamp=now_str,
                cost_per_hour=matched_lot.price,
                vehicle_number=vehicle_num
            )
            avail_spot.status = 'R'
            db.session.add(res)
            db.session.commit()

            return {
                "reply": (
                    f"🎉 **Booking Confirmed!**\n\n"
                    f"• **Location:** {matched_lot.prime_location_name}\n"
                    f"• **Spot Number:** Spot #{avail_spot.spot_number}\n"
                    f"• **Vehicle:** `{vehicle_num}`\n"
                    f"• **Rate:** ₹{matched_lot.price}/hr\n"
                    f"• **Reservation ID:** #{res.id}\n\n"
                    f"You're all set! Tell me *\"Release spot #{res.id}\"* whenever you are ready to exit."
                ),
                "action": "booking_success"
            }
        
        elif matched_lot and not vehicle_num:
            avail = ParkingSpot.query.filter_by(lot_id=matched_lot.id, status='A').count()
            return {
                "reply": f"**{matched_lot.prime_location_name}** has **{avail} spots available** at ₹{matched_lot.price}/hr.\n\nTo complete this booking, please provide your **vehicle number** (e.g., `TN-01-AB-1234`).",
                "action": "need_vehicle_number",
                "lot_id": matched_lot.id
            }

    # 4. Check for Cheapest / Budget Parking Intent
    if any(k in msg for k in ["cheapest", "lowest price", "affordable", "budget"]):
        lots_with_avail = [l for l in lots if ParkingSpot.query.filter_by(lot_id=l.id, status='A').count() > 0]
        if lots_with_avail:
            lots_with_avail.sort(key=lambda x: x.price)
            cheapest = lots_with_avail[:3]
            reply = "💰 Here are the **most affordable available parking lots** right now:\n\n"
            for l in cheapest:
                avail = ParkingSpot.query.filter_by(lot_id=l.id, status='A').count()
                reply += f"• **{l.prime_location_name}** — **₹{l.price}/hr**\n  - {l.address} (PIN: {l.pin_code})\n  - Available: **{avail}/{l.max_spots} spots**\n\n"
            reply += "Would you like me to reserve a spot in any of these for you?"
            return {"reply": reply, "action": None}

    # 5. Search by Location or Name Intent
    matched_lots = []
    for lot in lots:
        avail = ParkingSpot.query.filter_by(lot_id=lot.id, status='A').count()
        if (lot.prime_location_name.lower() in msg or 
            (lot.address and any(word in lot.address.lower() for word in msg.split() if len(word) > 3)) or
            (lot.pin_code and lot.pin_code in msg)):
            matched_lots.append((lot, avail))

    if matched_lots:
        reply = f"Found **{len(matched_lots)} matching parking lot(s)**:\n\n"
        for lot, avail in matched_lots[:4]:
            reply += f"• **{lot.prime_location_name}**\n  - Rate: ₹{lot.price}/hr\n  - Location: {lot.address}\n  - Available: **{avail}/{lot.max_spots} spots**\n\n"
        reply += "Tell me: *\"Book [Lot Name] for [Vehicle Number]\"* to book immediately!"
        return {"reply": reply, "action": None}

    # 6. General Overview / Help Response
    total_avail = sum(ParkingSpot.query.filter_by(lot_id=l.id, status='A').count() for l in lots)
    return {
        "reply": (
            f"👋 Hi! I'm your **ParkIN AI Assistant**.\n\n"
            f"Across Chennai we currently have **{total_avail} available parking spots** across **{len(lots)} locations**.\n\n"
            f"Here are the actions I can perform for you:\n"
            f"• 🚗 **Book a Spot:** *\"Book Express Avenue for car TN-01-AB-1234\"*\n"
            f"• 🏁 **Release a Spot:** *\"Release my parking spot\"* or *\"Release reservation #42\"*\n"
            f"• 🔎 **Find Open Slots:** *\"Show spots near Royapettah or T. Nagar\"*\n"
            f"• 💰 **Find Cheapest:** *\"What is the cheapest parking lot?\"*\n"
            f"• 📋 **Check Status:** *\"Where is my car parked right now?\"*"
        ),
        "action": None
    }


@ai_assistant_bp.route('/chat', methods=['POST'])
@api_user_required
def ai_chat():
    user_email = session.get('user')
    data = request.get_json(silent=True) or request.form.to_dict()
    user_message = (data.get('message') or '').strip()

    if not user_message:
        return jsonify({'success': False, 'message': 'Message cannot be empty'}), 400

    api_key = os.getenv('GEMINI_API_KEY', '').strip()

    # If Gemini API key is available, use LLM with augmented context & tool execution
    if api_key:
        lots_context = get_available_lots_context()
        user_bookings = get_user_active_bookings_context(user_email)
        
        system_prompt = f"""
You are the official AI Parking Assistant for 'ParkIN' (a smart parking platform in Chennai).
Current User Email: {user_email}
Current Time: {datetime.now().strftime("%Y-%m-%d %H:%M")}

Live Parking Lots Directory:
{json.dumps(lots_context, indent=2)}

User's Active Unreleased Bookings:
{json.dumps(user_bookings, indent=2)}

Rules & Output Instructions:
1. Speak directly to the user as a helpful parking assistant.
2. NEVER output self-reflection, internal reasoning, or planning checklists (e.g., do NOT write "* Concise? Yes", "* Friendly? Yes", "* Markdown? Yes").
3. Format lists with clear bullet points (•) and bold titles.
4. Always use Indian Rupee currency symbol ₹ (e.g., ₹30/hr).
5. If the user wants to book a spot and has given a lot name and vehicle number, append this exact JSON block at the bottom:
   ```json
   {{"action": "book", "lot_id": <lot_id>, "vehicle_number": "<vehicle_number>"}}
   ```
6. If the user wants to release or check out of their active parking spot:
   - If they have exactly 1 active booking, append this JSON block at the bottom:
     ```json
     {{"action": "release", "reservation_id": <reservation_id>}}
     ```
   - If they have multiple active bookings, list them and ask which one they want to release.
"""
        full_prompt = f"{system_prompt}\n\nUser Question: {user_message}\n\nAssistant Response:"
        gemini_reply = call_gemini_api(full_prompt, api_key)

        if gemini_reply:
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', gemini_reply, re.DOTALL)
            if json_match:
                try:
                    action_data = json.loads(json_match.group(1))

                    # 1. Action: BOOK
                    if action_data.get("action") == "book" and action_data.get("lot_id") and action_data.get("vehicle_number"):
                        target_lot = ParkingLot.query.get(action_data["lot_id"])
                        if target_lot:
                            spot = ParkingSpot.query.filter_by(lot_id=target_lot.id, status='A').first()
                            if spot:
                                spot.status = 'R'
                                res = Reservation(
                                    spot_id=spot.id,
                                    lot_id=target_lot.id,
                                    user_email=user_email,
                                    parking_timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    cost_per_hour=target_lot.price,
                                    vehicle_number=action_data["vehicle_number"]
                                )
                                db.session.add(res)
                                db.session.commit()
                                clean_reply = re.sub(r'```json\s*\{.*?\}\s*```', '', gemini_reply, flags=re.DOTALL).strip()
                                return jsonify({
                                    'success': True,
                                    'reply': clean_reply + f"\n\n✅ *Confirmed reservation #{res.id} for Spot #{spot.spot_number} at {target_lot.prime_location_name}.*",
                                    'action': 'booking_success'
                                })

                    # 2. Action: RELEASE
                    elif action_data.get("action") == "release" and action_data.get("reservation_id"):
                        res_info, err = execute_release_reservation(action_data["reservation_id"], user_email)
                        if not err:
                            clean_reply = re.sub(r'```json\s*\{.*?\}\s*```', '', gemini_reply, flags=re.DOTALL).strip()
                            return jsonify({
                                'success': True,
                                'reply': (
                                    f"✅ **Spot Successfully Released!**\n\n"
                                    f"• **Location:** {res_info['lot_name']}\n"
                                    f"• **Spot:** Spot #{res_info['spot_number']}\n"
                                    f"• **Vehicle:** `{res_info['vehicle_number']}`\n"
                                    f"• **Duration:** {res_info['duration_hours']} hr(s)\n"
                                    f"• **Total Bill:** **₹{res_info['total_cost']:.2f}**\n\n"
                                    f"Your spot is now marked available and completed."
                                ),
                                'action': 'release_success'
                            })

                except Exception as ex:
                    print(f"[AI Assistant] Action execution error: {ex}")

            clean_reply = re.sub(r'```json\s*\{.*?\}\s*```', '', gemini_reply, flags=re.DOTALL).strip()
            return jsonify({'success': True, 'reply': clean_reply})

    # Default / Local NLP engine
    result = rule_based_fallback(user_message, user_email)
    return jsonify({
        'success': True,
        'reply': result['reply'],
        'action': result.get('action')
    })
