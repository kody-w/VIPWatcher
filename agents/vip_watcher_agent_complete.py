from agents.basic_agent import BasicAgent
import json
import requests
from datetime import datetime, timedelta
import logging

class VIPWatcherAgent(BasicAgent):
    def __init__(self):
        self.name = "VIPWatcher"
        self.metadata = {
            "name": self.name,
            "description": "Monitors communications from VIP contacts stored in OneDrive, sends rich Teams notifications, and manages VIP-related actions. Maintains recent alerts memory for follow-up questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "The VIP Watcher action to perform",
                        "enum": [
                            "check_new_communications",
                            "get_vip_list", 
                            "add_vip",
                            "remove_vip",
                            "refresh_vips",
                            "show_last_alert",
                            "show_recent_alerts",
                            "why_flagged",
                            "snooze_alert",
                            "create_task",
                            "open_message",
                            "mark_as_read",
                            "check_reply_status"
                        ]
                    },
                    "vip_name": {
                        "type": "string",
                        "description": "Name of VIP contact (for add/remove operations)"
                    },
                    "vip_email": {
                        "type": "string",
                        "description": "Primary email of VIP contact"
                    },
                    "alt_emails": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Alternative emails for VIP contact"
                    },
                    "teams_user_id": {
                        "type": "string",
                        "description": "Teams user ID for VIP contact"
                    },
                    "upn": {
                        "type": "string",
                        "description": "User Principal Name for VIP contact"
                    },
                    "alert_id": {
                        "type": "string",
                        "description": "ID of specific alert to act upon"
                    },
                    "snooze_duration": {
                        "type": "string",
                        "description": "Duration to snooze: '30m', '2h', 'today'",
                        "enum": ["30m", "2h", "today"]
                    },
                    "task_title": {
                        "type": "string",
                        "description": "Title for follow-up task"
                    },
                    "task_due": {
                        "type": "string",
                        "description": "Due date for task (ISO format or 'tomorrow')"
                    },
                    "filter_vip": {
                        "type": "string",
                        "description": "Filter alerts by specific VIP name"
                    },
                    "time_range": {
                        "type": "string",
                        "description": "Time range for filtering: 'today', 'this_week', 'last_4h'",
                        "enum": ["today", "this_week", "last_4h"]
                    },
                    "user_guid": {
                        "type": "string",
                        "description": "User GUID for personalized VIP list and alerts"
                    }
                },
                "required": ["action"]
            }
        }
        
        # Power Automate endpoints
        self.pa_endpoints = {
            "get_vip_list": "https://2ecf0a25a2e7eb6a9aec43400e2b67.02.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/8c5bc94235b9442b90579c95accdf526/triggers/manual/paths/invoke/?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=E3MWG_chA_T4GfppoLqgqbo4O4y3lxUovybs1NSRECg",
            "update_vip_list": "https://prod-00.centralus.logic.azure.com/workflows/YOUR_UPDATE_VIP_FLOW/triggers/manual/paths/invoke",
            "check_communications": "https://2ecf0a25a2e7eb6a9aec43400e2b67.02.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/d76e36a98722474599660e98ad47a750/triggers/manual/paths/invoke/?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=J7L6rYJdsov9Eng_gM0qufKflB_sZDICvnB4fssUMiU",
            "teams_operations": "https://prod-00.centralus.logic.azure.com/workflows/YOUR_TEAMS_OPS_FLOW/triggers/manual/paths/invoke",
            "task_operations": "https://prod-00.centralus.logic.azure.com/workflows/YOUR_TASK_FLOW/triggers/manual/paths/invoke",
            "audit_log": "https://prod-00.centralus.logic.azure.com/workflows/YOUR_AUDIT_LOG_FLOW/triggers/manual/paths/invoke"
        }
        
        # In-memory storage for recent alerts (last 50)
        self.recent_alerts = []
        self.vip_cache = None
        self.last_vip_refresh = None
        
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        action = kwargs.get('action')
        user_guid = kwargs.get('user_guid', 'default')
        
        try:
            # Route to appropriate handler
            if action == "check_new_communications":
                return self._check_new_communications(user_guid)
                
            elif action == "get_vip_list":
                return self._get_vip_list(user_guid, refresh=False)
                
            elif action == "refresh_vips":
                return self._get_vip_list(user_guid, refresh=True)
                
            elif action == "add_vip":
                return self._add_vip(user_guid, kwargs)
                
            elif action == "remove_vip":
                return self._remove_vip(user_guid, kwargs)
                
            elif action == "show_last_alert":
                return self._show_last_alert()
                
            elif action == "show_recent_alerts":
                return self._show_recent_alerts(kwargs)
                
            elif action == "why_flagged":
                return self._explain_flagging(kwargs.get('alert_id'))
                
            elif action == "snooze_alert":
                return self._snooze_alert(kwargs)
                
            elif action == "create_task":
                return self._create_task(kwargs)
                
            elif action == "open_message":
                return self._open_message(kwargs.get('alert_id'))
                
            elif action == "mark_as_read":
                return self._mark_as_read(kwargs.get('alert_id'))
                
            elif action == "check_reply_status":
                return self._check_reply_status(kwargs.get('alert_id'))
                
            else:
                return json.dumps({
                    "status": "error",
                    "message": f"Unknown action: {action}"
                })
                
        except Exception as e:
            logging.error(f"VIP Watcher error: {str(e)}")
            return json.dumps({
                "status": "error",
                "message": f"Error executing {action}: {str(e)}"
            })

    def _check_new_communications(self, user_guid):
        """Check for new communications from VIPs"""
        
        # First ensure VIP list is loaded
        vip_list = self._get_cached_vips(user_guid)
        if not vip_list:
            return json.dumps({
                "status": "warning",
                "message": "VIP list is empty or unavailable. Add VIPs first."
            })
        
        # Call Power Automate to check Email, Teams, and Calendar
        payload = {
            "user_guid": user_guid,
            "check_email": True,
            "check_teams": True,
            "check_calendar": True,
            "since_timestamp": (datetime.utcnow() - timedelta(hours=4)).isoformat()
        }
        
        response = self._call_power_automate(self.pa_endpoints["check_communications"], payload)
        
        # Handle empty response or error
        if isinstance(response, dict) and response.get("status") == "error":
            return json.dumps(response)
        
        # If response is a list (array of communications)
        communications = []
        if isinstance(response, list):
            communications = response
        elif isinstance(response, dict):
            communications = response.get("communications", [])
        
        # If no communications found
        if not communications:
            return json.dumps({
                "status": "success",
                "message": "No new communications found in the last 4 hours",
                "checked": {
                    "vip_count": len(vip_list),
                    "communications_checked": 0
                }
            })
        
        # Process each communication against VIP list
        new_alerts = []
        
        for comm in communications:
            vip_matches = self._match_against_vips(comm, vip_list)
            if vip_matches:
                alert = self._create_alert(comm, vip_matches)
                new_alerts.append(alert)
                self.recent_alerts.insert(0, alert)
                
                # Send Teams notification via adaptive card
                self._send_vip_notification(alert, user_guid)
        
        # Keep only last 50 alerts
        self.recent_alerts = self.recent_alerts[:50]
        
        # Write to audit log
        self._audit_log(f"Checked {len(communications)} communications, found {len(new_alerts)} VIP matches", user_guid)
        
        if new_alerts:
            return json.dumps({
                "status": "success",
                "message": f"Found {len(new_alerts)} new VIP communications",
                "alerts": new_alerts[:5],  # Return top 5
                "total_count": len(new_alerts),
                "checked": {
                    "vip_count": len(vip_list),
                    "communications_checked": len(communications)
                }
            })
        else:
            return json.dumps({
                "status": "success",
                "message": f"Checked {len(communications)} communications - no VIP matches found",
                "checked": {
                    "vip_count": len(vip_list),
                    "communications_checked": len(communications),
                    "vips": [vip.get("display_name", "Unknown") for vip in vip_list]
                }
            })

    def _match_against_vips(self, comm, vip_list):
        """Match communication participants against VIP list"""
        matches = []
        
        # Build participant set from communication
        participants = set()
        
        # Add sender/from
        if comm.get("from"):
            participants.add(comm["from"].lower())
        if comm.get("sender"):
            participants.add(comm["sender"].lower())
        if comm.get("organizer"):
            participants.add(comm["organizer"].lower())
            
        # Add recipients
        for field in ["to", "cc", "attendees", "required_attendees", "optional_attendees"]:
            if comm.get(field):
                if isinstance(comm[field], list):
                    participants.update([p.lower() for p in comm[field]])
                else:
                    participants.add(comm[field].lower())
        
        # Add @mentioned users
        if comm.get("mentioned_users"):
            participants.update([u.lower() for u in comm["mentioned_users"]])
            
        # Match against each VIP
        for vip in vip_list:
            match_type = None
            match_field = None
            
            # 1. Exact match by UPN or Teams ID
            if vip.get("upn") and vip["upn"].lower() in participants:
                match_type = "exact"
                match_field = "upn"
            elif vip.get("teams_user_id") and vip["teams_user_id"].lower() in participants:
                match_type = "exact"
                match_field = "teams_user_id"
                
            # 2. Email match
            elif vip.get("primary_email") and vip["primary_email"].lower() in participants:
                match_type = "exact"
                match_field = "primary_email"
            elif vip.get("alt_emails"):
                for alt_email in vip["alt_emails"]:
                    if alt_email.lower() in participants:
                        match_type = "exact"
                        match_field = "alt_email"
                        break
                        
            # 3. Fuzzy name match (simplified - would use proper fuzzy matching library)
            elif vip.get("display_name"):
                for participant in participants:
                    if self._fuzzy_match(vip["display_name"], participant):
                        match_type = "probable"
                        match_field = "display_name"
                        break
            
            if match_type:
                matches.append({
                    "vip_name": vip.get("display_name", "Unknown VIP"),
                    "match_type": match_type,
                    "match_field": match_field,
                    "vip_data": vip
                })
        
        return matches

    def _fuzzy_match(self, name1, name2):
        """Simple fuzzy name matching (would use proper library in production)"""
        name1_parts = set(name1.lower().split())
        name2_parts = set(name2.lower().split())
        
        # If at least 2 name parts match, consider it a probable match
        common_parts = name1_parts.intersection(name2_parts)
        return len(common_parts) >= 2

    def _create_alert(self, comm, vip_matches):
        """Create alert object from communication and VIP matches"""
        alert = {
            "id": f"alert_{datetime.utcnow().timestamp()}",
            "timestamp": datetime.utcnow().isoformat(),
            "channel_type": comm.get("type", "unknown"),  # Email, Chat, Invite
            "vip_matches": [m["vip_name"] for m in vip_matches],
            "match_details": vip_matches,
            "subject": comm.get("subject", comm.get("preview", "No subject")),
            "from": comm.get("from", comm.get("sender", "Unknown")),
            "urgency": self._calculate_urgency(comm),
            "communication_data": comm,
            "status": "new"
        }
        
        return alert

    def _calculate_urgency(self, comm):
        """Calculate urgency heuristic"""
        urgency_score = 0
        
        # High importance flag
        if comm.get("importance") == "high":
            urgency_score += 3
            
        # @mentions
        if comm.get("mentioned_users"):
            urgency_score += 2
            
        # Meeting starting soon (< 48h)
        if comm.get("type") == "Invite" and comm.get("start_time"):
            try:
                start = datetime.fromisoformat(comm["start_time"])
                hours_until = (start - datetime.utcnow()).total_seconds() / 3600
                if hours_until < 48:
                    urgency_score += 2
                if hours_until < 24:
                    urgency_score += 2
            except:
                pass
        
        # Map score to level
        if urgency_score >= 5:
            return "high"
        elif urgency_score >= 3:
            return "medium"
        else:
            return "low"

    def _send_vip_notification(self, alert, user_guid):
        """Send Teams adaptive card notification for VIP alert"""
        
        # Build adaptive card
        card = {
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": f"🔔 VIP Alert - {', '.join(alert['vip_matches'])}",
                    "weight": "Bolder",
                    "size": "Large"
                },
                {
                    "type": "TextBlock",
                    "text": f"via {alert['channel_type']}",
                    "spacing": "None",
                    "isSubtle": True
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {"title": "Subject", "value": alert['subject']},
                        {"title": "From", "value": alert['from']},
                        {"title": "When", "value": alert['timestamp']},
                        {"title": "Urgency", "value": alert['urgency'].upper()},
                        {"title": "Confidence", "value": alert['match_details'][0]['match_type'].title()}
                    ]
                }
            ],
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "Open",
                    "data": {"action": "open", "alert_id": alert['id']}
                },
                {
                    "type": "Action.Submit",
                    "title": "Snooze 30m",
                    "data": {"action": "snooze", "alert_id": alert['id'], "duration": "30m"}
                },
                {
                    "type": "Action.Submit",
                    "title": "Create Task",
                    "data": {"action": "create_task", "alert_id": alert['id']}
                },
                {
                    "type": "Action.Submit",
                    "title": "Why flagged?",
                    "data": {"action": "why_flagged", "alert_id": alert['id']}
                },
                {
                    "type": "Action.Submit",
                    "title": "Not a VIP",
                    "data": {"action": "not_vip", "alert_id": alert['id']}
                }
            ]
        }
        
        # Send via AdaptiveCardPowerAutomate agent
        from agents.adaptive_card_agent import AdaptiveCardPowerAutomateAgent
        card_agent = AdaptiveCardPowerAutomateAgent()
        
        result = card_agent.perform(
            adaptive_card_json=json.dumps(card),
            recipient=user_guid,  # Would be user's email in production
            post_as="VIP Watcher Bot",
            post_in="Chat with bot",
            update_message=f"VIP Alert sent for {alert['from']}",
            bot_name="VIPWatcher",
            wait_for_response=True,
            card_title=f"VIP Alert - {alert['subject'][:50]}",
            card_category="vip_alert",
            priority_level=alert['urgency'],
            reference_id=alert['id']
        )
        
        return result

    def _get_vip_list(self, user_guid, refresh=False):
        """Get VIP list from OneDrive"""
        
        # Check cache first (unless refresh requested)
        if not refresh and self.vip_cache and self.last_vip_refresh:
            cache_age = (datetime.utcnow() - self.last_vip_refresh).total_seconds() / 60
            if cache_age < 30:  # Cache valid for 30 minutes
                return json.dumps({
                    "status": "success",
                    "vips": self.vip_cache,
                    "count": len(self.vip_cache),
                    "cached": True
                })
        
        # Call Power Automate to read VIP list from OneDrive
        payload = {
            "user_guid": user_guid,
            "file_path": f"/VIPWatcher/VIP-Contacts.csv"  # Or .xlsx
        }
        
        response = self._call_power_automate(self.pa_endpoints["get_vip_list"], payload)
        
        # Handle different response formats
        if isinstance(response, list):
            # Power Automate returned a direct array of VIPs
            # Process alt_emails from string to array
            for vip in response:
                if isinstance(vip.get("alt_emails"), str):
                    # Convert semicolon-separated string to array
                    if vip["alt_emails"]:
                        vip["alt_emails"] = [email.strip() for email in vip["alt_emails"].split(";") if email.strip()]
                    else:
                        vip["alt_emails"] = []
            
            self.vip_cache = response
            self.last_vip_refresh = datetime.utcnow()
            
            return json.dumps({
                "status": "success",
                "vips": self.vip_cache,
                "count": len(self.vip_cache),
                "cached": False
            })
        elif isinstance(response, dict):
            # Check if it's an error response
            if response.get("status") == "error":
                return json.dumps(response)
            # Or a success response with vips field
            elif response.get("status") == "success" or response.get("vips"):
                vips = response.get("vips", [])
                # Process alt_emails from string to array
                for vip in vips:
                    if isinstance(vip.get("alt_emails"), str):
                        if vip["alt_emails"]:
                            vip["alt_emails"] = [email.strip() for email in vip["alt_emails"].split(";") if email.strip()]
                        else:
                            vip["alt_emails"] = []
                
                self.vip_cache = vips
                self.last_vip_refresh = datetime.utcnow()
                
                return json.dumps({
                    "status": "success",
                    "vips": self.vip_cache,
                    "count": len(self.vip_cache),
                    "cached": False
                })
            else:
                # Unknown dict format, treat as error
                return json.dumps({
                    "status": "error",
                    "message": "Unexpected response format from Power Automate"
                })
        else:
            return json.dumps({
                "status": "error",
                "message": f"Invalid response type from Power Automate: {type(response)}"
            })

    def _get_cached_vips(self, user_guid):
        """Get cached VIP list, loading if necessary"""
        if not self.vip_cache or not self.last_vip_refresh:
            result = self._get_vip_list(user_guid, refresh=True)
            result_data = json.loads(result)
            if result_data.get("status") == "success":
                return self.vip_cache
        return self.vip_cache or []

    def _add_vip(self, user_guid, kwargs):
        """Add a new VIP to the list"""
        vip_name = kwargs.get('vip_name')
        vip_email = kwargs.get('vip_email')
        
        if not vip_name or not vip_email:
            return json.dumps({
                "status": "error",
                "message": "Both vip_name and vip_email are required"
            })
        
        # Build VIP entry
        new_vip = {
            "display_name": vip_name,
            "primary_email": vip_email,
            "alt_emails": kwargs.get('alt_emails', []),
            "upn": kwargs.get('upn', vip_email),
            "teams_user_id": kwargs.get('teams_user_id', ''),
            "notes": f"Added {datetime.utcnow().strftime('%Y-%m-%d')}"
        }
        
        # Call Power Automate to update OneDrive file
        payload = {
            "user_guid": user_guid,
            "action": "add",
            "vip_data": new_vip
        }
        
        response = self._call_power_automate(self.pa_endpoints["update_vip_list"], payload)
        
        if response.get("status") == "success":
            # Update cache
            if self.vip_cache:
                self.vip_cache.append(new_vip)
            
            # Audit
            self._audit_log(f"Added VIP: {vip_name} ({vip_email})", user_guid)
            
            return json.dumps({
                "status": "success",
                "message": f"Successfully added {vip_name} to VIP list"
            })
        else:
            return json.dumps(response)

    def _remove_vip(self, user_guid, kwargs):
        """Remove a VIP from the list"""
        vip_email = kwargs.get('vip_email')
        vip_name = kwargs.get('vip_name')
        
        if not vip_email and not vip_name:
            return json.dumps({
                "status": "error",
                "message": "Either vip_email or vip_name is required"
            })
        
        payload = {
            "user_guid": user_guid,
            "action": "remove",
            "vip_email": vip_email,
            "vip_name": vip_name
        }
        
        response = self._call_power_automate(self.pa_endpoints["update_vip_list"], payload)
        
        if response.get("status") == "success":
            # Update cache
            if self.vip_cache:
                self.vip_cache = [v for v in self.vip_cache 
                                 if v.get('primary_email') != vip_email 
                                 and v.get('display_name') != vip_name]
            
            # Audit
            identifier = vip_email or vip_name
            self._audit_log(f"Removed VIP: {identifier}", user_guid)
            
            return json.dumps({
                "status": "success",
                "message": f"Successfully removed {identifier} from VIP list"
            })
        else:
            return json.dumps(response)

    def _show_last_alert(self):
        """Show the most recent alert"""
        if not self.recent_alerts:
            return json.dumps({
                "status": "info",
                "message": "No recent alerts found"
            })
        
        alert = self.recent_alerts[0]
        return json.dumps({
            "status": "success",
            "alert": alert,
            "message": f"Most recent alert from {alert['from']} about '{alert['subject']}'"
        })

    def _show_recent_alerts(self, kwargs):
        """Show recent alerts with optional filtering"""
        filter_vip = kwargs.get('filter_vip')
        time_range = kwargs.get('time_range', 'today')
        
        filtered_alerts = self.recent_alerts.copy()
        
        # Filter by VIP if specified
        if filter_vip:
            filtered_alerts = [a for a in filtered_alerts 
                             if filter_vip.lower() in [v.lower() for v in a['vip_matches']]]
        
        # Filter by time range
        if time_range:
            cutoff_time = datetime.utcnow()
            if time_range == 'last_4h':
                cutoff_time -= timedelta(hours=4)
            elif time_range == 'today':
                cutoff_time = cutoff_time.replace(hour=0, minute=0, second=0)
            elif time_range == 'this_week':
                cutoff_time -= timedelta(days=7)
            
            filtered_alerts = [a for a in filtered_alerts 
                             if datetime.fromisoformat(a['timestamp']) > cutoff_time]
        
        # Return top 5
        result_alerts = filtered_alerts[:5]
        
        if result_alerts:
            summary = []
            for i, alert in enumerate(result_alerts, 1):
                summary.append(f"{i}. {alert['timestamp'][:16]} | {alert['channel_type']} | {', '.join(alert['vip_matches'])} | {alert['subject'][:50]}")
            
            return json.dumps({
                "status": "success",
                "message": f"Found {len(filtered_alerts)} alerts, showing top 5",
                "alerts": result_alerts,
                "summary": "\n".join(summary)
            })
        else:
            return json.dumps({
                "status": "info",
                "message": "No alerts found matching criteria"
            })

    def _explain_flagging(self, alert_id):
        """Explain why an alert was flagged"""
        if not alert_id:
            # Use most recent alert
            if not self.recent_alerts:
                return json.dumps({
                    "status": "error",
                    "message": "No alerts available"
                })
            alert = self.recent_alerts[0]
        else:
            # Find specific alert
            alert = next((a for a in self.recent_alerts if a['id'] == alert_id), None)
            if not alert:
                return json.dumps({
                    "status": "error",
                    "message": f"Alert {alert_id} not found"
                })
        
        explanations = []
        for match in alert['match_details']:
            if match['match_type'] == 'exact':
                explanations.append(f"• {match['vip_name']}: Exact match on {match['match_field']}")
            else:
                explanations.append(f"• {match['vip_name']}: Probable match on {match['match_field']} (fuzzy matching)")
        
        urgency_reasons = []
        if alert['urgency'] == 'high':
            urgency_reasons.append("marked as high importance")
            if alert.get('communication_data', {}).get('mentioned_users'):
                urgency_reasons.append("you were @mentioned")
        
        return json.dumps({
            "status": "success",
            "message": "Flagging explanation",
            "alert_id": alert['id'],
            "matches": explanations,
            "urgency": alert['urgency'],
            "urgency_reasons": urgency_reasons
        })

    def _snooze_alert(self, kwargs):
        """Snooze an alert for specified duration"""
        alert_id = kwargs.get('alert_id')
        duration = kwargs.get('snooze_duration', '30m')
        
        # Calculate snooze until time
        snooze_until = datetime.utcnow()
        if duration == '30m':
            snooze_until += timedelta(minutes=30)
        elif duration == '2h':
            snooze_until += timedelta(hours=2)
        elif duration == 'today':
            snooze_until = snooze_until.replace(hour=23, minute=59, second=59)
        
        # Update alert status
        for alert in self.recent_alerts:
            if alert['id'] == alert_id:
                alert['status'] = 'snoozed'
                alert['snooze_until'] = snooze_until.isoformat()
                break
        
        # Schedule reminder via Power Automate
        payload = {
            "alert_id": alert_id,
            "remind_at": snooze_until.isoformat(),
            "user_guid": kwargs.get('user_guid', 'default')
        }
        
        self._call_power_automate(self.pa_endpoints["teams_operations"], payload)
        
        return json.dumps({
            "status": "success",
            "message": f"Alert snoozed until {snooze_until.strftime('%H:%M')}",
            "snooze_until": snooze_until.isoformat()
        })

    def _create_task(self, kwargs):
        """Create a follow-up task"""
        alert_id = kwargs.get('alert_id')
        task_title = kwargs.get('task_title')
        task_due = kwargs.get('task_due', 'tomorrow')
        
        # Get alert details
        alert = next((a for a in self.recent_alerts if a['id'] == alert_id), None)
        if not alert and self.recent_alerts:
            alert = self.recent_alerts[0]
        
        if not alert:
            return json.dumps({
                "status": "error",
                "message": "No alert found"
            })
        
        # Default task title if not provided
        if not task_title:
            task_title = f"Follow up on: {alert['subject'][:50]}"
        
        # Calculate due date
        if task_due == 'tomorrow':
            due_date = (datetime.utcnow() + timedelta(days=1)).isoformat()
        else:
            due_date = task_due
        
        # Create task via Power Automate
        payload = {
            "title": task_title,
            "due_date": due_date,
            "notes": f"VIP: {', '.join(alert['vip_matches'])}\nFrom: {alert['from']}\nSubject: {alert['subject']}",
            "link": alert.get('communication_data', {}).get('web_url', ''),
            "user_guid": kwargs.get('user_guid', 'default')
        }
        
        response = self._call_power_automate(self.pa_endpoints["task_operations"], payload)
        
        if response.get("status") == "success":
            return json.dumps({
                "status": "success",
                "message": f"Task created: {task_title}",
                "due_date": due_date
            })
        else:
            return json.dumps(response)

    def _open_message(self, alert_id):
        """Generate deep link to open message"""
        alert = next((a for a in self.recent_alerts if a['id'] == alert_id), None)
        if not alert and self.recent_alerts:
            alert = self.recent_alerts[0]
        
        if not alert:
            return json.dumps({
                "status": "error",
                "message": "No alert found"
            })
        
        # Get deep link from communication data
        web_url = alert.get('communication_data', {}).get('web_url', '')
        
        if web_url:
            return json.dumps({
                "status": "success",
                "message": "Opening message",
                "url": web_url,
                "instruction": f"Click here to open: {web_url}"
            })
        else:
            return json.dumps({
                "status": "error",
                "message": "No URL available for this message"
            })

    def _mark_as_read(self, alert_id):
        """Mark alert as read"""
        for alert in self.recent_alerts:
            if alert['id'] == alert_id:
                alert['status'] = 'read'
                break
        
        return json.dumps({
            "status": "success",
            "message": "Alert marked as read"
        })

    def _check_reply_status(self, alert_id):
        """Check if user has replied to the communication"""
        alert = next((a for a in self.recent_alerts if a['id'] == alert_id), None)
        if not alert and self.recent_alerts:
            alert = self.recent_alerts[0]
        
        if not alert:
            return json.dumps({
                "status": "error",
                "message": "No alert found"
            })
        
        # Call Power Automate to check sent items/thread
        payload = {
            "message_id": alert.get('communication_data', {}).get('message_id', ''),
            "thread_id": alert.get('communication_data', {}).get('thread_id', ''),
            "user_guid": alert.get('user_guid', 'default')
        }
        
        response = self._call_power_automate(self.pa_endpoints["check_communications"], payload)
        
        if response.get("replied"):
            return json.dumps({
                "status": "success",
                "message": "You have replied to this message",
                "reply_time": response.get("reply_time", "Unknown")
            })
        else:
            return json.dumps({
                "status": "success",
                "message": "No reply found for this message"
            })

    def _call_power_automate(self, endpoint, payload):
        """Generic Power Automate call handler"""
        try:
            headers = {"Content-Type": "application/json"}
            response = requests.post(endpoint, json=payload, headers=headers, timeout=30)
            
            if response.status_code in [200, 202]:
                if response.text:
                    try:
                        # Try to parse as JSON
                        return response.json()
                    except json.JSONDecodeError:
                        # If it's not valid JSON, return as error
                        return {
                            "status": "error",
                            "message": f"Invalid JSON response: {response.text[:200]}"
                        }
                else:
                    return {"status": "success"}
            else:
                return {
                    "status": "error",
                    "message": f"Power Automate returned status {response.status_code}",
                    "details": response.text[:500] if response.text else "No response body"
                }
        except Exception as e:
            logging.error(f"Power Automate call failed: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to call Power Automate: {str(e)}"
            }

    def _audit_log(self, event, user_guid):
        """Write to audit log"""
        try:
            payload = {
                "timestamp": datetime.utcnow().isoformat(),
                "user_guid": user_guid,
                "event": event,
                "agent": "VIPWatcher"
            }
            
            self._call_power_automate(self.pa_endpoints["audit_log"], payload)
        except Exception as e:
            logging.error(f"Failed to write audit log: {str(e)}")