from typing import List, Dict, Any, Optional
import discord
from datetime import datetime, timedelta

def create_bracket_view(tournament_data: Dict[str, Any]) -> List[str]:
    """Create a visual representation of the tournament bracket"""
    lines = []
    current_round = tournament_data["current_round"]
    
    # Header
    lines.extend([
        "🏆 Tournament Bracket",
        "═" * 50,
        ""
    ])
    
    # Process each round
    for round_idx, matches in enumerate(tournament_data["rounds"]):
        # Round header
        round_marker = " (Current)" if round_idx == current_round else ""
        lines.append(f"Round {round_idx + 1}{round_marker}")
        lines.append("─" * 20)
        
        # Process matches in this round
        for match_idx, match in enumerate(matches):
            if match[1] is None:
                ch_name = match[0].name if match[0] is not None else "TBD"
                lines.append(f"├─➤ {ch_name} (BYE)")
            else:
                # Find match data for current round
                match_info = ""
                if round_idx == current_round and tournament_data["current_matches"]:
                    try:
                        match_data = tournament_data["current_matches"][match_idx]
                        if match_data["message"]:
                            votes_1 = sum(1 for r in match_data["message"].reactions 
                                        if str(r.emoji) == "1️⃣") - 1
                            votes_2 = sum(1 for r in match_data["message"].reactions 
                                        if str(r.emoji) == "2️⃣") - 1
                            match_info = f" ({votes_1} vs {votes_2})"
                    except (IndexError, AttributeError):
                        pass
                
                ch1_name = match[0].name if match[0] is not None else "TBD"
                ch2_name = match[1].name if match[1] is not None else "TBD"
                lines.extend([
                    f"├─┬─ {ch1_name}{match_info}",
                    f"│ └─ {ch2_name}"
                ])
            
            # Add spacing between matches except for the last one
            if match_idx < len(matches) - 1:
                lines.append("│")
        
        # Add spacing between rounds
        lines.append("")
    
    # Add footer with time remaining if tournament is active
    if current_round < len(tournament_data["rounds"]):
        time_left = timedelta(days=1) - (datetime.now() - tournament_data["start_time"])
        hours, remainder = divmod(int(time_left.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)
        lines.extend([
            "─" * 50,
            f"Time remaining in current round: {hours}h {minutes}m"
        ])
    
    return lines

def format_for_discord(lines: List[str]) -> List[str]:
    """Split bracket view into Discord-message-sized chunks"""
    messages = []
    current_chunk = []
    current_length = 0
    
    for line in lines:
        # Account for Discord markdown
        line_length = len(line) + 6  # Add space for 